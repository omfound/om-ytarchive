#!/usr/bin/env python3

import constants as c
from internetarchive import upload
from internetarchive import get_item
from internetarchive import modify_metadata
from internetarchive import delete
from datetime import datetime
from db import ytarchive
from log import log
from os import path
import om_api
import requests
from args import get_args
from subprocess import call


def update_session_status(session, status, archive_id=False):
    """Update stored session item status"""
    if archive_id:
        ytarchive().sessionsUpdate({
            'id': session.id,
            'archive_id': archive_id,
            'state': status})
    else:
        ytarchive().sessionsUpdate({
            'id': session.id,
            'state': status})


def update_file_status(file, status):
    """Update stored session file status"""
    ytarchive().filesUpdate({'id': file.id, 'state': status})


def finish_unchanged_files(archive_info, files):
    """Changes stored state of files with matching md5s to synced to prevent
    further processing
    """
    remove_files = []

    for key, file in enumerate(files):
        for archive_file in archive_info.item_metadata["files"]:
            if file["md5"] == archive_file["md5"]:
                remove_files.append(file)

    for remove_file in remove_files:
        update_file_status(remove_file, c.SESSION_SYNCED)
        log(remove_file, "File unchanged, removed from queue", c.SESSION_SYNCED)
        files.remove(remove_file)

    return files


def metadata_changed(metadata, archive_info):
    """Compares session item metadata from Open.Media API and Archive.org
    to determine whether they match or changes have been made
    """
    am = archive_info.item_metadata["metadata"]

    # no description key if it is empty...
    archive_metadata = dict(
        collection=am.get("collection", None),
        title=am.get("title", None),
        description=am.get("description", None),
        date=am.get("date", None),
        contributor=am.get("contributor", None),
        creator=am.get("creator", None),
        mediatype=am.get("mediatype", None),
        language=am.get("language", None),
        licenseurl=am.get("licenseurl", None),
        subject=am.get("subject", None)
    )

    if archive_metadata == metadata:
        return False
    else:
        return True


def prepare_archive_metadata(session):
    """Maps Open.Media API session metadata to an Archive.org API compatible
    dict
    """
    isodate = datetime.fromtimestamp(session.created).isoformat()

    if session.description:
        description = session.description
    else:
        description = ''

    metadata = dict(
        collection=session.archive_collection_id,
        title=session.title,
        description=description,
        date=str(isodate),
        contributor=session.group,
        creator="https://open.media",
        mediatype="movies",
        language="eng",
        licenseurl="https://creativecommons.org/licenses/by-sa/4.0/",
        subject=session.category)

    return metadata


def prepare_archive_files(session_files):
    """Creates an array of filepaths for Archive.org API file upload"""
    files = []
    if session_files:
        for session_file in session_files:
            files.append(session_file.filepath)
            update_file_status(session_file, c.FILE_SYNCING)

    return files


def prepare_archive_file_names(session_files):
    """Creates an array of filenames for Archive.org API file deletion"""
    files = []
    if session_files:
        for session_file in session_files:
            files.append(path.basename(session_file.filepath))
            update_file_status(session_file, c.FILE_DELETING)

    return files


def update_remote_archive_id(session_id, archive_id):
    om_api.Sessions().updateArchiveId(session_id=session_id, archive_id=archive_id)


def fix_pdf_files(files):
    """Use mutool to attempt to repair a corrupted pdf file"""
    for filepath in files:
        if ".pdf" in filepath:
            mutool_command = "mutool clean " + filepath + " " + filepath
            print("Attempting to fix: " + filepath)
            call(mutool_command, shell=True)


def get_file_from_filepath(filepath, files):
    file_match = None
    for file in files:
        if file.filepath == filepath:
            file_match = file
    return file_match


def archive_create(archive_id, files, metadata, session, session_files, archive_item_created=False):
    success = True

    for filepath in files:
        active_file = get_file_from_filepath(filepath, session_files)
        file_uploaded = True
        try:
            if not archive_item_created:
                r = upload(archive_id, [filepath], metadata)
            else:
                r = upload(archive_id, [filepath])
        except requests.exceptions.HTTPError as err:
            file_uploaded = False
            update_file_status(active_file, c.FILE_FAILED)
            log(active_file, 'Failed to upload file to archive.org: ' + str(err), c.FILE_FAILED, c.LOG_ERROR)
            if active_file.type == 'video':
                success = False
                log(session, "Failed to add new session to archive.org: " + str(err), c.SESSION_FAILED, c.LOG_ERROR)
                return success

        if r[0].status_code != 200 or not file_uploaded:
            log(active_file, "Failed to upload file to archive.org: " + r[0].reason, c.FILE_FAILED, c.LOG_ERROR)
            if active_file.type == 'video':
                success = False
                log(session, "Failed to add new session to archive.org: " + r[0].reason, c.SESSION_FAILED, c.LOG_ERROR)
                return success
        else:
            archive_item_created = True
            log(active_file, "File uploaded to archive.org", c.FILE_SYNCED)
            update_file_status(active_file, c.FILE_SYNCED)

    if success:
        update_session_status(session, c.SESSION_SYNCED, archive_id)
        update_remote_archive_id(session.id, archive_id)
        log(session, "Session added to archive.org", c.SESSION_SYNCED)
    return success


def archive_update_metadata(archive_id, metadata, session):
    success = True

    m = modify_metadata(archive_id, metadata)
    if m.status_code != 200:
        success = False
        log(session, "Failed to update metadata on archive.org: " + m.reason, c.SESSION_FAILED, c.LOG_ERROR)
    else:
        log(session, "Session metadata updated on archive.org", c.SESSION_SYNCED)
    return success


def archive_update(archive_id, session, session_files, archive_info=False):
    """Adds or updates items on Archive.org via API"""
    success = True

    # archive.org metadata format
    metadata = prepare_archive_metadata(session)

    # archive.org files array format
    files = prepare_archive_files(session_files)

    # not on archive.org, can send metadata and files all at once
    # otherwise we have to send them seperately
    if not session.archive_id and files:
        success = archive_create(archive_id, files, metadata, session, session_files)
    elif session.archive_id:
        if metadata_changed(metadata, archive_info, session):
            success = archive_update_metadata(archive_id, metadata)
        if files:
            success = archive_update_files(archive_id, files, metadata, session, session_files, archive_item_created=True)
    return success


def archive_delete_removed_files(archive_id, session_files, session):
    """Delete files from Archive.org that are no longer present in Open.Media"""
    success = True
    files = prepare_archive_file_names(session_files)

    r = delete(archive_id, files, formats=None, glob_pattern=None, cascade_delete=True)
    if len(r) > 0:
        for response in r:
            if response.status_code != 200:
                success = False
                log(session, "Failed to delete files on archive.org: " + r.reason, c.SESSION_FAILED, c.LOG_ERROR)
        if success:
            log(session, "Files deleted on archive.org", c.SESSION_DELETED)
    else:
        log(session, "No matching files found for deletion on archive.org", c.SESSION_DELETED, c.LOG_WARNING)

    if success:
        for session_file in session_files:
            update_file_status(session_file, c.FILE_DELETED)
            log(session_file, "File deleted on archive.org", c.FILE_DELETED)

    return success


def session_archive_id(session):
    """Generates a unique identifier for archive item: om-om_site_id-om_id"""
    if session.archive_id:
        archive_id = session.archive_id
    else:
        archive_id = "om-" + str(session.site_id) + "-" + str(session.id)

    return archive_id


def sync():
    args = get_args()

    if 'site_id' in args and args.site_id:
        session = ytarchive().sessionsGet(id=None, params={'state': c.SESSION_PROCESSED, 'site_id': args.site_id, 'sort': 'last_updated:asc', 'limit': 1})
    else:
        session = ytarchive().sessionsGet(id=None, params={'state': c.SESSION_PROCESSED, 'sort': 'last_updated:asc', 'limit': 1})

    if session:
        update_session_status(session, c.SESSION_SYNCING)
        log(session, "Session queued for archive.org sync", c.SESSION_SYNCING)

        update_success = True
        delete_success = True
        archive_id = session_archive_id(session)
        archive_info = False
        session_files = ytarchive().filesGet(id=None, params={'session_id': session.id, 'state': c.FILE_PROCESSED})
        # remove any unchanged files and mark them as finished
        if session.archive_id:
            archive_info = get_item(archive_id)
            session_files = finish_unchanged_files(archive_info, session_files)
        update_success = archive_update(archive_id, session, session_files, archive_info)

        # remove any files no longer present on session
        # note that we never delete videos or sessions for permanent backup
        removed_session_files = ytarchive().filesGetRemoved(session.id)
        if removed_session_files:
            delete_success = archive_delete_removed_files(archive_id, removed_session_files, session)

        if not delete_success:
            update_session_status(session, c.SESSION_FAILED)
            log(session, "Failed to delete items from archive.org", c.SESSION_FAILED, c.LOG_ERROR)


sync()

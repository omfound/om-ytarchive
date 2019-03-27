#!/usr/bin/env python3

import constants as c
from internetarchive import get_item
from log import log
from db import ytarchive
from os import path
from pprint import pprint
import shutil


def validate_files(session_files, archive_info):
    """Loop through session item files and check if Open.Media API MD5 matches
    the MD5 stored on Archive.org"""
    session_success = True
    pprint(archive_info)
    pprint(session_files)

    for session_file in session_files:
        session_file_exists = False
        for archive_file in archive_info.item_metadata["files"]:
            session_file_name = path.basename(session_file.filepath)
            if archive_file["md5"] == session_file.md5 and archive_file["name"] == session_file_name:
                if session_file.state == c.FILE_SYNCED:
                    update_session_file_validation(session_file, True)
                    log(session_file, "File validated", c.FILE_SYNCED)
                    session_file_exists = True
                elif session_file.state == c.FILE_DELETED:
                    update_session_file_validation(session_file, False)
                    update_session_file_status(session_file, c.FILE_FAILED)
                    log(session_file, 0, "File not validated, deleted file exists on archive.org", c.FILE_FAILED)
                    session_file_exists = True
                    session_success = False

        if not session_file_exists:
            if session_file.state == c.FILE_DELETED:
                update_session_file_validation(session_file, True)
                log(session_file, "File validated", c.FILE_DELETED)
            else:
                update_session_file_status(session_file, c.FILE_FAILED)
                update_session_file_validation(session_file, False)
                log(session_file, "File not validated, no hash match", c.FILE_FAILED, c.LOG_ERROR)
                session_success = False

    return session_success


def update_session_file_validation(session_file, validated):
    """shortcut to update stored validated status for items"""
    ytarchive().filesUpdate({'id': session_file.id, 'validated': validated})


def update_session_file_status(session_file, status):
    """shortcut to update stored file state"""
    ytarchive().filesUpdate({'id': session_file.id, 'state': status})


def cleanup_files(session):
    """Remove all of the files downloaded during processing"""
    # directory = "/home/ubuntu/ytarchive/process_files/"
    directory = "/transfers/process_files/"
    session_folder = directory + str(session.id)
    shutil.rmtree(session_folder)


def validate():
    """Check all synced files to make sure their md5 hash matches the hash
    stored on Archive.org"""
    synced_session = ytarchive().sessionsGetSyncedOldest()

    if synced_session:
        archive_info = get_item(synced_session.archive_id)
        session_files = ytarchive().filesGetSynced(synced_session.id)
        valid = validate_files(session_files, archive_info)

        if valid:
            ytarchive().sessionsUpdate({'id': synced_session.id, 'validated': True})
            log(synced_session, "Session files validated", c.SESSION_SYNCED)
            cleanup_files(synced_session)
        else:
            ytarchive().sessionsUpdate({'id': synced_session.id, 'state': c.SESSION_FAILED, 'validated': False})
            log(synced_session, "Session files failed validation", c.SESSION_FAILED, c.LOG_ERROR)


validate()

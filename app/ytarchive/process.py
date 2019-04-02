#!/usr/bin/env python3

import constants as c
import requests
import os
import errno
import hashlib
from subprocess import call
from db import ytarchive
from log import log
from args import get_args


def create_directory(filepath):
    """Create a directory if it does not exist"""
    if not os.path.exists(os.path.dirname(filepath)):
        try:
            os.makedirs(os.path.dirname(filepath))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def download_file(url, filepath):
    """Download a file and store to the provided filepath"""
    r = requests.get(url, allow_redirects=True)
    if r.status_code == 404 or r.status_code == 403:
        return False
    elif r.content == "false":
        return False
    else:
        create_directory(filepath)
        open(filepath, 'wb').write(r.content)
        return True


def download_youtube(url, filepath):
    """Download an mp4 from YouTube url via youtube-dl and store to the provided filepath"""
    create_directory(filepath)
    output_arg = "-f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'"
    output_arg += " -o "
    output_arg += filepath

    yt_command = "youtube-dl " + output_arg + " " + url
    retcode = call(yt_command, shell=True)

    if retcode == 0:
        return True
    else:
        return False


def update_session_file_status(session_file, status):
    """Update stored file status and properties based on state"""
    if status == c.FILE_PROCESSED:
        data = {
            'state': status,
            'md5': session_file.md5,
            'id': session_file.id}
    elif status == c.FILE_FETCHED:
        data = {
            'state': status,
            'filepath': session_file.filepath,
            'id': session_file.id}
    else:
        data = {
            'state': status,
            'id': session_file.id}

    ytarchive().filesUpdate(data)


def session_file_extension(session_file_type):
    """Lookup extension based on file type"""
    types = {
        'agenda': 'pdf',
        'journal': 'pdf',
        'minutes': 'html',
        'cuepoints': 'srt',
        'captions': 'srt',
        'video': 'mp4',
        'packet': 'pdf',
        'other': 'pdf'}
    type_extension = types[session_file_type]
    return type_extension


def session_file_filepath(session_file, session_file_type):
    """Derive filepath from metadata"""
    directory = "/transfers/process_files/"
    directory += str(session_file.session_id)
    type_extension = session_file_extension(session_file_type)
    filename = str(session_file.id) + "." + type_extension
    filepath = directory + "/" + filename
    return filepath


def download_session_files(session, session_files):
    """Download and store all files associated with a session item"""
    for key, session_file in enumerate(session_files):
        update_session_file_status(session_file, c.FILE_FETCHING)
        session_file_type = session_file.type.lower()
        filepath = session_file_filepath(session_file, session_file_type)

        # YouTube API does not expose mp4 url, so we use yt_download
        if (session_file_type != "video"):
            result = download_file(session_file.url, filepath)
        else:
            result = download_youtube(session_file.url, filepath)

        if result:
            session_file.filepath = filepath
            session_files[key].filepath = filepath
            update_session_file_status(session_file, c.FILE_FETCHED)
            log(session_file, "File downloaded", c.FILE_FETCHED)
        else:
            # TODO: invalid is pretty vague, eventually we should provide more
            # specific error handling around failed file downloads
            session_files[key].state = c.FILE_INVALID
            update_session_file_status(session_file, c.FILE_INVALID)
            log(session_file, "File invalid or failed to download", c.FILE_INVALID, c.LOG_WARNING)
    return session_files


def md5(filepath):
    """Generates an MD5 hash from provided filepath, supports large files"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def hash_session_files(session, downloaded_session_files):
    """Generate and store md5 hash for each downloaded file"""
    for session_file in downloaded_session_files:
        if session_file.state != c.FILE_INVALID:
            update_session_file_status(session_file, c.FILE_PROCESSING)
            hash_md5 = md5(session_file.filepath)
            session_file.md5 = hash_md5
            update_session_file_status(session_file, c.FILE_PROCESSED)
            log(session_file, "File hashed", c.FILE_PROCESSED)


def process():
    site_id = None
    args = get_args()
    if 'site' in args and args.site:
        site_id = args.site

    """Download files and metadata for the oldest updated session"""
    updated_session = ytarchive().sessionsGetChangedOldest(site_id)

    if updated_session:
        ytarchive().sessionsUpdate({'id': updated_session.id, 'state': c.SESSION_FETCHING})
        log(updated_session, "Files queued for download", c.SESSION_FETCHING)
        updated_session_files = ytarchive().filesGetNewChanged(updated_session.id)
        downloaded_session_files = download_session_files(updated_session, updated_session_files)
        log(updated_session, "Files downloaded locally", c.SESSION_FETCHED)
        ytarchive().sessionsUpdate({'id': updated_session.id, 'state': c.SESSION_PROCESSING})
        hash_session_files(updated_session, downloaded_session_files)
        ytarchive().sessionsUpdate({'id': updated_session.id, 'state': c.SESSION_PROCESSED})
        log(updated_session, "Files hashed", c.SESSION_PROCESSED)


process()

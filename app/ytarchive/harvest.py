#!/usr/bin/env python3

import time
import constants as c
from db import ytarchive
import om_api
from models import Session, VideoFile, CaptionFile, CuepointFile, DocumentFile
from log import log
from args import get_args


def get_live_sessions(site, stored_sessions, last_run_time, created_after):
    """Get sessions from Open.Media API, optionally after the last harvest run
    time
    """

    # start with brand new sessions
    sessions = om_api.Sessions().list(
        site_id=site['site_id'],
        archived="false",
        created_after=created_after,
        video_processed=True)
    sessions = remove_stored_sessions(sessions, stored_sessions)

    # no new sessions, check for updated existing ones
    if len(sessions) <= 0:
        sessions = om_api.Sessions().list(
            site_id=site['site_id'],
            archived="true",
            updated_after=last_run_time,
            video_processed=True)
    return sessions


def remove_stored_sessions(sessions, stored_sessions):
    new_sessions = []
    for index, session in enumerate(sessions):
        if int(session['id']) not in stored_sessions:
            new_sessions.append(session)
    return new_sessions


def get_stored_sessions(site):
    """Get previously stored site sessions to compare against live"""
    stored_sessions = ytarchive().sessionsGet(id=None, params={'site_id': site['site_id']})
    if not stored_sessions:
        stored_sessions = []
    return stored_sessions


def get_stored_files(session):
    """Get previously stored session files to compare against live"""
    stored_files = ytarchive().filesGet(id=None, params={'session_id': session.id})
    return stored_files


def dict_by_id(items):
    """Map an array of items to a dictionary keyed by id to speed
    up comparisons between stored and live
    """
    keyed = {}
    for item in items:
        keyed[item.id] = item

    return keyed


def sessions_map_sessions(sessions):
    """Map Open.Media sessions API entry to session model"""
    ob_sessions = []

    for session in sessions:
        ob_sessions.append(Session(session))

    return ob_sessions


def session_map_file_documents(session):
    """Map Open.Media documents API entry to file model"""
    files = []

    if session.documents:
        for document in session.documents:
            if "id" and "url" in document:
                files.append(DocumentFile(session, document))

    return files


def get_session_files_metadata(session):
    """Create list of file items from Open.Media session API
    results
    """
    files = []

    # currently the session api call only brings in sessions
    # with processed youtube ids, but we may back up non-video content
    # in the future so check is here
    if session.video_url and session.video_id:
        # youtube video
        files.append(VideoFile(session))

        # youtube captions
        captions = om_api.Captions().list(session_id=session.id)

        if captions:
            files.append(CaptionFile(session))

        # cuepoints
        cuepoints = om_api.Cuepoints().list(session_id=session.id)
        if cuepoints:
            files.append(CuepointFile(session))

    if session.documents:
        doc_files = session_map_file_documents(session)

        for doc_file in doc_files:
            files.append(doc_file)

    return files


def get_file_state(file, stored_files):
    """Compare live files vs our stored cache and return their current
    state. States can be found in constants.py"""
    state = c.FILE_NEW

    if file.id not in stored_files:
        state = c.FILE_UNHARVESTED
    else:
        # only update files that are not actively being processed
        current_state = stored_files[file.id].state
        condition = (current_state == c.FILE_NEW or
                     current_state == c.FILE_SYNCED or
                     current_state == c.FILE_INVALID)
        if condition:
            if current_state == c.FILE_NEW:
                state = c.FILE_NEW
            else:
                state = c.FILE_CHANGED
        else:
            state = stored_files[file.id].state
    return state


def store_unharvested_file(file):
    """Insert a new live file into our stored cache"""
    ytarchive().filesInsert({
        'id': file.id,
        'session_id': file.session_id,
        'url': file.url,
        'type': file.type,
        'state': c.FILE_NEW})
    log(file, "New File", c.FILE_NEW)


def update_existing_file(file, state):
    """Update a previously stored file with new metadata from live"""
    ytarchive().filesUpdate({
        'id': file.id,
        'url': file.url,
        'type': file.type,
        'state': state,
        'validated': 0})
    log(file, "Possible change to file", state)


def mark_stored_files_for_removal(stored_files):
    """Mark stored files that have finished processing as removed that are no longer present
    on the live site"""
    for stored_key, stored_file in enumerate(stored_files):
        current_state = stored_file.state
        # avoid deleting files that are actively being processed
        condition = ((current_state == c.FILE_NEW or
                      current_state == c.FILE_SYNCED) and
                     stored_file.validated)

        if condition:
            ytarchive().filesUpdate({
                'id': stored_file.id,
                'url': stored_file.url,
                'type': stored_file.type,
                'state': c.FILE_REMOVED})
            log(stored_file, "File removed", c.FILE_REMOVED)


def store_files(session):
    """Store and update file metadata from new or changed session
    We assume that all files that still exist may have been changed and
    verify this by comparing MD5 during process.py
    """
    stored_files = get_stored_files(session)
    if not stored_files:
        stored_files = []
    else:
        stored_files = dict_by_id(stored_files)

    files = get_session_files_metadata(session)

    for file in files:
        file_state = get_file_state(file, stored_files)

        # store new files
        if file_state == c.FILE_UNHARVESTED:
            store_unharvested_file(file)
        # update new or changed files that are not currently processing
        elif file_state == c.FILE_NEW or file_state == c.FILE_CHANGED:
            update_existing_file(file, file_state)
            del(stored_files[file.id])

    # we removed new and updated files from the currently stored files
    # list above, any remaining should be marked for deletion on archive.org
    mark_stored_files_for_removal(stored_files)


def session_map_item(site, session, stored_sessions, state):
    """Map session API results to an item dict"""
    if session.description:
        description = session.description
    else:
        description = None

    if len(session.categories) > 0:
        category = session.categories[0]['label']
    else:
        category = None

    item = {
        'id': session.id,
        'site_id': int(site['site_id']),
        'archive_collection_id': site['om_user_settings_archive_collection'],
        'group': site['group'],
        'title': session.title,
        'description': description,
        'category': category,
        'created': session.created,
        'last_updated': session.updated,
        'state': state,
        'validated': 0}

    if session.archive_id:
        item['archive_id'] = session.archive_id

    return item


def session_current_state(session, stored_sessions):
    """Get the current state for a session based on live and stored copy"""
    if session.id not in stored_sessions:
        if session.archive_id:
            current_state = c.SESSION_UNMANAGED
        else:
            current_state = c.SESSION_NEW
    else:
        current_state = stored_sessions[session.id].state
    return current_state


def session_next_state(current_state):
    """Get the next state for a session"""
    if current_state == c.SESSION_NEW:
        next_state = c.SESSION_NEW
    elif current_state == c.SESSION_UNMANAGED:
        next_state = c.SESSION_SKIP
    # all sessions that are not new must have been changed as they would
    # otherwise not show up in the api call
    else:
        next_state = c.SESSION_CHANGED
    return next_state


def session_state_message(state):
    """Determine log message based on session state"""
    if state == c.SESSION_NEW:
        message = "New session"
    elif state == c.SESSION_UNMANAGED:
        message = "Session archive information is being manually managed"
    elif state == c.SESSION_SKIPPED:
        message = "Skipping updated unmanaged session"
    else:
        message = "Session changed"
    return message


def session_processing_completed(session, current_state, stored_sessions):
    """Determine if a session has completed processing"""
    condition = ((current_state == c.SESSION_NEW or
                  current_state == c.SESSION_SYNCED) and
                 stored_sessions[session.id].validated)
    if condition:
        return True
    else:
        return False


def store_sessions(site, last_run_time, created_after):
    """Loop through all sessions that have changed since last harvest run and
    update their status in the youtube_archive MySQL database
    """
    # previously harvested sessions
    stored_sessions = get_stored_sessions(site)
    stored_sessions = dict_by_id(stored_sessions)

    # live sessions that have been updated after the last harvest run
    sessions = get_live_sessions(site, stored_sessions, last_run_time, created_after)
    sessions = sessions_map_sessions(sessions)
    results = {'new': [], 'updated': [], 'skipped': []}

    for session in sessions:
        current_state = session_current_state(session, stored_sessions)
        next_state = session_next_state(current_state)
        message = session_state_message(next_state)

        if next_state == c.SESSION_NEW:
            item = session_map_item(site, session, stored_sessions, c.SESSION_NEW)
            ytarchive().sessionsInsert(item)
            results['new'].append(session)
            store_files(session)
        # session is new but already has archive information so we avoid it
        elif next_state == c.SESSION_UNMANAGED:
            item = session_map_item(site, session, stored_sessions, c.SESSION_UNMANAGED)
            ytarchive().sessionsInsert(item)
            results['skipped'].append(session)
        elif next_state == c.SESSION_SKIPPED:
            results['skipped'].append(session)
        # session has been previously imported, check for updates
        else:
            # only update if the session has been changed since last import
            if stored_sessions[session.id].last_updated < session.updated:
                # only update items that are not currently being processed
                if session_processing_completed(session, current_state, stored_sessions):
                    item = session_map_item(site, session, stored_sessions, next_state)
                    ytarchive().sessionsUpdate(item)
                    results['updated'].append(session)
                    store_files(session)
        log(session, message, next_state)
    return results


def last_run_time(site):
    """Get the unix timestamp from the last harvest run for a given site"""
    results = ytarchive().logsGet(id=None, params={'site_id': site['site_id'], 'type': 'harvest_run', 'state': 'harvesting', 'sort': 'time:desc', 'limit': 1})
    if results:
        return results[0].time
    else:
        return time.time()


def log_harvest_run_start(site):
    """Store start time for current site harvest run"""
    ytarchive().logsInsert({
        'time': time.time(),
        'site_id': site['site_id'],
        'type': 'harvest_run',
        'severity': c.LOG_STATUS,
        'message': "Harvest run",
        'state': 'harvesting'
    })


def log_harvest_run_end(site, items_added, items_updated, items_deleted):
    """Stored end time and various operation summary data for finished
    harvest_run
    """
    message = str(items_added) + " items added, " + str(items_updated) + " updated, " + str(items_deleted) + " deleted"
    ytarchive().logsInsert({
        'time': time.time(),
        'site_id': site['site_id'],
        'type': 'harvest_run',
        'severity': c.LOG_STATUS,
        'message': message,
        'state': 'harvested'})


def get_sites(args):
    final_sites = []
    site_ids = ['382', '400']
    if args.site:
        site_ids = [str(args.site)]

    sites = om_api.Sites().list(has_archive_collection=True)

    for site in sites:
        if site['site_id'] in site_ids:
            final_sites.append(site)

    return final_sites


def harvest():
    """Grab all sites from Open.Media API that have a defined archive.org
    collection then store new and updated session information
    """
    args = get_args()
    sites = get_sites(args)
    # 1514764800 = start of 2018
    created_after = 1514764800
    for site in sites:
        the_last_run_time = last_run_time(site)
        log_harvest_run_start(site)
        results = store_sessions(site, the_last_run_time, created_after)
        log_harvest_run_end(site, len(results["new"]), len(results["updated"]), 0)


harvest()

#!/usr/bin/env python3

import time
from db import ytarchive
import constants as c
debug_mode = True


def log(item, message, state=None, severity=c.LOG_STATUS):
    if not state:
        state = item.state

    if hasattr(item, 'session_id'):
        session_id = item.session_id
        file_id = item.id
        type = 'file'
        session = ytarchive().sessionsGet(id=item.session_id)
        site_id = session.site_id
    else:
        session_id = item.id
        file_id = None
        type = 'session'
        site_id = item.site_id

    data = {
        'session_id': session_id,
        'file_id': file_id,
        'severity': severity,
        'message': message,
        'state': state,
        'time': time.time(),
        'type': type,
        'site_id': site_id}

    ytarchive().logsInsert(data)
    if debug_mode:
        print(prepare_console_message(data))


def prepare_console_message(data):
    console_message = str(data['site_id']) + "/" + str(data['session_id']) + " | "
    if 'file_id' in data and data['file_id']:
        console_message += str(data['file_id']) + " - "
    console_message += data['message']
    return console_message

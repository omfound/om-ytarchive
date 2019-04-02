#!/usr/bin/env python3
from app import Base


class Session():
    def __init__(self, session):
        self.id = int(session['id'])
        self.site_id = int(session['site_id'])
        self.created = int(session['created'])
        self.updated = int(session['updated'])
        self.cuepoints_updated = int(session['cuepoints_updated'])
        self.title = session['title']
        self.description = session['description'] if 'description' in session else None
        self.url = session['url'] if 'url' in session else None
        self.date = int(session['date'])
        self.archive_id = session['archive_id']
        self.video_url = session['video_url'] if 'video_url' in session else None
        self.video_id = session['video_id'] if 'video_id' in session else None
        self.documents = session['documents'] if 'documents' in session else None
        self.categories = session['categories']
        self.minutes_status = int(session['minutes_status'])


class VideoFile():
    def __init__(self, session):
        self.session_id = session.id
        self.id = session.video_id
        self.url = session.video_url
        self.type = 'video'


class CaptionFile():
    def __init__(self, session):
        api_url = Base().settings()['om_api']['url']
        captions_id = str(session.id) + "_captions"
        captions_url = api_url + "/session/"
        captions_url += str(session.id)
        captions_url += '/captions-srt'

        self.session_id = session.id
        self.id = captions_id
        self.url = captions_url
        self.type = 'captions'


class CuepointFile():
    def __init__(self, session):
        api_url = Base().settings()['om_api']['url']
        cuepoints_id = str(session.id) + '_cuepoints'
        cuepoints_url = api_url + '/session/'
        cuepoints_url += str(session.id)
        cuepoints_url += '/cuepoints-srt'

        self.session_id = session.id
        self.id = cuepoints_id
        self.url = cuepoints_url
        self.type = 'cuepoints'


class DocumentFile():
    def __init__(self, session, document):
        self.session_id = session.id
        self.id = "doc-" + document['type'].lower() + str(document['id'])
        self.url = document['url']
        self.type = document['type']

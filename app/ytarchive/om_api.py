#!/usr/bin/env python3

import configparser
import requests
from os import path


class OmApi():

    def __init__(self):
        config_path = path.join(path.abspath(path.dirname(__file__)), 'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        self.api_url = config['om_api']['url']
        self.api_key = config['om_api']['key']


class Sites(OmApi):

    def __init__(self):
        OmApi.__init__(self)
        self.endpoint = self.api_url + "/sites?key=" + self.api_key + "&limit=200"

    def list(self, has_archive_collection=None):
        sites_data = requests.get(self.endpoint)
        sites = sites_data.json()
        results = []

        if has_archive_collection is not None:
            for site in sites["results"]:
                if "om_user_settings_archive_collection" in site and has_archive_collection:
                    results.append(site)
                elif "om_user_settings_archive_collection" not in site and not has_archive_collection:
                    results.append(site)
        else:
            results = sites["results"]

        return results


class Sessions(OmApi):

    def __init__(self):
        OmApi.__init__(self)

    def get(self, session_id):
        session_url = self.api_url + "/sessions/" + str(session_id)

        session_data = requests.get(session_url)
        session = session_data.json()
        return session

    def list(self, site_id=None, updated_after=None, video_processed=None, archived=None, created_after=None):
        # craft endpoint
        sessions_url = self.api_url
        if not site_id:
            sessions_url += "/sessions"
        else:
            sessions_url += "/site/" + str(site_id) + "/sessions"

        # build params
        filters = {}
        if updated_after:
            filters['updatedAfter'] = str(updated_after)
        if archived:
            filters['archived'] = archived
        if created_after:
            filters['createdAfter'] = str(created_after)

        sessions_data = requests.get(sessions_url, params=filters)
        sessions = sessions_data.json()
        results = []

        if video_processed is not None:
            for session in sessions["results"]:
                if "video_url" in session:
                    sessionVideo = SessionVideo()
                    processed = sessionVideo.processedStatus(session["id"])
                    if processed and video_processed:
                        results.append(session)
                    elif not processed and not video_processed:
                        results.append(session)
        else:
            results = sessions["results"]
        return results

    def updateArchiveId(self, session_id, archive_id):
        sessions_url = self.api_url + "/sessions/" + str(session_id)
        sessions_url += "?key=" + self.api_key
        requests.post(sessions_url, data={'archive_id': archive_id})


class SessionVideo(OmApi):

    def __init__(self):
        OmApi.__init__(self)

    def processedStatus(self, session_id):
        processed_url = self.api_url + "/session/" + str(session_id) + "/youtube-processed"
        processed_data = requests.get(processed_url)
        processed = processed_data.json()
        processed = processed["results"]["processed"]

        return processed


class Captions(OmApi):
    def __init__(self):
        OmApi.__init__(self)

    def list(self, session_id=None):
        # craft endpoint
        url = self.api_url
        if not session_id:
            url += "/captions"
        else:
            url += "/session/" + str(session_id) + "/captions"

        json_data = requests.get(url)
        data = json_data.json()

        return data['results']


class Cuepoints(OmApi):
    def __init__(self):
        OmApi.__init__(self)

    def list(self, session_id=None):
        # craft endpoint
        url = self.api_url
        if not session_id:
            url += "/cuepoints"
        else:
            url += "/session/" + str(session_id) + "/cuepoints"

        json_data = requests.get(url)
        data = json_data.json()

        return data['results']

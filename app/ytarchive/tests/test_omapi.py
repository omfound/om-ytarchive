#!/usr/bin/env python3
import om_api
test_session_id = 43260
test_site_id = 1


def test_om_api_sites_list():
    sites = om_api.Sites().list(has_archive_collection=True)
    assert len(sites) > 0


def test_om_api_sessions_list():
    sessions = om_api.Sessions().list(site_id=test_site_id)
    assert len(sessions) > 0


def test_om_api_session_get():
    session = om_api.Sessions().get(session_id=test_session_id)
    assert int(session['id']) == test_session_id


def test_om_api_session_video_processed_status():
    status = om_api.SessionVideo().processedStatus(session_id=test_session_id)
    assert status


def test_om_api_captions_list():
    captions = om_api.Captions().list(session_id=test_session_id)
    assert len(captions) > 0


def test_om_api_cuepoints_list():
    cuepoints = om_api.Cuepoints().list(session_id=test_session_id)
    assert len(cuepoints) > 0

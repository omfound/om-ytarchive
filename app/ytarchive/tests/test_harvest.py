#!/usr/bin/env python3
import harvest
import om_api
from models import Session
test_session_id = 43260
test_site_id = 1


def test_get_session_files_metadata_video():
    session = om_api.Sessions().get(session_id=test_session_id)
    session = Session(session)
    files = harvest.get_session_files_metadata(session)
    assert files[0].id == '3QtFoVNX1V0'

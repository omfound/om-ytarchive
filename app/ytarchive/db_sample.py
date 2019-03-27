#!/usr/bin/env python3

from sqlalchemy_declarative import Session, File, Log
from db import ytarchive

session = ytarchive().db

# sample session
new_session = Session(
    id=179,
    site_id=1,
    group="Admin",
    archive_collection_id="coloradochannel",
    archive_id="om-1-179",
    title="Creating a Foundation for Change new title",
    category="City Council",
    state="synced",
    created=1489783849,
    last_updated=1531858777,
    validated=1)
session.add(new_session)
session.commit()

# sample session
new_session = Session(
    id=180,
    site_id=1,
    group="Admin",
    archive_collection_id="coloradochannel",
    archive_id="om-1-180",
    title="Another session title",
    category="City Council",
    state="synced",
    created=1589783849,
    last_updated=1631858777,
    validated=1)
session.add(new_session)
session.commit()


# sample file
new_file = File(
    session_id=179,
    type="captions",
    url="https://dev-ompg.pantheonsite.io/api/session/14920/captions-srt",
    state="invalid",
    id="14920_captions")
session.add(new_file)
session.commit()

# sample log
new_log = Log(
    file_id="14920_captions",
    severity=0,
    message="Updated session",
    state="changed",
    time="1530646442",
    type="metadata",
    session_id=179)
session.add(new_log)
session.commit()

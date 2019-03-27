from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from marshmallow_sqlalchemy import ModelSchema

Base = declarative_base()


class Session(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True, autoincrement=False)
    site_id = Column(Integer)
    group = Column(String(320))
    archive_collection_id = Column(String(320))
    archive_id = Column(String(320))
    title = Column(String(320))
    description = Column(Text)
    category = Column(String(320))
    state = Column(String(32), nullable=False)
    created = Column(Integer, nullable=False)
    last_updated = Column(Integer, nullable=False)
    validated = Column(Boolean, default=0)


class SessionSchema(ModelSchema):
    class Meta:
        model = Session


class File(Base):
    __tablename__ = 'files'
    id = Column(String(120), nullable=False, primary_key=True)
    session_id = Column(Integer, nullable=False)
    type = Column(String(30), nullable=False)
    filepath = Column(String(320))
    url = Column(String(320), nullable=False)
    state = Column(String(32), nullable=False)
    md5 = Column(String(32))
    validated = Column(Boolean, default=0)


class FileSchema(ModelSchema):
    class Meta:
        model = File


class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer)
    file_id = Column(String(120), nullable=False)
    severity = Column(String(32), nullable=False)
    message = Column(String(320), nullable=False)
    state = Column(String(32), nullable=False)
    time = Column(Integer, nullable=False)
    type = Column(String(32), nullable=False)
    session_id = Column(Integer, nullable=False)


class LogSchema(ModelSchema):
    class Meta:
        model = Log

#!/usr/bin/env python3

import configparser
from os import path
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_
from sqlalchemy_declarative import Session, File, Log
import constants as c


class ytarchive():

    def __init__(self):
        config_path = path.join(path.abspath(path.dirname(__file__)), 'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        engine_string = 'mysql://' + config['youtube_archive_db']['user']
        engine_string += ':' + config['youtube_archive_db']['passwd']
        engine_string += '@db:3306/' + config["youtube_archive_db"]["db"]
        engine = create_engine(engine_string)
        DBSession = sessionmaker(bind=engine)
        self.db = DBSession()

    def sessionsGet(self, id=None, params=None):
        query = self.db.query(Session)
        if id:
            results = query.filter_by(id=id).first()
        elif params:
            query = self.addParams(query, Session, params)
            if 'limit' in params and params['limit'] == 1:
                results = query.first()
            else:
                results = query.all()
        else:
            results = query.all()

        self.db.close()
        return results

    def sessionsGetChangedOldest(self, site_id=None):
        query = self.db.query(Session)
        query = query.filter(or_(Session.state == c.SESSION_NEW, Session.state == c.SESSION_CHANGED))

        if site_id:
            query = query.filter(Session.site_id == site_id)

        query = query.order_by(getattr(Session, 'last_updated').asc())
        query = query.limit(1)
        results = query.first()
        self.db.close()
        return results

    def sessionsGetSyncedOldest(self, site_id=None):
        query = self.db.query(Session)
        query = query.filter(or_(Session.state == c.SESSION_SYNCED, Session.state == c.SESSION_DELETED))
        query = query.filter(Session.validated == 0)

        if site_id:
            query = query.filter(Session.site_id == site_id)

        query = query.order_by(getattr(Session, 'last_updated').asc())
        query = query.limit(1)
        results = query.first()
        self.db.close()
        return results

    def sessionsInsert(self, records):
        multiple = True
        if not isinstance(records, (list,)):
            records = [records]
            multiple = False

        for index, record in enumerate(records):
            newSession = Session(**record)
            self.db.add(newSession)
            self.db.commit()
            records[index]['id'] = newSession.id

        self.db.close()
        if not multiple:
            return records[0]
        else:
            return records

    def sessionsUpdate(self, records):
        if not isinstance(records, (list,)):
            records = [records]
        for record in records:
            self.db.query(Session).filter_by(id=record['id']).update(record)
        self.db.commit()
        self.db.close()

    def sessionsDelete(self, id=None, params=None):
        query = self.db.query(Session)
        if id:
            results = query.filter_by(id=id).delete()
        elif params:
            query = self.addParams(query, Session, params)
            results = query.delete()
        else:
            results = query.delete()

        self.db.commit()
        self.db.close()
        return results

    def sessionRevertSynced(self, id=None):
        self.db.query(Session).filter_by(id=id).update({'state': c.SESSION_SYNCED, 'validated': False})
        self.db.commit()
        self.db.query(File).filter_by(session_id=id).update({'state': c.FILE_SYNCED})
        self.db.commit()
        self.db.close()

    def sessionProcessedOldest(self):
        session = self.db.query(Session).filter_by(state=c.SESSION_PROCESSED).order_by(Session.last_updated.asc()).first()
        self.db.close()
        return session

    def filesGet(self, id=None, params=None):
        query = self.db.query(File)
        if id:
            results = query.filter_by(id=id).first()
        elif params:
            query = self.addParams(query, File, params)
            results = query.all()
        else:
            results = query.all()

        self.db.close()
        return results

    def filesGetNewChanged(self, session_id):
        query = self.db.query(File)
        query = query.filter(File.session_id == session_id)
        query = query.filter(or_(File.state == c.FILE_NEW, File.state == c.FILE_CHANGED))
        results = query.all()
        self.db.close()
        return results

    def filesGetRemoved(self, session_id):
        query = self.db.query(File)
        query = query.filter(File.session_id == session_id)
        query = query.filter(File.state == c.FILE_REMOVED)
        query = query.filter(File.type != 'video')
        results = query.all()
        self.db.close()
        return results

    def filesGetSynced(self, session_id):
        query = self.db.query(File)
        query = query.filter(File.session_id == session_id)
        query = query.filter(or_(File.state == c.FILE_SYNCED, File.state == c.FILE_DELETED))
        query = query.filter(File.validated == False)  # noqa: E712
        results = query.all()
        self.db.close()
        return results

    def filesInsert(self, records):
        multiple = True
        if not isinstance(records, (list,)):
            records = [records]
            multiple = False

        for index, record in enumerate(records):
            newFile = File(**record)
            self.db.add(newFile)
            self.db.commit()
            records[index]['id'] = newFile.id

        self.db.close()
        if not multiple:
            return records[0]
        else:
            return records

    def filesUpdate(self, records):
        if not isinstance(records, (list,)):
            records = [records]
        for record in records:
            self.db.query(File).filter_by(id=record['id']).update(record)
        self.db.commit()
        self.db.close()

    def filesDelete(self, id=None, params=None):
        query = self.db.query(File)
        if id:
            results = query.filter_by(id=id).delete()
        elif params:
            query = self.addParams(query, File, params)
            results = query.delete()
        else:
            results = query.delete()

        self.db.commit()
        self.db.close()
        return results

    def logsGet(self, id=None, params=None):
        query = self.db.query(Log)
        if id:
            results = query.filter_by(id=id).first()
        elif params:
            query = self.addParams(query, Log, params)
            results = query.all()
        else:
            results = query.all()
        self.db.close()
        return results

    def logsGetSynced(self, session_id):
        query = self.db.query(Log)
        query = query.filter(Log.session_id == session_id)
        query = query.filter(Log.state == c.SESSION_SYNCED)
        query = query.filter(Log.file_id == None)  # noqa: E711
        result = query.first()
        self.db.close()
        return result

    def logsInsert(self, records):
        multiple = True
        if not isinstance(records, (list,)):
            records = [records]
            multiple = False

        for index, record in enumerate(records):
            newLog = Log(**record)
            self.db.add(newLog)
            self.db.commit()
            records[index]['id'] = newLog.id

        self.db.close()
        if not multiple:
            return records[0]
        else:
            return records

    def logsUpdate(self, records):
        if not isinstance(records, (list,)):
            records = [records]
        for record in records:
            self.db.query(Log).filter_by(id=record['id']).update(record)
        self.db.commit()
        self.db.close()

    def logsDelete(self, id=None, params=None):
        query = self.db.query(Log)
        if id:
            results = query.filter_by(id=id).delete()
        elif params:
            query = self.addParams(query, Log, params)
            results = query.delete()
        else:
            results = query.delete()

        self.db.commit()
        self.db.close()
        return results

    def reset(self):
        self.sessionsDelete()
        self.filesDelete()
        self.logsDelete()

    def addParams(self, query, Model, params):
        for raw_key in params:
            key_parts = self.getKeyParts(raw_key)
            key = key_parts['key']
            op = key_parts['op']

            if hasattr(Model, key):
                column = getattr(Model, key, None)
                values = self.getValues(params, raw_key)
                if len(values) > 1:
                    if op == 'ne':
                        query = query.filter(getattr(Model, key).notin_(values))
                    else:
                        query = query.filter(getattr(Model, key).in_(values))
                else:
                    attr = self.getFilterAttr(column, op)
                    filt = getattr(column, attr)(values)
                    query = query.filter(filt)
            elif 'sort' in key:
                query = self.addSort(query, Model, params)
            elif key == 'limit':
                query = self.addLimit(query, Model, params)
            else:
                raise ValueError("Unknown query parameter: " + key)
        return query

    def getValues(self, params, key):
        if "getlist" in dir(params):
            values = params.getlist(key)
        else:
            values = [params[key]]

        if len(values) == 1:
            if ',' in values[0]:
                values = values[0].split(',')

        return values

    def getFilterAttr(self, column, op):
        try:
            attr = next(filter(
                lambda e: hasattr(column, e % op),
                ['%s', '%s_', '__%s__']
            )) % op
        except StopIteration:
            raise ValueError('Invalid filter operator: %s' % op)
        return attr

    def getKeyParts(self, key):
        processed_key = {'key': key, 'op': 'eq'}

        if ':' in key:
            parts = key.split(':')
            if parts[1]:
                processed_key['key'] = parts[0]
                processed_key['op'] = parts[1]
        return processed_key

    def addLimit(self, query, Model, params):
        value = params.get('limit')
        if self.isInt(value):
            query = query.limit(value)
            return query
        else:
            raise ValueError("Invalid value for limit parameter: " + value)

    def addSort(self, query, Model, params):
        if "getlist" in dir(params):
            values = params.getlist('sort')
        else:
            values = [params['sort']]

        for value in values:
            direction = 'asc'
            parts = value.split(':')
            if len(parts) == 2:
                if parts[1] == 'asc' or parts[1] == 'desc':
                    direction = parts[1]
                    sortkey = parts[0]
            else:
                sortkey = value

            if hasattr(Model, sortkey):
                if direction == 'asc':
                    query = query.order_by(getattr(Model, sortkey).asc())
                elif direction == 'desc':
                    query = query.order_by(getattr(Model, sortkey).desc())
            else:
                raise ValueError("Unknown sort parameter: " + sortkey)
        return query

    def isInt(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False

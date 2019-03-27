#!/usr/bin/env python3

from db import ytarchive
from sqlalchemy_declarative import SessionSchema, FileSchema, LogSchema
from flask.views import MethodView
from flask import request, abort, jsonify
from collections import OrderedDict


class Sessions(MethodView):
    def get(self, id=None):
        try:
            data = ytarchive().sessionsGet(id, request.args)
        except ValueError as e:
            abort(400, str(e))

        schema = SessionSchema() if id else SessionSchema(many=True)
        data = schema.dump(data)

        return response(results=data, id=id, type='session')


class Files(MethodView):
    def get(self, id=None):
        try:
            data = ytarchive().filesGet(id, request.args)
        except ValueError as e:
            abort(400, str(e))

        schema = FileSchema() if id else FileSchema(many=True)
        data = schema.dump(data)

        return response(results=data, id=id, type='file')


class Logs(MethodView):
    def get(self, id=None):
        try:
            data = ytarchive().logsGet(id, request.args)
        except ValueError as e:
            abort(400, str(e))

        schema = LogSchema() if id else LogSchema(many=True)
        data = schema.dump(data)

        return response(results=data, id=id, type='log')


def response(results, id, type):
    if not results.data:
        if id is None:
            abort(404, "No " + type + "s found")
        else:
            abort(404, "No " + type + " found with the id: " + id)
    else:
        response = OrderedDict(
            size=len(results.data),
            results=results.data
        )
        return jsonify(response), 200

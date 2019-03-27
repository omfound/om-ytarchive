#!/usr/bin/env python3

from flask import Flask
from api_resources import Sessions, Files, Logs
import configparser
from os import path

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

session_view = Sessions.as_view('sessions')
app.add_url_rule('/api/sessions/', defaults={'id': None}, view_func=session_view, methods=['GET', ])
app.add_url_rule('/api/sessions/<string:id>', view_func=session_view, methods=['GET', ])

file_view = Files.as_view('files')
app.add_url_rule('/api/files/', defaults={'id': None}, view_func=file_view, methods=['GET', ])
app.add_url_rule('/api/files/<string:id>', view_func=file_view, methods=['GET', ])

log_view = Logs.as_view('logs')
app.add_url_rule('/api/logs/', defaults={'id': None}, view_func=log_view, methods=['GET', ])
app.add_url_rule('/api/logs/<string:id>', view_func=log_view, methods=['GET', ])


class Base():

    def __init__(self):
        config_path = path.join(path.abspath(path.dirname(__file__)), 'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        self.config = config

    def settings(self):
        return self.config


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

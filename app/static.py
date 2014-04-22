# -*- coding: utf-8 -*-
"""
    app.static
    ~~~~~~~~~~

    Manage the static assets for the Kibera School Project.

    This module injects the right css and javascript for templates.

"""

import os
import urllib
import requests
from hashlib import sha1
from cssmin import cssmin as cssmin_func
from flask import Markup
from . import app


def static_config():
    return {
        'tag_templates': {
            'css': '<link rel="stylesheet" href="{}" />',
            'js':'<script src="{}"></script>',
        },
        'build_filters': {
            'css': (concatenate, cssmin),
            'js': (concatenate, closure),
        }
    }


def concatenate(sources):
    combined = '\n'.join(sources)
    return [combined]


def cssmin(sources):
    return map(cssmin_func, sources)


def closure(sources):
    return [sources[0]]


def load_static_files(type_name, filenames):
    sources = []
    folder_path = os.path.join(app.root_path, 'static', type_name)
    for filename in filenames:
        file_path = os.path.join(folder_path, filename)
        with open(file_path) as file_object:
            source = file_object.read()
            sources.append(source)
    return sources


def apply_filters(type_name, sources):
    filters = static_config()['build_filters'][type_name]
    for filter_func in filters:
        sources = filter_func(sources)
    return sources


def save_sources(type_name, sources):
    build_folder = os.path.join(app.root_path, 'static', 'compiled', type_name)
    try:
        os.makedirs(build_folder)
    except IOError:
        pass
    filenames = []
    for source in sources:
        hashed = sha1(bytes(source, 'utf-8')).hexdigest()
        filename = '{}.{}'.format(hashed, type_name)
        file_path = os.path.join(build_folder, filename)
        with open(file_path, 'w') as file_obj:
            file_obj.write(source)
        filenames.append(filename)
    return filenames


def render_tags(type_name, filenames):
    template = static_config()['tag_templates'][type_name]
    tags = []
    for filename in filenames:
        if app.config.get('FREEZING') is True:
            url = '/compiled/'
        else:
            url = '/static/'
        url += '{}/{}'.format(type_name, filename)
        tag = template.format(url)
        tags.append(tag)
    return Markup('\n'.join(tags))


def static(type_name, filenames):
    sources = load_static_files(type_name, filenames)
    if app.config.get('FREEZING') is True:
        sources = apply_filters(type_name, sources)
        filenames = save_sources(type_name, sources)
    return render_tags(type_name, filenames)

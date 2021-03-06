# -*- coding: utf-8 -*-
"""
    app.content
    ~~~~~~~~~~~

    Load raw content for generating pages

    Content comes from folders in the `content` folder. It is expected that
    these subfolders each represent a sort of type of content, with all data
    contained being of the same type.

    One function should be written for each folder, decorated by
    `load(type_name)`. It should return some kind of object representing all
    of the content of that type.

    That object will be keyed by `type_name` into an importable dict in this
    module, called `content`.

    At present, all content is loaded at import time.

"""

import os
import re
import json
import codecs
import unicodedata
import datetime
from markdown import markdown, Markdown  # quick-use, extensions-able


content = {}
content_path = 'content'


meta_converters = {
    'noop': lambda x: x,
    'iso-date': lambda x: [datetime.date(*map(int, t.split('-'))) for t in x],
    'float': lambda x: map(float, x),
    'slugify': lambda x: [s.lowercase().replace(' ', '-') for s in x],
    'one': lambda x: x[0],
}


class Markup(str):
    def __html__(self):
        return self


def slugify(value):
    """Converts to lowerase, removes non-word characters, spaces to hyphens

    Borrowed from django -- http://djangoproject.org -- BSD? licensed
    """
    value = unicodedata.normalize('NFKD', value).\
                        encode('ascii', 'ignore').\
                        decode('ascii')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[-\s]+', '-', value)
    return value


class MetaError(ValueError):
    """Errors arising from reading metadata"""
    def apply_context(self, **context):
        contextualized_message = self.message.format(**context)
        self.__init__(contextualized_message)


def apply_field_constraints(field_val, required, filters):
    if field_val is None:
        if required is True:
            raise KeyError('The blog {filename} is missing metadata: {field}')
        return None
    else:
        filtered = field_val
        for filter_name in reversed(filters):
            try:
                filtered = meta_converters[filter_name](filtered)
            except Exception as e:
                raise MetaError('Metadata {{field}} for blog post {{filename}}'
                                ' has issues:\n{}'.format(e))
        return filtered


def get_file_pairs(folder_path):
    """Provide (file_object, filename) pairs for all files in a given path.

    This is a generator, you can iterate it.
    """
    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        try:
            with codecs.open(file_path, 'r', encoding='utf-8') as file_object:
                yield file_object, filename
        except IOError as e:
            raise e  # todo: handle these nicely and make nice error messages


def load(type_name):
    """Wrap the loading procedure of each folder/type of content.

    This decorator handles file I/O and object storage for the decorated
    functions.

    The wrapped function should take a single parameter which must match the
    name of the folder.

    Its return value must represent all of the content for that content type.

    The decorated function will be called once, and will be passed an iterable
    of tuples of `(fileObj, filename)` pairs, one for each file present in its
    folder.
    """

    assert type_name not in content, 'Content loader collision: {} already '\
                                     'has a loader'.format(type_name)

    def loader_decorator(loader_func):
        path = os.path.join(content_path, type_name)
        assert os.path.isdir(path), '{} does not seem to be a folder in {}'\
                                    .format(type_name, content_path)
        file_pairs = get_file_pairs(path)

        content[type_name] = loader_func(file_pairs)

        return loader_func  # probably never used since it's called above
                            # ...kind of an abuse of decorators, I know...
    return loader_decorator


def validate_school_geo(school_geo, _seen=set()):
    """Validate the geojson data as it comes in."""
    assert school_geo['type'] == 'Feature'
    assert school_geo['geometry']['type'] == 'MultiPoint'
    assert 'properties' in school_geo
    properties = school_geo['properties']
    assert 'id' in properties
    _id = properties['id'].rsplit('/', 1)[1]
    assert _id not in _seen
    _seen.add(_id)
    assert 'name' in properties
    school_text_slug = slugify(properties['name'])
    school_geo['slug'] = '{}/{}'.format(_id, school_text_slug)


@load('schools')
def load_schools(school_stuff):
    """Load many schools' data from each (and likely only one) geojson file."""
    schools = []
    seen_slugs = set()
    for school_file, filename in school_stuff:
        school_data = json.load(school_file)
        for school_geojson in school_data['features']:
            validate_school_geo(school_geojson)
            schools.append(school_geojson)
    return schools


@load('videos')
def load_videos(video_stuff):
    videos = []
    for vid_file, _ in video_stuff:
        vid_data = json.load(vid_file)
        videos.extend(vid_data)
    return videos


@load('stories')
def load_stories(story_stuff):
    meta = {
        'title':       (True, ('one',)),
        'description': (True, ('one',))
    }
    markdowner = Markdown(extensions=['meta'], output_format='html5')
    stories = []
    for story_file, filename in story_stuff:
        story = {}
        html = markdowner.convert(story_file.read())  # also loads metadata
        story['body'] = Markup(html)
        story['slug'] = os.path.splitext(filename)[0]

        for field, (required, filters) in meta.items():
            field_val = markdowner.Meta.get(field)
            try:
                val = apply_field_constraints(field_val, required, filters)
            except MetaError as e:
                e.apply_context(filename, field)
                raise e
            story[field] = val

        stories.append(story)
        markdowner.reset()

    return stories


@load('social')
def load_social(social_stuff):
    profiles = []
    for social_file, _ in social_stuff:
        social_data = json.load(social_file)
        profiles.extend(social_data)
    return profiles

# -*- coding: utf-8 -*-

import logging
from os import path as op
import re
from time import time


_ENTITIES = [
    ('&', ['&amp;', '&#x26;', '&#38;']),
    ('<', ['&lt;', '&#x3C;', '&#60;']),
    ('>', ['&gt;', '&#x3E;', '&#62;']),
    ('"', ['&quot;', '&#x22;', '&#34;']),
    ('\'', ['&#x27;', '&#39;']),
    ('/', ['&#x2F;', '&#47;']),
]


def _cleanpath(*args):
    parts = [args[0].strip()]

    for arg in args[1:]:
        parts.append(arg.strip(' \t\n\r\v\f' + op.sep))

    return parts


def abspath(*args):
    return op.realpath(
        op.expanduser(
            op.join(
                *_cleanpath(*args)
            )
        )
    )


def escape(html):
    for match, replacements in _ENTITIES:
        html = html.replace(match, replacements[0])

    return html


def get_logger(name):
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()

        logger.addHandler(handler)

    return logger


def normpath(*args):
    return op.normpath(
        op.join(
            *_cleanpath(*args)
        )
    )


def unescape(html):
    for replace, matches in _ENTITIES:
        for match in matches:
            html = html.replace(match, replace)

    return html


def dest_path(dest_root, url):
    parts = [dest_root] + url.split('/')

    if url.endswith('/'):
        parts.append('index.html')

    path = normpath(*parts)

    if op.commonprefix((dest_root, path)) != dest_root:
        raise ConfigException('Invalid URL.',
            'url: {0}'.format(url),
            'path traversal is not allowed')

    return path


class Timer(object):
    _start = []

    @classmethod
    def start(cls):
        cls._start.append(time())

    @classmethod
    def stop(cls):
        return time() - cls._start.pop()


class Url(object):
    @staticmethod
    def join(*args):
        url = '/'.join(args)

        if not re.match(r'[^/]+://', url):
            url = '/' + url

        return re.sub(r'(?<!:)//+', '/', url)

    @staticmethod
    def slugify(string):
        slug = re.sub(r'\s+', '-', string.strip())
        slug = re.sub(r'[^a-z0-9\-_.]', '', slug, flags = re.I)

        return slug

    @classmethod
    def format(cls, url, clean):
        if clean:
            return cls.join(url, '')

        return '{0}.html'.format(url)

    @classmethod
    def from_format(cls, format, text, date = None, data = None):
        clean = format.endswith('/')
        slug = cls.slugify(text)

        if '<slug>' in format:
            url = format.replace('<slug>', slug)
        else:
            url = cls.join(format, slug)

        if date is not None:
            subs = {
                '<year>': '%Y',
                '<month>': '%m',
                '<day>': '%d',
                '<i_month>': str(date.month),
                '<i_day>': str(date.day)
            }

            url = url.replace('%', '%%')

            for match, replace in subs.items():
                url = url.replace(match, replace)

            url = date.strftime(url)

        if data is not None:
            for attribute, value in data.items():
                if isinstance(value, str):
                    url = url.replace('<{0}>'.format(attribute), cls.slugify(value))

        if clean:
            return cls.join(url, '')

        return '{0}.html'.format(url)

    @classmethod
    def from_path(cls, root, text):
        name = '{0}.html'.format(cls.slugify(text))

        return normpath(root, name)

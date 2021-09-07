# -*- coding: utf-8 -*-

from collections import OrderedDict
from datetime import datetime
from itertools import tee, chain
from pathlib import Path
from collections import namedtuple

import os.path as op
import yaml

from peppermynt.exceptions import ConfigException
from peppermynt.fs import Directory
from peppermynt.utils import get_logger, dest_path, normpath, Url


yaml.add_constructor('tag:yaml.org,2002:str', lambda loader, node: loader.construct_scalar(node))

logger = get_logger('mynt')


class Config(dict):
    def __init__(self, string):
        super(Config, self).__init__()

        try:
            self.update(yaml.load(string))
        except yaml.YAMLError:
            raise ConfigException('Config contains unsupported YAML.')
        except:
            logger.debug('..  config file is empty')
            pass


class SiteContent(namedtuple('SiteContentBase', 'posts containers pages feeds')):
    pass


class Data:
    def __init__(self, *, items, archives, tags):
        self.items = items
        self.archives = archives
        self.tags = tags

    def __iter__(self):
        return self.items.values().__iter__()

    def sort_items(self, key, reverse=False):
        def sort_key(url_and_item):
            _, item = url_and_item
            try:
                attribute = item.get(key, item)
            except AttributeError:
                attribute = getattr(item, key, item)

            if isinstance(attribute, str):
                return attribute.lower()

            return attribute

        self.items = OrderedDict(sorted(self.items.items(), key=sort_key, reverse=reverse))


class Item(dict):
    # Typical keys:
    # 'date', 'timestamp', 'tags', 'url', 'layout', 'title', 'summary', 'prev', 'next'
    # 'raw_content' is the markdown input; it gets replaced with 'content' when the item is parsed
    def __init__(self, src, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)

        self.__src = src

    def __str__(self):
        return self.__src

    def output_path(self, dest_root):
        return dest_path(dest_root, self['url'])

    def extension(self):
        return op.splitext(op.basename(self.__src))[1]

    def read_content(self, output_file_path):
        if not self.get('content', None):
            with open(output_file_path, 'r', encoding='utf-8') as output_file:
                self['content'] = output_file.read().strip()
        return self['content']


class Tag:
    def __init__(self, name, url, count, items, archives):
        self.name = name
        self.url = url
        self.count = count
        self.items = items
        self.archives = archives

    def __iter__(self):
        return self.items.__iter__()


class Page(namedtuple('PageBase', 'template data url')):
    def identifier(self):
        return self.url or self.template


class Container:
    def __init__(self, name, src, config):
        self._pages = None

        self.name = name
        self.path = src
        self.config = {} if config is None else config
        self.data = Data(items=OrderedDict(), archives=OrderedDict(), tags=OrderedDict())

    def _get_pages(self):
        pages = []

        for item in self.items:
            if item['layout'] is None:
                continue

            pages.append(Page(item['layout'], {'item': item}, item['url']))

        return pages

    def add(self, item):
        self.data.items[item['url']] = item

    def archive(self):
        pass

    def sort(self):
        pass

    def tag(self):
        pass

    @property
    def archives(self):
        return self.data.archives

    @property
    def items(self):
        return list(self.data.items.values())

    @property
    def pages(self):
        if self._pages is None:
            self._pages = self._get_pages()

        return self._pages

    @property
    def tags(self):
        return self.data.tags


class Items(Container):
    _sort_order = {
        'asc': False,
        'desc': True
    }

    def __init__(self, name, src, config):
        super(Items, self).__init__(name, src, config)

        self.path = Directory(normpath(src.path, '_containers', self.name))

    def _archive(self, items, archive):
        for item in items:
            year, month = datetime.utcfromtimestamp(item['timestamp']).strftime('%Y %B').split()

            if year not in archive:
                archive[year] = {
                    'months': OrderedDict({month: [item]}),
                    'url': Url.from_format(self.config['archives_url'], year),
                    'year': year
                }
            elif month not in archive[year]['months']:
                archive[year]['months'][month] = [item]
            else:
                archive[year]['months'][month].append(item)

    def _get_pages(self):
        pages = super(Items, self)._get_pages()

        if self.config['archive_layout'] and self.archives:
            for archive in self.archives.values():
                pages.append(Page(
                    self.config['archive_layout'],
                    {'archive': archive},
                    archive['url']
                ))

        if self.config['tag_layout'] and self.tags:
            for tag in self.tags.values():
                pages.append(Page(
                    self.config['tag_layout'],
                    {'tag': tag},
                    tag.url
                ))

        return pages

    def _relate(self):
        def pairwise(iterable):
            "s -> (s0,s1), (s1,s2), (s2, s3), ..."
            a, b = tee(iterable)
            a = chain([None], a)
            b = chain(b, [None])
            return zip(a, b)

        for item1, item2 in pairwise(self.items):
            if self._sort_descending():
                this_item, next_item = item1, item2
            else:
                next_item, this_item = item1, item2

            if this_item:
                this_item['next'] = next_item

            if next_item:
                next_item['prev'] = this_item

    def archive(self):
        self._archive(self.items, self.archives)

        for tag in self.tags.values():
            self._archive(tag.items, tag.archives)

    def sort(self):
        self.data.sort_items(
            key=self.config['sort'],
            reverse=self._sort_descending()
        )
        self._relate()

    def _sort_descending(self):
        return self._sort_order.get(self.config['order'].lower(), False)

    def tag(self):
        tags = []

        for item in self.items:
            item['tags'].sort(key=lambda s: s.lower())

            for tag in item['tags']:
                if tag not in self.tags:
                    self.tags[tag] = []

                self.tags[tag].append(item)

        for name, items in self.tags.items():
            tags.append(Tag(
                name,
                Url.from_format(self.config['tags_url'], name),
                len(items),
                items,
                OrderedDict()
            ))

        tags.sort(key=lambda item: (-item.count, item.name))

        self.tags.clear()

        for tag in tags:
            self.tags[tag.name] = tag


class Posts(Items):
    def __init__(self, src, site):
        super(Posts, self).__init__('posts', src, self._get_config(site))

        self.path = Directory(normpath(src.path, '_posts'))

    def _get_config(self, site):
        config = {
            'archives_url': 'archives_url',
            'archive_layout': 'archive_layout',
            'order': 'posts_order',
            'sort': 'posts_sort',
            'tags_url': 'tags_url',
            'tag_layout': 'tag_layout',
            'url': 'posts_url'
        }

        for k, v in config.items():
            config[k] = site.get(v)

        return config

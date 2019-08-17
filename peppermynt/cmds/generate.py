#!/usr/bin/env python

from doit.cmd_run import Run as DoitRun

OPT_BASE_URL = {
    'name': 'base-url',
    'short': None,
    'long': 'base-url',
    'type': str,
    'help': 'Sets the site\'s base URL, overriding the config setting.'
}

OPT_LOCALE = {
    'name': 'locale',
    'short': None,
    'long': 'locale',
    'type': str,
    'help': 'Sets the locale used by the renderer.'
}

OPT_CLEAN = {
    'name': 'clean',
    'short': 'c',
    'long': 'clean',
    'type': bool,
    'default': False,
    help: 'Forces generation by deleting the destination if it exists.'
}

OPT_FORCE = {
    'name': 'force',
    'short': 'f',
    'long': 'force',
    'type': bool,
    'default': False,
    help: 'Forces generation by emptying the destination if it exists.'
}


class GenerateBase(DoitRun):
    doc_purpose = "generate a website"
    doc_usage = "SRC DEST"
    doc_description = None
    execute_tasks = True

    cmd_options = (
        OPT_BASE_URL,
        OPT_LOCALE,
        OPT_CLEAN,
        OPT_FORCE
    )


# aliasing Gen = Generate doesn't work, alas
class Gen(GenerateBase):
    pass


class Generate(GenerateBase):
    pass

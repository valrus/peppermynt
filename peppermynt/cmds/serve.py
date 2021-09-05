#!/usr/bin/env python

from os import chdir, getcwd

from doit.cmd_base import Command

from ..exceptions import OptionException
from ..fs import Directory
from ..server import RequestHandler, Server
from ..utils import Url, get_logger


class Serve(Command):
    def __init__(self, *args, **kwargs):
        self.logger = get_logger('peppermynt')
        super().__init__(*args, **kwargs)
        peppermynt = self.config['PEPPERMYNT']['peppermynt']
        self.args = peppermynt.args
        self.src = Directory(self.args.src)
        self.server = None

    def execute(self, params, args):
        base_url = Url.join(self.args.base_url, '')

        if not self.src.exists:
            raise OptionException('Source must exist.')

        self.logger.info('>> Serving at 127.0.0.1:%s', self.args.port)
        self.logger.info('Press ctrl+c to stop.')

        cwd = getcwd()
        self.server = Server(('', self.args.port), base_url, RequestHandler)

        chdir(self.src.path)

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()
            chdir(cwd)

            # why?
            print('')

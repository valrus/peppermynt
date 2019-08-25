#!/usr/bin/env python

from time import sleep

from doit.cmd_auto import Auto as DoitAuto
from doit.cmd_base import Command
from watchdog.observers import Observer

from ..fs import Directory, EventHandler
from ..exceptions import OptionException
from ..utils import get_logger


class PeppermyntWatchCmd(Command):
    def __init__(self, *args, **kwargs):
        self.logger = get_logger('peppermynt')
        super().__init__(*args, **kwargs)
        self.peppermynt = self.config['PEPPERMYNT']['peppermynt']
        self.args = self.peppermynt.args
        self.src = Directory(self.args.src)
        self.dest = Directory(self.args.dest)

        self.observer = None

    def execute(self, params, args):
        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not args.force:
            raise OptionException('Destination already exists.',
                'the -f flag must be passed to force watching by emptying the destination every time a change is made')

        self.logger.info('>> Watching')
        self.logger.info('Press ctrl+c to stop.')

        self.observer = Observer()

        self.observer.schedule(EventHandler(self.src.path, self.peppermynt.regenerate), self.src.path, True)
        self.observer.start()

        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()

            print('')

        self.observer.join()


class WatchBase(DoitAuto):
    pass


class Watch(WatchBase):
    pass

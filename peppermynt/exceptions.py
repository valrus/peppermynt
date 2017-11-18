# -*- coding: utf-8 -*-


class PeppermyntException(Exception):
    code = 1

    def __init__(self, message, *args):
        self.message = message
        self.debug = args

    def __str__(self):
        message = '!! {0}'.format(self.message)

        for d in self.debug:
            message += '\n..  {0}'.format(d)

        return message


class ConfigException(PeppermyntException):
    pass

class ContentException(PeppermyntException):
    pass

class FileSystemException(PeppermyntException):
    pass

class OptionException(PeppermyntException):
    code = 2

class ParserException(PeppermyntException):
    pass

class RendererException(PeppermyntException):
    pass

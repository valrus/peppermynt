# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import sys

from peppermynt.core import Peppermynt
from peppermynt.exceptions import PeppermyntException


def main():
    try:
        Peppermynt()
    except PeppermyntException as e:
        print(e)

        return e.code

    return 0


if __name__ == '__main__':
    sys.exit(main())

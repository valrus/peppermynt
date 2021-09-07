# -*- coding: utf-8 -*-

import sys

from peppermynt.core import Peppermynt, DoitPeppermynt
from peppermynt.exceptions import PeppermyntException


def main():
    try:
        peppermynt = Peppermynt(args=sys.argv[1:])
        DoitPeppermynt(peppermynt).run(peppermynt.doit_args)
    except PeppermyntException as e:
        print(e)

        return e.code

    return 0


if __name__ == '__main__':
    sys.exit(main())

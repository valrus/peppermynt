#!/usr/bin/env python

from doit.cmd_run import Run as DoitRun

class GenerateBase(DoitRun):
    doc_purpose = "generate a website"
    doc_usage = "SRC DEST"
    doc_description = None
    execute_tasks = True


# aliasing Gen = Generate doesn't work, alas
class Gen(GenerateBase):
    pass


class Generate(GenerateBase):
    pass

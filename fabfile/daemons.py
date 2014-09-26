#!/usr/bin/env python

from time import sleep

from fabric.api import execute, task

import app_config

@task
def liveblog():
    """
    Fetch new Tumblr posts indenfinitely.
    """
    while True:
        execute('liveblog.update')
        execute('deploy_slides')
        sleep(app_config.TUMBLR_REFRESH_INTERVAL)

@task
def stack():
    """
    Rotate slides indenfinitely.
    """
    while True:
        execute('stack.rotate')
        sleep(app_config.SLIDE_ROTATE_INTERVAL)

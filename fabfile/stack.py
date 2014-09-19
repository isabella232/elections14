#!/usr/bin/env python

import json

from fabric.api import env, local, require, task

import app_config
from models import SlideSequence
from utils import deploy_json

STACK_NUMBER_FILENAME = '.stack_number'

@task
def rotate():
    """
    Rotate to the next slide in the sequence.
    """
    require('settings', provided_by=['production', 'staging'])

    try:
        with open(STACK_NUMBER_FILENAME, 'r') as f:
            stack_number = int(f.read().strip())
    except IOError:
        stack_number = 0

    slides = SlideSequence.select().count()

    if stack_number == slides:
        stack_number = 0

    next_slide = SlideSequence.get(SlideSequence.sequence == stack_number)
    stack_number += 1

    with open('www/%s' % app_config.NEXT_SLIDE_FILENAME, 'w') as f:
        json.dump({
            'next': 'slides/%s.html' % next_slide.slide.slug,
        }, f)

    with open(STACK_NUMBER_FILENAME, 'w') as f:
        f.write(unicode(stack_number))

    if env.settings:
        deploy_json(
            'www/%s' % app_config.NEXT_SLIDE_FILENAME,
            app_config.NEXT_SLIDE_FILENAME
        )

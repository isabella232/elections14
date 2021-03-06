#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import copy
import json

import argparse
from flask import Flask, render_template

import app_config
import app_utils
from app_utils import get_last_updated
from render_utils import make_context, smarty_filter, urlencode_filter
import slides
import static_app
import static_theme

app = Flask(__name__)

app.jinja_env.filters['smarty'] = smarty_filter
app.jinja_env.filters['urlencode'] = urlencode_filter

@app.template_filter()
def format_board_time(dt):
    """
    Format a time for the big board
    """
    if not dt:
        return ''

    return '{d:%l}:{d.minute:02}'.format(d=dt) + ' EST'

@app.template_filter()
def format_percent(num):
    """
    Format a percentage
    """
    return int(round(num))

@app.template_filter()
def format_precincts_percent(num):
    """
    Format a percentage for precincts reporting
    """
    if num > 0 and num < 1:
        return '<1'
    if num > 99 and num < 100:
        return '>99'
    else:
        return int(round(num))

@app.template_filter()
def signed(num):
    """
    Add sign to number (e.g. +1, -1)
    """
    return '{0:+d}'.format(num)

@app.route('/')
def index():
    """
    Example view demonstrating rendering a simple HTML page.
    """
    from models import Race

    context = make_context()

    with open('data/featured.json') as f:
        context['featured'] = json.load(f)

    context['races'] = Race.select()

    """
    Balance of Power data
    """
    races = Race.select().where(Race.office_name == 'U.S. Senate').order_by(Race.state_postal)

    context['not_called'] = app_utils.calculate_seats_left(races)

    if app_config.DEPLOY_PROMO:
        template_file = 'promo.html'
    else:
        template_file = 'index.html'

    return render_template(template_file, **context), 200,

@app.route('/promo/')
def promo():
    """
    Test promo template.
    """
    return render_template('promo.html', **make_context())

@app.route('/board/<slug>/')
def _big_board(slug):
    """
    Preview a slide outside of the stack.
    """
    context = make_context()

    context['body'] = _slide(slug).data

    if slug == 'senate-big-board':
        title = 'U.S. Senate'
    elif slug == 'house-big-board-one':
        title = 'U.S. House 1'
    elif slug == 'house-big-board-two':
        title = 'U.S. House 2'
    elif slug == 'governor-big-board':
        title = 'Governors'
    elif slug == 'ballot-measures-big-board':
        title = 'Ballot measures'

    context['title'] = title

    return render_template('_big_board_wrapper.html', **context)

@app.route('/bop.html')
@app_utils.cors
def _bop():
    """
    Serve the most recent bop data
    """
    from models import Race

    context = make_context()

    races = Race.select().where(Race.office_name == 'U.S. Senate').order_by(Race.state_postal)

    context['bop'] = app_utils.calculate_bop(races, app_utils.SENATE_INITIAL_BOP)
    context['not_called'] = app_utils.calculate_seats_left(races)

    return render_template('bop.html', **context)

@app.route('/live-data/stack.json')
@app_utils.cors
def _stack_json():
    """
    Serve up the current slide stack.
    """
    from models import SlideSequence

    data = SlideSequence.stack()

    # There is one state slug to manipulate in the stack, but the client
    # should see two
    for i, d in enumerate(data):
        if d['slug'] == 'state-house-results':
            one = copy(d)
            one['slug'] = 'state-house-results-1'

            two = copy(d)
            two['slug'] = 'state-house-results-2'

            data[i:i + 1] = [
                one,
                two
            ]

            break


    js = json.dumps(data)

    return js, 200, { 'Content-Type': 'application/javascript' }

@app.route('/preview/state-house-results/index.html')
@app.route('/preview/state-senate-results/index.html')
def _state_picker_preview():
    """
    Preview a state slide outside of the stack.
    """
    context = make_context()

    return render_template('_state_picker_preview.html', **context)

@app.route('/preview/state-house-results-<string:slug>-<int:page>/index.html')
@app_utils.cors
def _state_house_slide_preview(slug, page):
    """
    Preview a state slide outside of the stack.
    """
    context = make_context()

    context['body'] = _state_house_slide(slug, page).data

    return render_template('slide_preview.html', **context)

@app.route('/preview/state-senate-results-<slug>/index.html')
@app_utils.cors
def _state_senate_slide_preview(slug):
    """
    Preview a state slide outside of the stack.
    """
    context = make_context()

    resp = _state_senate_slide(slug)
    if resp.status_code == 200:
        context['body'] = resp.data
        return render_template('slide_preview.html', **context)
    else:
        return "404", 404

@app.route('/preview/<slug>/index.html')
@app_utils.cors
def _slide_preview(slug):
    """
    Preview a slide outside of the stack.
    """
    from models import SlideSequence

    context = make_context()

    sequence = SlideSequence.select()

    for slide in sequence:
        if slide.slide.slug == slug:
            context['in_sequence'] = True
            previous_slide_order = slide.order - 1
            next_slide_order = slide.order + 1
            break
    try:
        context['previous_slide'] = SlideSequence.get(SlideSequence.order == previous_slide_order).slide.slug
    except:
        pass

    try:
        context['next_slide'] = SlideSequence.get(SlideSequence.order == next_slide_order).slide.slug
    except:
        pass

    context['body'] = _slide(slug).data.decode('utf-8')
    context['slug'] = slug

    return render_template('slide_preview.html', **context)

@app.route('/slides/state-house-results-<string:slug>-<int:page>.html')
@app_utils.cors
def _state_house_slide(slug, page):
    """
    Serve a state slide.
    """
    from models import Race, Slide

    slide = Slide.get(Slide.slug == 'state-house-results')

    slug = slug.upper()

    races = Race.select().where(
        (Race.office_name == 'U.S. House') &
        (Race.state_postal == slug)
    ).order_by(Race.seat_number)

    timestamp = get_last_updated(races)
    context = make_context(timestamp=timestamp)

    context['slide_class'] = 'state-house'
    context['state_postal'] = slug
    context['state_name'] = app_config.STATES.get(slug)

    # Calculate BOP using all races
    context.update(app_utils.calculate_state_bop(races))

    # Filter to display races
    races = races.where(Race.featured_race == True)

    if slug in app_config.PAGINATED_STATES:
        race_count = races.count()
        page_size = race_count / 2

        if page == 1:
            races = races.limit(page_size)
        elif page == 2:
            races = races.offset(page_size)

        context['page'] = page

    if races.count():
        context['time_on_screen'] = slide.time_on_screen
        context['races'] = [race for race in races]
        context['body'] = render_template('slides/state_house.html', **context)

        return render_template('_slide.html', **context)
    else:
        return "no races", 404

@app.route('/slides/state-senate-results-<slug>.html')
@app_utils.cors
def _state_senate_slide(slug):
    """
    Serve a state slide.
    """
    from models import Race, Slide

    slide = Slide.get(Slide.slug == 'state-senate-results')
    slug = slug.upper()

    senate_races = Race.select().where(
        (Race.office_name == 'U.S. Senate') &
        (Race.state_postal == slug)
    ).order_by(Race.seat_number)

    governor_races = Race.select().where(
        (Race.office_name == 'Governor') &
        (Race.state_postal == slug)
    )

    if senate_races.count() == 0 and governor_races.count() == 0:
        return "404", 404

    senate_updated = get_last_updated(senate_races)
    governor_updated = get_last_updated(governor_races)

    if senate_updated > governor_updated:
        timestamp = senate_updated
    else:
        timestamp = governor_updated

    context = make_context(timestamp=timestamp)
    context['state_postal'] = slug
    context['state_name'] = app_config.STATES.get(slug)

    context['slide_class'] = 'state-senate'
    context['senate'] = senate_races
    context['governor'] = governor_races
    context['time_on_screen'] = slide.time_on_screen
    context['body'] = render_template('slides/state_senate.html', **context)

    return render_template('_slide.html', **context)

@app.route('/slides/<slug>.html')
@app_utils.cors
def _slide(slug):
    """
    Serve up slide html fragment
    """
    from models import Slide

    context = make_context()

    slide = Slide.get(Slide.slug == slug)
    view_name = slide.view_name

    if slide.data:
        context['body'] = slides.__dict__[view_name](slide.data)
    else:
        context['body'] = slides.__dict__[view_name]()

    context['slide_class'] = view_name.replace('_', '-')
    context['time_on_screen'] = slide.time_on_screen

    return render_template('_slide.html', **context)

app.register_blueprint(static_app.static_app)
app.register_blueprint(static_theme.theme)

# Boilerplate
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port')
    args = parser.parse_args()
    server_port = 8000

    if args.port:
        server_port = int(args.port)

    app.run(host='0.0.0.0', port=server_port, debug=app_config.DEBUG)

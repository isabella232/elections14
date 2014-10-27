#!/usr/bin/env python

import datetime
import json

from dateutil.parser import parse
from flask import render_template
import pytz

from render_utils import make_context

import app_utils

def senate_big_board():
    """
    Senate big board
    """
    from models import Race

    context = make_context()

    context['page_title'] = 'Senate'
    context['page_class'] = 'senate'
    context['column_number'] = 2

    races = Race.select().where(Race.office_name == 'U.S. Senate').order_by(Race.poll_closing_time, Race.state_postal)

    context['poll_groups'] = app_utils.group_races_by_closing_time(races)
    context['bop'] = app_utils.calculate_bop(races, app_utils.SENATE_INITIAL_BOP)
    context['not_called'] = app_utils.calculate_seats_left(races)

    return render_template('slides/race_results.html', **context)

def house_big_board(page):
    """
    House big board
    """
    from models import Race

    context = make_context()

    context['page_title'] = 'House'
    context['current_page'] = page
    context['page_class'] = 'house'
    context['column_number'] = 2

    all_races = Race.select().where(Race.office_name == 'U.S. House')
    all_featured_races = Race.select().where((Race.office_name == 'U.S. House') & (Race.featured_race == True)).order_by(Race.poll_closing_time, Race.state_postal)

    if page == 2:
        featured_races = all_featured_races[app_utils.HOUSE_PAGE_LIMIT:]
    else:
        featured_races = all_featured_races[:app_utils.HOUSE_PAGE_LIMIT]

    context['poll_groups'] = app_utils.group_races_by_closing_time(featured_races)
    context['bop'] = app_utils.calculate_bop(all_races, app_utils.HOUSE_INITIAL_BOP)
    context['not_called'] = app_utils.calculate_seats_left(all_races)
    context['seat_number'] = ".seat_number"

    return render_template('slides/race_results.html', **context)

def house_big_board_one():
    """
    First page of house results.
    """
    return house_big_board(1)

def house_big_board_two():
    """
    Second page of house results.
    """
    return house_big_board(2)

def governor_big_board():
    """
    Governor big board
    """
    from models import Race

    context = make_context()

    context['page_title'] = 'Governors'
    context['page_class'] = 'governor'
    context['column_number'] = 2

    races = Race.select().where(Race.office_name == 'Governor').order_by(Race.poll_closing_time, Race.state_postal)

    context['poll_groups'] = app_utils.group_races_by_closing_time(races)

    return render_template('slides/race_results.html', **context)

def ballot_measures_big_board():
    """
    Governor big board
    """
    from models import Race

    context = make_context()

    context['page_title'] = 'Ballot Measures'
    context['page_class'] = 'ballot-measures'
    context['column_number'] = 2

    races = Race.select().where((Race.office_id == 'I') & (Race.featured_race == True)).order_by(Race.poll_closing_time, Race.state_postal)

    context['poll_groups'] = app_utils.group_races_by_closing_time(races)

    return render_template('slides/ballot_measure_results.html', **context)

def _format_tumblr_date(post):
    # Parse GMT date from API
    post_date = parse(post['date'])

    # Convert to Eastern time (EDT or EST)
    eastern = pytz.timezone('US/Eastern')

    return post_date.astimezone(eastern).strftime('%I:%M %p EST')

def tumblr_text(data):
    post = json.loads(data)

    context = make_context()
    context['post'] = post
    context['formatted_date'] = _format_tumblr_date(post)

    return render_template('slides/tumblr_text.html', **context)

def tumblr_photo(data):
    post = json.loads(data)

    context = make_context()
    context['post'] = post
    context['formatted_date'] = _format_tumblr_date(post)

    image = None

    for size in post['photos'][0]['alt_sizes']:
        if not image or size['width'] > image['width']:
            if size['width'] < 960:
                image = size

    context['image'] = image

    return render_template('slides/tumblr_photo.html', **context)

def tumblr_quote(data):
    post = json.loads(data)

    context = make_context()
    context['post'] = post
    context['formatted_date'] = _format_tumblr_date(post)

    return render_template('slides/tumblr_quote.html', **context)

def recent_senate_calls():
    """
    Get the most recent called Senate races
    """
    from models import Race

    context = make_context()

    context['races'] = Race.select().where(
        (Race.office_name == 'U.S. Senate') &
        (((Race.ap_called == True) & (Race.accept_ap_call == True)) |
        (Race.npr_called == True))
    ).order_by(
        Race.ap_called_time.desc(),
        Race.npr_called_time.desc()
    ).limit(3)

    context['label'] = 'Senate'

    return render_template('slides/recent-calls.html', **context)

def recent_house_calls():
    """
    Get the most recent called Senate races
    """
    from models import Race

    context = make_context()

    context['races'] = Race.select().where(
        (Race.office_name == 'U.S. House') &
        (((Race.ap_called == True) & (Race.accept_ap_call == True)) |
        (Race.npr_called == True))
    ).order_by(
        Race.ap_called_time.desc(),
        Race.npr_called_time.desc()
    ).limit(3)

    context['label'] = 'House'

    return render_template('slides/recent-calls.html', **context)

def recent_governor_calls():
    """
    Get the most recent called Senate races
    """
    from models import Race

    context = make_context()

    context['races'] = Race.select().where(
        (Race.office_name == 'Governor') &
        (((Race.ap_called == True) & (Race.accept_ap_call == True)) |
        (Race.npr_called == True))
    ).order_by(
        Race.ap_called_time.desc(),
        Race.npr_called_time.desc()
    ).limit(3)

    context['label'] = 'Governor'

    return render_template('slides/recent-calls.html', **context)

def balance_of_power():
    """
    Serve up the balance of power graph
    """
    from models import Race

    context = make_context()

    context['page_title'] = 'Balance of Power'
    context['page_class'] = 'balance-of-power'

    house_races = Race.select().where(Race.office_name == 'U.S. House').order_by(Race.state_postal)
    senate_races = Race.select().where(Race.office_name == 'U.S. Senate').order_by(Race.state_postal)

    context['house_bop'] = app_utils.calculate_bop(house_races, app_utils.HOUSE_INITIAL_BOP)
    context['senate_bop'] = app_utils.calculate_bop(senate_races, app_utils.SENATE_INITIAL_BOP)
    context['house_not_called'] = app_utils.calculate_seats_left(house_races)
    context['senate_not_called'] = app_utils.calculate_seats_left(senate_races)

    return render_template('slides/balance-of-power.html', **context)

def blue_dogs():
    """
    Ongoing list of how blue dog democrats are faring
    """
    context = make_context()

    return render_template('slides/blue-dogs.html', **context)

def house_freshmen():
    """
    Ongoing list of how representatives elected in 2012 are faring
    """
    context = make_context()

    from models import Race

    races = Race.select().where(Race.freshmen == True)

    context['races_won'] = [race for race in races if race.is_called() and not race.is_runoff() and not race.party_changed()]
    context['races_lost'] = [race for race in races if race.is_called() and not race.is_runoff() and race.party_changed()]
    context['races_not_called'] = [race for race in races if not race.is_called()]

    context['races_count'] = races.count()

    return render_template('slides/house-freshmen.html', **context)

def incumbents_lost():
    """
    Ongoing list of which incumbents lost their elections
    """
    context = make_context()

    from models import Race

    senate_races = Race.select().where(Race.office_name == 'U.S. Senate')
    house_races = Race.select().where(Race.office_name == 'U.S. House')

    context['called_senate_races'] = [race for race in senate_races if race.is_called()]
    context['called_house_races'] = [race for race in house_races if race.is_called()]

    return render_template('slides/incumbents-lost.html', **context)

def obama_reps():
    """
    Ongoing list of Incumbent Republicans In Districts Barack Obama Won In 2012
    """
    context = make_context()

    from models import Race

    races = Race.select().where(Race.obama_gop == True)

    context['races_won'] = [race for race in races if race.is_called() and not race.is_runoff() and not race.party_changed()]
    context['races_lost'] = [race for race in races if race.is_called() and not race.is_runoff() and race.party_changed()]
    context['races_not_called'] = [race for race in races if not race.is_called()]

    context['races_count'] = races.count()

    return render_template('slides/obama-reps.html', **context)

def poll_closing():
    """
    Serve up poll closing information
    """
    from models import Race

    context = make_context()

    # get featured house/ballot measures + all senate and governors
    featured_races = Race.select().where(
        (Race.featured_race == True) |
        (Race.office_name == 'U.S. Senate') |
        (Race.office_name == 'Governor')
    ).order_by(Race.poll_closing_time, Race.state_postal)

    poll_groups = app_utils.group_races_by_closing_time(featured_races)

    now = datetime.datetime.now()
    for closing_time, races in poll_groups:
        if now < closing_time:
            nearest_closing_time = closing_time
            nearest_poll_group = races
            break

    states_closing = []
    for race in nearest_poll_group:
        states_closing.append(race.state_postal)

    states_closing = set(states_closing)
    context['num_states_closing'] = len(states_closing)

    context['closing_time'] = nearest_closing_time.strftime('%H:%M %p ET')
    context['races'] = nearest_poll_group

    return render_template('slides/poll-closing.html', **context)

def rematches():
    """
    List of elections with candidates who have faced off before
    """
    context = make_context()

    return render_template('slides/rematches.html', **context)

def romney_dems():
    """
    Ongoing list of Incumbent Democrats In Districts Mitt Romney Won In 2012
    """
    from models import Race

    context = make_context()

    races = Race.select().where(Race.romney_dem == True)

    context['races_won'] = [race for race in races if race.is_called() and not race.is_runoff() and not race.party_changed()]
    context['races_lost'] = [race for race in races if race.is_called() and not race.is_runoff() and race.party_changed()]
    context['races_not_called'] = [race for race in races if not race.is_called()]

    context['races_count'] = races.count()

    return render_template('slides/romney-dems.html', **context)



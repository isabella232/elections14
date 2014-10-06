#!/usr/bin/env python

from datetime import datetime
import time
import json
import os
from time import sleep

from fabric.api import task
import requests

import app_config

SLEEP_INTERVAL = 60 
SECRETS = app_config.get_secrets()
CACHE_FILE = '.ap_cache.json'

def _init_ap(endpoint):
    """
    Make a request to an AP init endpoint.
    """
    url = 'https://api.ap.org/v2/%s/2014-11-04' % endpoint
    headers = {}

    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    except IOError:
        cache = {}

    if endpoint in cache:
        url = cache[endpoint]['nextrequest']
        headers['If-Modified-Since'] = cache[endpoint]['Last-Modified']
        headers['If-None-Match'] = cache[endpoint]['Etag']

        # If using cache, other params have already been added to url
        params = {
            'apiKey': SECRETS['AP_API_KEY']
        }
    else:
        params = {
            'officeID': 'S,H,G',
            'format': 'json',
            'apiKey': SECRETS['AP_API_KEY']
        }

    params = {
        'officeID': 'S,H,G',
        'format': 'json',
        'apiKey': SECRETS['AP_API_KEY']
    }

    response = requests.get(url, params=params)

    if response.status_code == 304:
        print '%s: already up to date' % endpoint
        return
    elif response.status_code == 403:
        print '%s: rate-limited' % endpoint
        return
    elif response.status_code != 200:
        print '%s: returned %i' % (endpoint, response.status_code)
        return

    cache[endpoint] = {
        'response': response.json(),
        'nextrequest': response.json()['nextrequest'],
        'Last-Modified': response.headers['Last-Modified'],
        'Etag': response.headers['Etag']
    }

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

    print '%s: inited' % endpoint

def _update_ap(endpoint, use_cache=True):
    """
    Make a request to an AP update endpoint.
    """
    url = 'https://api.ap.org/v2/%s/2014-11-04' % endpoint
    headers = {}

    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    except IOError:
        cache = {}

    if endpoint in cache:
        url = cache[endpoint]['nextrequest']
        headers['If-Modified-Since'] = cache[endpoint]['Last-Modified']
        headers['If-None-Match'] = cache[endpoint]['Etag']

        # If using cache, other params have already been added to url
        params = {
            'apiKey': SECRETS['AP_API_KEY']
        }
    else:
        params = {
            'officeID': 'S,H,G',
            'format': 'json',
            'apiKey': SECRETS['AP_API_KEY']
        }
        
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 304:
        print '%s: already up to date' % endpoint
        return
    elif response.status_code == 403:
        print '%s: rate-limited' % endpoint
        return
    elif response.status_code != 200:
        print '%s: returned %i' % (endpoint, response.status_code)
        return

    cache[endpoint] = {
        'response': response.json(),
        'nextrequest': response.json()['nextrequest'],
        'Last-Modified': response.headers['Last-Modified'],
        'Etag': response.headers['Etag']
    }

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

    print '%s: updated' % endpoint

@task
def init():
    """
    Initialize data from AP.
    """
    try:
        os.remove(CACHE_FILE)
    except OSError:
        pass

    _init_ap('init/races')
    sleep(SLEEP_INTERVAL)
    _init_ap('init/candidates')

@task
def update():
    """
    Update data from AP.
    """
    _update_ap('races')
    sleep(SLEEP_INTERVAL)
    _update_ap('calls')

@task
def write(output_dir='data'):
    """
    Write AP data to intermediary files.
    """
    with open(CACHE_FILE) as f:
        cache = json.load(f)

    races = []
    candidates = []
    updates = []

    init_races = cache['init/races']['response']['races']
    init_candidates = cache['init/candidates']['response']['candidates']
    update_races = cache['races']['response']['races']
    #update_calls = cache['calls']['response']['calls']

    for race in init_races:
        races.append({
            'state_postal': race.get('statePostal'),
            'office_id': race.get('officeID'),
            'office_name': race.get('officeName'),
            'seat_name': race.get('seatName'),
            'seat_number': race.get('seatNum'),
            'race_id': race.get('raceID'),
            'race_type': race.get('raceTypeID'),
            'last_updated': race.get('lastUpdated')
        })

    with open('%s/init_races.json' % output_dir, 'w') as f:
        json.dump(races, f, indent=4)

    for candidate in init_candidates:
        candidates.append({
            'candidate_id': candidate.get('candidateID'),
            'last_name': candidate.get('last'),
            'party': candidate.get('party'),
            'first_name': candidate.get('first'),
            'race_id': candidate.get('raceID')
        })

    with open('%s/init_candidates.json' % output_dir, 'w') as f:
        json.dump(candidates, f, indent=4)

    for race in update_races:
        stateRU = race['reportingUnits'][0]

        assert stateRU.get('level', None) == 'state'

        update = {
            'race_id': race.get('raceID'),
            'is_test': race.get('test'),
            'precincts_reporting': stateRU.get('precinctsReporting'),
            'precincts_total': stateRU.get('precinctsTotal'),
            'last_updated': stateRU.get('lastUpdated'),
            'candidates': []
        }

        for candidate in stateRU.get('candidates'):
            update['candidates'].append({
                'candidate_id': candidate.get('candidateID'),
                'vote_count': candidate.get('voteCount'),
                'ap_winner': candidate.get('winner', '') == 'X',
            })

        updates.append(update)

    with open('%s/update.json' % output_dir, 'w') as f:
        json.dump(updates, f, indent=4)

@task
def record():
    """
    Begin recording AP data for playback later.
    """
    update_interval = 60 * 5
    folder = datetime.now().strftime('%Y-%m-%d')
    root = 'data/recording/%s' % folder

    if not os.path.exists(root):
        os.mkdir(root)

    init()
    write('.')

    os.rename('races.json', '%s/races_init.json' % root)
    os.rename('candidates.json', '%s/candidates_init.json' % root)

    sleep(SLEEP_INTERVAL)

    while True:
        timestamp = time.time()

        update()
        write('.')

        os.rename('races.json', '%s/races.%i.json' % (root, timestamp))
        os.rename('candidates.json', '%s/candidates.%i.json' % (root, timestamp))

        sleep(update_interval)


#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv
import json
import requests

FEED_URL = 'http://arkdedicated.com/switch/cache/officialserverlist.json'
FILTER = lambda entry: entry['SessionIsPve'] == 0
COL_NAME_INT = 'Name'
COL_NAME = 'Name'
COL_NAME_MAP = lambda name: name.split('-')[-1]
WEBHOOK_URL = 'INSERT DISCORD WEBHOOK URL HERE'

STATE_CSV = '/tmp/state2.csv'


def save_state(fields, rows):
    with open(STATE_CSV, 'w') as state:
        csv.writer(state).writerows(rows.items())


def load_state():
    try:
        with open(STATE_CSV, 'r') as stream:
            return dict((n, int(v)) for n, v in csv.reader(stream))

    except IOError:
        return dict()


DIFF_CHARS = {-1: '- ', 0: '  ', 1: '+ '}

def compare_state(old, new):
    out = {}
    changed = False

    for n, v in new.items():
        d = min(max(v - old.get(n, 0), -1), 1)
        if d != 0:
            changed = True
        out[n] = (DIFF_CHARS[d], v)

    if not changed:
        raise ValueError

    return out


def post_to_channel(message):
    url = WEBHOOK_URL
    payload = {'content': message}
    requests.post(url, json.dumps(payload), headers={"Content-Type": "application/json"})


def group_max_for(entries, group_name, max_name):
    groups = {}
    group_max = {}
    out = {}

    for entry in entries:
        groups[(entry[group_name], entry[max_name])] = entry

        try:
            group_max[entry[group_name]] = max(entry[max_name], group_max[entry[group_name]])

        except KeyError:
            group_max[entry[group_name]] = entry[max_name]

    total = 0

    for map_name, max_val in group_max.items():
        out[map_name] = groups[(map_name, max_val)]
	total += max_val

    # TODO test
    # out['Total'] = total

    return out


def show_groups(field, group):
    return dict((n, v[field]) for n, v in group.items())


def format_num(val):
    if isinstance(val, int) and (val == 0 or val >= 10):
        return str(val) + ' 👀'

    else:
        return str(val)


def format_data(fields, rows):
    widths = [max(map(len, map(format_num, col))) for col in zip(fields, *rows)]

    row = lambda row: ' | '.join(field.ljust(width) for field, width in zip(map(format_num, row), widths))

    out = ['```diff',
           row(fields),
           '-+-'.join('-' * width for width in widths)
    ]
    out.extend(map(row, rows))
    out.append('```')

    return '\n'.join(out)


if __name__ == '__main__':
    entries = requests.get(FEED_URL).json()
    filtered_entries = filter(FILTER, entries)

    field = "NumPlayers"
    groups = show_groups(field, group_max_for(filtered_entries, COL_NAME_INT, "LastUpdated"))

    fields = ("  " + COL_NAME, "Players")

    old = load_state()
    save_state(fields, groups)

    try:
        diff = compare_state(old, groups)
        names = sorted(diff, key=COL_NAME_MAP)
        post_to_channel(format_data(fields, list((diff[n][0] + COL_NAME_MAP(n), diff[n][1]) for n in names)))

    except ValueError:
        pass

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Note: old syntax for python 2.6

from __future__ import print_function

from datetime import datetime
from itertools import chain
import json
import math

import requests

ENDPOINTS_JSON = '/path/to/endpoints.json'

EYES = ' @@'

fields = ("  Map", "Players")

display_name = {
    "MapName": "  Map",
    "NumPlayers": "Players",
    "ago": "Last Changed",
}.__getitem__

def save_state(state_json, rows):
    with open(state_json, 'w') as state:
        json.dump(rows, state)


def load_state(state_json):
    try:
        with open(state_json, 'r') as state:
            return json.load(state)

    except:
        return dict()

DIFF_CHARS = {-1: '- ', 0: '  ', 1: '+ '}

AGO_RESOLUTION = 60

def post_to_channel(url, message):
    payload = {'content': message}
    requests.post(url, json.dumps(payload), headers={"Content-Type": "application/json"})
    print(url, message)

def group_max_for(entries, group_name, max_name):
    groups = {}
    group_max = {}
    out = {}

    for entry in entries:
        groups[(entry[group_name], entry[max_name])] = entry

        group_max[entry[group_name]] = (
            max(entry[max_name], group_max[entry[group_name]])
            if entry[group_name] in group_max
            else entry[max_name]
        )

    for map_name, max_val in group_max.items():
        out[map_name] = groups[(map_name, max_val)]

    return out

def show_groups(fields, groups):
    return dict(
        (group_name, dict((n,v) for n,v in group.items() if n in fields))
        for group_name, group in groups.items()
    )

def format_num(val):
    if isinstance(val, int) and (val == 0 or val >= 10):
        return str(val) + EYES

    else:
        return str(val)


def format_data(fields, rows):
    headings = list(map(display_name, fields))
    key_order = list(map(next, map(iter, rows)))
    r = dict(rows)

    def gutter(s, row):
        r = iter(row)
        return list(chain([s+next(r)], r))

    table = [gutter(k, map(vals.__getitem__, fields)) for k, vals in map(r.__getitem__, key_order)]

    widths = [max(map(len, map(format_num, col))) for col in zip(headings, *table)]
    row = lambda row: ' | '.join(field.ljust(width) for field, width in zip(map(format_num, row), widths))

    out = [
        '```diff',
       row(headings),
       '-+-'.join('-' * width for width in widths)
    ]
    out.extend(map(row, table))
    out.append('```')

    return '\n'.join(out)

def compare_state(fields, new_groups, groups):
    # look for changes in fields,
    # then update timestamp for only those fields that have changed
    out = {}
    now = datetime.utcnow()
    for group in set(groups.keys()) | set(new_groups.keys()):
      for attempt in range(2):
        try:
            if tuple(map(new_groups[group].__getitem__, fields)) != tuple(map(groups[group].__getitem__, fields)):
                new_groups[group]['changed'] = groups[group]['changed'] = str(now)
                out[group] = new_groups[group]

            ago = int(-(-(
                now - datetime.strptime(groups[group]['changed'], '%Y-%m-%d %H:%M:%S.%f')
            ).seconds // AGO_RESOLUTION))
            if ago >= 60:
                new_groups[group]['ago'] = groups[group]['ago'] = '{a} hour{s} ago'.format(
                    a=int(ago/60),
                    s='s' if ago != 1 else '',
                    # b=EYES if groups[group]['changed'] == str(now) else ''
                )
            else:
                new_groups[group]['ago'] = groups[group]['ago'] = '{a} min{s} ago'.format(
                    a=ago,
                    s='s' if ago != 1 else '',
                    # b=EYES if groups[group]['changed'] == str(now) else ''
                )
            break

        except KeyError:
            try:
                # new map
                new_groups[group].update(
                    changed=str(datetime.utcnow()),
                    ago='0 min ago' + EYES,
                )
                out[group] = new_groups[group]
                break
            except KeyError as ke:
                # mapname missing; set to 0 but preserve update time
                new_groups[group] = dict(chain(
                    groups[group].items(),
                    (("NumPlayers",0),)
                ))
                continue

    return out

def render_compare_state(field, changes, old):
    out = {}
    alerts = []

    total_v = 0

    for n,v in old.items():
        total_v += changes.get(n,v)[field]
        try:
            d = min(max(changes[n][field] - v[field], -1), 1)

        except KeyError:
            d = 0

        out[n] = (DIFF_CHARS[d], changes.get(n,v), d)

    blank = dict((k,'') for k in set.union(set(), *map(set, map(dict.keys, old.values()))))

    # I know this needs improving but this'll do for now:
    tot = dict(blank, **{field:total_v, "MapName": "~Total"})

    out['~Total'] = (DIFF_CHARS[0], tot, total_v)

    return out, alerts

if __name__ == '__main__':
    fields = ["NumPlayers"]
    show_fields = ["MapName", "NumPlayers", 'ago']

    with open(ENDPOINTS_JSON, 'r') as ep:
      endpoints = json.load(ep)
      for endpoint in endpoints:
        entries = requests.get(endpoint['feed_url']).json()

        filtered_entries = [
            entry for entry in entries
            if all(entry[fk] == fv for fk, fv in endpoint['filter'].items())
        ]

        state_json = endpoint['state']
        old = load_state(state_json)
        groups = show_groups(show_fields, group_max_for(filtered_entries, "MapName", "LastUpdated"))

        changes = compare_state(fields, groups, old)

        if changes:
            save_state(state_json, dict(old, **changes))
            diff, alerts = render_compare_state(fields[0], changes, old)
            names = sorted(diff)
            post_to_channel(endpoint['webhook_url'], format_data(show_fields, [(name, diff[name][0:2]) for name in names]))

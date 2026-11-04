"""Ten explicitly hypothetical constraints; structured-fact detector for simulation only."""
from collections import Counter, defaultdict
import re

MIN_RN = {'low': 2, 'normal': 3, 'high': 4, 'surge': 4}
SHIFTS = {'DAY': (7, 19), 'NIGHT': (19, 31)}


def validate(roster):
    if not isinstance(roster, dict) or roster.get('synthetic') is not True:
        raise ValueError('Only explicit synthetic schedules are supported')
    if roster.get('schema_version') != 'edii-sim-roster-v1':
        raise ValueError('Unsupported synthetic roster schema')
    if type(roster.get('month_days')) is not int or roster['month_days'] != 28 or not isinstance(roster.get('roster_id'), str) or not re.fullmatch(r'M\d{2}', roster['roster_id']):
        raise ValueError('Invalid fictional month identity')
    staff = roster.get('staff')
    if not isinstance(staff, list) or not staff or any(not isinstance(s, dict) for s in staff):
        raise ValueError('Staff must be a nonempty list')
    ids = [s.get('staff_id') for s in staff]
    if any(not isinstance(s, str) or not re.fullmatch(r'S\d{2}', s) for s in ids) or len(set(ids)) != len(ids):
        raise ValueError('Invalid or duplicate staff tokens')
    for s in staff:
        if s.get('role') not in ('RN', 'LPN', 'TECH') or type(s.get('orientee')) is not bool or type(s.get('traveler')) is not bool:
            raise ValueError('Invalid staff role or flag')
        if type(s.get('period_cap')) is not int or not 0 <= s['period_cap'] <= 336:
            raise ValueError('Invalid hypothetical hours cap')
        if not isinstance(s.get('competencies'), list) or any(not isinstance(c, str) or c not in ('TRIAGE', 'RESUS') for c in s['competencies']):
            raise ValueError('Invalid competency list')
        if type(s.get('charge')) is not bool or (s['orientee'] and s.get('preceptor') not in ids):
            raise ValueError('Invalid charge/preceptor field')
        if not isinstance(s.get('allowed_shifts'), list) or not s['allowed_shifts'] or any(not isinstance(sh, str) or sh not in SHIFTS for sh in s['allowed_shifts']):
            raise ValueError('Invalid contract shift list')
        days = s.get('contract_days')
        if not isinstance(days, list) or len(days) != 2 or any(type(d) is not int for d in days) or not 1 <= days[0] <= days[1] <= 28:
            raise ValueError('Invalid contract-day interval')
    if not isinstance(roster.get('score_days'), list) or len(roster['score_days']) != 7 or any(type(d) is not int or not 1 <= d <= 28 for d in roster['score_days']) or len(set(roster['score_days'])) != 7:
        raise ValueError('Exactly seven distinct scored dates are required')
    if not isinstance(roster.get('assignments'), list) or not isinstance(roster.get('unavailable'), list):
        raise ValueError('Assignments and unavailable must be explicit lists')
    for a in roster['assignments']:
        if not isinstance(a, dict):
            raise ValueError('Each assignment must be an object')
        if a.get('staff_id') not in ids or type(a.get('day')) is not int or not 1 <= a['day'] <= 28 or not isinstance(a.get('shift'), str) or a['shift'] not in SHIFTS:
            raise ValueError('Unknown assignment identity')
        if not isinstance(a.get('place'), str) or not re.fullmatch(r'[A-Z]{2,12}', a['place']) or a.get('exception') not in (None, 'EMERGENCY'):
            raise ValueError('Invalid assignment place or exception')
    for a in roster['unavailable']:
        if not isinstance(a, list) or len(a) != 3 or a[0] not in ids or type(a[1]) is not int or not 1 <= a[1] <= 28 or not isinstance(a[2], str) or a[2] not in SHIFTS:
            raise ValueError('Invalid unavailable block')
    context = roster.get('census')
    if not isinstance(context, dict) or set(context) != {f'D{d:02}/{sh}' for d in range(1,29) for sh in SHIFTS} or any(not isinstance(v, str) or v not in MIN_RN for v in context.values()):
        raise ValueError('Complete census context is required')
    return roster


def facts(roster):
    """Normalize scheduling context without computing a rule verdict."""
    validate(roster)
    staff = {s['staff_id']: s for s in roster['staff']}
    blocks, schedule = defaultdict(list), defaultdict(set)
    for a in roster['assignments']:
        blocks[a['day'], a['shift']].append(a)
        schedule[a['staff_id']].add((a['day'], a['shift']))
    unavailable = {tuple(x) for x in roster['unavailable']}
    history = {}
    for sid, worked in schedule.items():
        prior_end, period_hours = None, defaultdict(int)
        dates = {d for d, _ in worked}
        for day, shift in sorted(worked, key=lambda x: (x[0], SHIFTS[x[1]][0])):
            start, end = ((day-1)*24 + h for h in SHIFTS[shift])
            period = (day-1)//14
            period_hours[period] += end-start
            consecutive = 1
            while day-consecutive in dates:
                consecutive += 1
            history[sid, day, shift] = (None if prior_end is None else start-prior_end, consecutive, period_hours[period])
            prior_end = end
    units = []
    for day in sorted(roster['score_days']):
        for shift in SHIFTS:
            rows = []
            assigned = blocks[day, shift]
            for sid in sorted({a['staff_id'] for a in assigned}):
                s = staff[sid]
                own = [a for a in assigned if a['staff_id'] == sid]
                rest, consecutive, hours = history[sid, day, shift]
                rows.append({
                    'staff_id': sid, 'role': s['role'], 'charge': s['charge'], 'competencies': s['competencies'],
                    'unavailable': (sid, day, shift) in unavailable,
                    'all_assignments_excepted': all(a.get('exception') == 'EMERGENCY' for a in own),
                    'rest_hours': rest, 'consecutive_days': consecutive, 'period_hours': hours, 'period_cap': s['period_cap'],
                    'orientee': s['orientee'], 'preceptor': s.get('preceptor'),
                    'places': sorted({a['place'] for a in own}), 'traveler': s['traveler'],
                    'allowed_shifts': s['allowed_shifts'], 'contract_days': s['contract_days'],
                })
            units.append({'unit_id':f"{roster['roster_id']}/D{day:02}/{shift}", 'day':day, 'shift':shift,
                          'census_band':roster['census'][f'D{day:02}/{shift}'], 'assigned':rows})
    return units


def judge(unit):
    rows = unit['assigned']; by_id = {r['staff_id']:r for r in rows}; found = set()
    eligible = [r for r in rows if r['role'] == 'RN' and not r['orientee']]
    if len(eligible) < MIN_RN[unit['census_band']]: found.add('H1')
    if not any(r['charge'] for r in eligible): found.add('H2')
    if any(not any(c in r['competencies'] for r in eligible) for c in ('TRIAGE','RESUS')): found.add('H3')
    if any(r['unavailable'] and not r['all_assignments_excepted'] for r in rows): found.add('H4')
    if any(r['rest_hours'] is not None and r['rest_hours'] < 12 for r in rows): found.add('H5')
    if any(r['consecutive_days'] > 3 for r in rows): found.add('H6')
    if any(r['period_hours'] > r['period_cap'] for r in rows): found.add('H7')
    pair_load = Counter(r['preceptor'] for r in rows if r['orientee'])
    for r in rows:
        if r['orientee']:
            p = by_id.get(r['preceptor'])
            if not p or p['role'] != 'RN' or p['orientee'] or p['staff_id'] == r['staff_id'] or pair_load[r['preceptor']] > 1:
                found.add('H8')
    if any(len(r['places']) > 1 for r in rows): found.add('H9')
    if any(r['traveler'] and (unit['shift'] not in r['allowed_shifts'] or not r['contract_days'][0] <= unit['day'] <= r['contract_days'][1]) for r in rows): found.add('H10')
    return sorted(found, key=lambda h:int(h[1:]))


def detect(roster):
    return {u['unit_id']:judge(u) for u in facts(roster)}


def main(argv=None):
    """Local CLI: callers choose paths; input data never chooses an output path."""
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roster', type=Path, help='Synthetic roster JSON, edii-sim-roster-v1')
    parser.add_argument('--out', type=Path, help='New output JSON; existing files are refused')
    args = parser.parse_args(argv)
    try:
        # Reuse the strict JSON parser; it does not compute or supply judgments.
        from analyze_responses import strict_json
        roster = strict_json(args.roster.read_text(encoding='utf8'))
        labels = detect(roster)
        payload = {'schema_version':'edii-sim-detector-v1', 'synthetic':True,
                   'roster_id':roster['roster_id'], 'hypothetical_rules':['H'+str(i) for i in range(1,11)],
                   'units':len(labels), 'gap_units':sum(bool(v) for v in labels.values()), 'labels':labels}
        rendered = json.dumps(payload, indent=2)+'\n'
        if args.out:
            with args.out.open('x', encoding='utf8') as handle:
                handle.write(rendered)
        else:
            print(rendered, end='')
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, 'Input/output error: '+str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())

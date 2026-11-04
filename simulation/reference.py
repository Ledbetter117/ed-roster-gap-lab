"""Separate exhaustive reference calculation over raw schedules, not detector facts.

Implemented separately in the same AI work context; not independent human authorship.
No detector, facts-view, or perturbation-intent imports are used.
"""


def score(roster):
    people = {p['staff_id']:p for p in roster['staff']}
    unavail = set(map(tuple, roster['unavailable']))
    unique = {(a['staff_id'],a['day'],a['shift']) for a in roster['assignments']}
    def start(d,sh): return 24*(d-1) + (7 if sh=='DAY' else 19)
    answers = {}
    for day in sorted(roster['score_days']):
        for shift in ('DAY','NIGHT'):
            members = {sid for sid,d,sh in unique if d==day and sh==shift}
            registered = members & {sid for sid,p in people.items() if p['role']=='RN' and p['orientee'] is False}
            errors = []
            minimum = {'low':2,'normal':3,'high':4,'surge':4}[roster['census'][f'D{day:02}/{shift}']]
            if len(registered) < minimum: errors.append('H1')
            if not (registered & {sid for sid,p in people.items() if p['charge']}): errors.append('H2')
            skills = set().union(*(set(people[sid]['competencies']) for sid in registered)) if registered else set()
            if not {'TRIAGE','RESUS'} <= skills: errors.append('H3')
            blocked = [a for a in roster['assignments'] if a['day']==day and a['shift']==shift and (a['staff_id'],day,shift) in unavail and a.get('exception')!='EMERGENCY']
            if blocked: errors.append('H4')
            for sid in members:
                earlier = [start(d,sh)+12 for who,d,sh in unique if who==sid and start(d,sh)<start(day,shift)]
                if earlier and start(day,shift)-max(earlier)<12:
                    errors.append('H5');break
            for sid in members:
                worked_days = {d for who,d,sh in unique if who==sid}
                if all(d in worked_days for d in range(day-3,day+1)):
                    errors.append('H6');break
            first_day = 1 if day<=14 else 15
            for sid in members:
                elapsed = sum(12 for who,d,sh in unique if who==sid and first_day<=d<=day and start(d,sh)<=start(day,shift))
                if elapsed>people[sid]['period_cap']:
                    errors.append('H7');break
            orientee_ids = members & {sid for sid,p in people.items() if p['orientee']}
            named = [people[sid]['preceptor'] for sid in orientee_ids]
            if any(people[sid]['preceptor'] not in registered or people[sid]['preceptor']==sid for sid in orientee_ids) or len(named)!=len(set(named)):
                errors.append('H8')
            if any(len({a['place'] for a in roster['assignments'] if a['staff_id']==sid and a['day']==day and a['shift']==shift})>1 for sid in members):
                errors.append('H9')
            if any(people[sid]['traveler'] and (shift not in people[sid]['allowed_shifts'] or day<people[sid]['contract_days'][0] or day>people[sid]['contract_days'][1]) for sid in members):
                errors.append('H10')
            answers[f"{roster['roster_id']}/D{day:02}/{shift}"] = errors
    return answers

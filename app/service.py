from datetime import datetime, timezone, timedelta
import os
from uuid import uuid4
from .errors import DomainError as HTTPException
from .models import Proposal

def uid(): return uuid4().hex
def now(): return datetime.now(timezone.utc).isoformat()
def find(d, collection, id):
    row=next((r for r in d[collection] if r['id']==id),None)
    if row is None: raise HTTPException(404,'Record not found')
    return row

def event(d, actor, action, result):
    d['auditEvents'].append(dict(id=uid(),actor=actor,action=action,time=now(),result=result,policy_version=d['policies'][-1]['version']))

def gate(d, p, exclude=None):
    policy=d['policies'][-1]; blocked=[]; review=[]
    tags={t.lower().strip() for t in p['tags']}
    # Supplement structured tags; conservative keyword detection, not a semantic guarantee.
    title=p['title'].lower()
    if any(t in title for t in ['tequila','beer','wine','vodka']): tags.add('alcohol')
    if any(t in title for t in ['pork','bacon','ham sandwich']): tags.add('pork')
    if tags & set(policy['blocked_tags']): blocked.append('Blocked category/tag under group policy')
    if any(not m['onboarded'] for m in d['members']): review.append('All members must complete onboarding')
    if p['transport'] not in policy['transport'] or any(p['transport'] not in m['transport'] for m in d['members']): blocked.append('Transport conflicts with group or member restriction')
    n=len(d['members']); share=(p['cost_cents']+n-1)//n if p['category']=='expense' else p['cost_cents']
    if share>policy['cap_cents']: blocked.append('Per-person group cap exceeded')
    committed=sum((x['cost_cents']+n-1)//n if x['category']=='expense' else x['cost_cents'] for x in d['proposals'] if x['status']=='accepted' and x['id']!=exclude)
    if any(committed+share>m['budget_cents'] for m in d['members']): blocked.append('A member total budget would be exceeded')
    requirements=set(policy['requirements']) | {r for m in d['members'] for r in m['requirements']}
    if p['category'] in ['food','expense']:
        venue=next((v for v in d['venues'] if v['id']==p.get('venue_id')),None)
        facts=set(venue['facts']) if venue and (not venue.get('demo') or os.getenv('DEMO_MODE','true').lower()=='true') else set()
        if requirements-facts: review.append('Dietary/health requirements need trusted evidence; text and screenshots are inference only')
        if venue and set(venue['tags']) & set(policy['blocked_tags']): blocked.append('Venue evidence conflicts with group policy')
    if p['category']!='expense':
        if not p.get('start') or not p.get('end'): review.append('Start and end times are required for schedule feasibility')
        else:
            start=datetime.fromisoformat(p['start']); end=datetime.fromisoformat(p['end'])
            for old in d['proposals']:
                if old['status']!='accepted' or old['id']==exclude or not old.get('start'): continue
                buffer=timedelta(minutes=max(p['travel_minutes'],old['travel_minutes']))
                if start < datetime.fromisoformat(old['end'])+buffer and end+buffer > datetime.fromisoformat(old['start']):
                    blocked.append('Schedule overlap or insufficient travel buffer'); break
    return ('blocked' if blocked else 'review' if review else 'allowed'),blocked+review or ['All deterministic checks passed']

def decide(d, actor, p, exclude=None):
    outcome,reasons=gate(d,p,exclude)
    decision=dict(id=uid(),actor=actor,proposal_id=p['id'],outcome=outcome,reasons=reasons,policy_version=d['policies'][-1]['version'],time=now())
    d['decisions'].append(decision)
    event(d,actor,'policy.evaluate',decision.copy())
    return decision

def propose(d,actor,payload,source='text'):
    p=Proposal.model_validate(payload).model_dump(mode='json')
    p.update(id=uid(),actor=actor,source=source,status='pending',created_at=now())
    decision=decide(d,actor,p)
    p['status']='eligible' if decision['outcome']=='allowed' else decision['outcome']
    d['proposals'].append(p)
    return {'proposal':p,'decision':decision}

def resolve(d,actor):
    if actor!='alex': raise HTTPException(403,'Only group organizer may close a ballot')
    candidates=[p for p in d['proposals'] if p['status']=='eligible']
    if not candidates: raise HTTPException(409,'No eligible proposals')
    votes={v['actor']:v['proposal_id'] for v in d['votes']}
    if len(votes)!=len(d['members']): raise HTTPException(409,'Every member must vote before closing this round')
    candidates.sort(key=lambda p:(-sum(v==p['id'] for v in votes.values()),p['cost_cents'],p['created_at'],p['id']))
    winner=None
    for p in candidates:
        decision=decide(d,actor,p,p['id'])
        if decision['outcome']=='allowed': winner=p; break
        p['status']=decision['outcome']
    if winner:
        winner['status']='accepted'
        if winner['category']=='expense':
            ids=sorted(m['id'] for m in d['members']); q,r=divmod(winner['cost_cents'],len(ids))
            allocation={m:q+(i<r) for i,m in enumerate(ids)}
            d['expenses'].append(dict(id=winner['id'],title=winner['title'],payer=winner['actor'],total_cents=winner['cost_cents'],allocations=allocation,currency='CAD'))
            for debtor,cents in allocation.items():
                if debtor!=winner['actor'] and cents:
                    d['payments'].append(dict(id=uid(),expense_id=winner['id'],sender=debtor,receiver=winner['actor'],amount_cents=cents,sent=False,received=False,status='outstanding'))
        for p in candidates:
            if p['status']=='eligible': p['status']='not_selected'
    d['votes'].clear()
    # Votes are represented by one mutable row per member; delete persistence handled separately.
    event(d,actor,'ballot.closed',{'winner':winner['id'] if winner else None,'rule':'Most votes, then lowest cost, then earliest submission'})
    return {'winner':winner}

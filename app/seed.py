def seed():
    members = [dict(id=i,name=n,requirements=r,transport=['walk','bus','train'],budget_cents=12000,onboarded=True) for i,n,r in [('alex','Alex',[]),('sara','Sara',['halal']),('dev','Dev',['vegetarian','nut-free'])]]
    return {
        'groups':[dict(id='montreal',name='Montreal weekend',revision=0,currency='CAD')],
        'members':members,
        'policies':[dict(id='policy-1',version=1,requirements=['halal'],transport=['walk','bus','train'],cap_cents=5000,blocked_tags=['alcohol','pork'])],
        'venues':[dict(id='demo-garden',name='Garden Table (fictional)',facts=['halal','vegetarian','nut-free'],tags=[],source='Curated DEMO fixture; not real venue verification',demo=True)],
        'tickets':[dict(id='demo-ticket',owner='alex',simulated=True,status='booked')],
        **{c:[] for c in ['proposals','votes','expenses','payments','decisions','auditEvents','conversations']}}

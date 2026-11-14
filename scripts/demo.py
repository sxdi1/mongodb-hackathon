"""Run against a fresh local mock server: python scripts/demo.py"""
import httpx
base='http://127.0.0.1:8000/api/'
def call(path,data=None,who='alex'):
    r=httpx.request('GET' if data is None else 'POST',base+path,json=data,headers={'Authorization':'Bearer demo-'+who});r.raise_for_status();return r.json()
r=call('chat',{'text':'add $45 tequila'})
assert r['tools'][0]['decision']['outcome']=='blocked'
print('PASS: tequila blocked with an audit event')
r=call('proposals',{'title':'Garden receipt','category':'expense','cost_cents':9001,'venue_id':'demo-garden'})
id=r['proposal']['id']
for who in ['alex','sara','dev']:call('vote',{'proposal_id':id},who)
assert call('resolve',{})['winner']['id']==id
for p in call('state')['payments']:
    if p['expense_id']==id:
        call('payments/'+p['id']+'/ack',{'kind':'sent'},p['sender'])
        assert call('payments/'+p['id']+'/ack',{'kind':'received'},p['receiver'])['status']=='acknowledged'
print('PASS: exact cent splitting and separate party acknowledgements; no payments executed')

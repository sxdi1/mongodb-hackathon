import logging, os, json, base64, secrets, re
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .errors import DomainError
from .store import Store
from .models import Profile, Policy, Proposal, Chat, Vote, Acknowledge, Cancel
from .service import find, event, uid, now, propose, resolve
from .adapters import WebAdapter
from . import agent

logger=logging.getLogger(__name__)
load_dotenv()
DEMO=os.getenv('DEMO_MODE','true').lower()=='true'
TOKENS=json.loads(os.getenv('AUTH_TOKENS','{}'))
if DEMO: TOKENS.update({'demo-alex':'alex','demo-sara':'sara','demo-dev':'dev'})

@asynccontextmanager
async def lifespan(app):
    if not TOKENS: raise RuntimeError('Configure AUTH_TOKENS outside demo mode')
    app.state.store=Store()
    yield

app=FastAPI(title='SplitSmart Bouncer',lifespan=lifespan)
@app.exception_handler(DomainError)
async def domain_error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={'detail':exc.detail})
def actor(authorization: str=Header(default='')):
    token=authorization.removeprefix('Bearer ')
    who=next((v for k,v in TOKENS.items() if secrets.compare_digest(k,token)),None)
    if not who: raise HTTPException(401,'Valid bearer token required')
    with app.state.store.transaction() as d: find(d,'members',who)
    return who

@app.get('/api/config')
def config(): return {'demo':DEMO,'agent':os.getenv('AGENT_MODE','mock'),'storage':os.getenv('STORAGE','sqlite')}

@app.get('/api/state')
def state(who=Depends(actor)):
    with app.state.store.transaction() as d:
        visible={k:v for k,v in d.items() if k not in ['members','auditEvents','decisions','searchCache']}
        visible['members']=[{k:v for k,v in m.items() if k in ['id','name','onboarded']} for m in d['members']]
        visible['me']=find(d,'members',who)
        visible['decisions']=d['decisions'][-100:]
        visible['auditEvents']=d['auditEvents'][-100:]
        return visible

@app.put('/api/profile')
def profile(body:Profile,who=Depends(actor)):
    with app.state.store.transaction() as d:
        m=find(d,'members',who); m.update(body.model_dump(),onboarded=True)
        event(d,who,'profile.updated',{'member':who,'note':'Private boundaries updated; values redacted'})
        return m

@app.put('/api/policy')
def policy(body:Policy,who=Depends(actor)):
    if who!='alex': raise HTTPException(403,'Organizer only')
    with app.state.store.transaction() as d:
        p=dict(id=uid(),version=d['policies'][-1]['version']+1,**body.model_dump())
        d['policies'].append(p); event(d,who,'policy.updated',p); return p

@app.post('/api/proposals')
def proposals(body:Proposal,who=Depends(actor)):
    with app.state.store.transaction() as d: return propose(d,who,body.model_dump(mode='json'))

@app.post('/api/chat')
def chat(body:Chat,who=Depends(actor)):
    image=None
    if body.image_base64:
        try: image=base64.b64decode(body.image_base64,validate=True)
        except ValueError: raise HTTPException(422,'Invalid base64 image')
        valid=(body.mime_type=='image/png' and image.startswith(b'\x89PNG\r\n\x1a\n')) or (body.mime_type=='image/jpeg' and image.startswith(b'\xff\xd8\xff'))
        if not valid or len(image)>2_000_000: raise HTTPException(422,'Use a PNG/JPEG up to 2 MB')
    with app.state.store.transaction() as d:
        history=[
            dict(
                id=message['id'],
                actor=message['actor'],
                name='Bouncer' if message['actor']=='bouncer' else find(d,'members',message['actor'])['name'],
                text=message['text'],
                analysis=message.get('analysis'),
                extraction=message.get('extraction'),
                reply_context=message.get('reply_context'),
            )
            for message in d['conversations'][-20:]
        ]
        actor_name=find(d,'members',who)['name']
        user_message_id=uid()
        d['conversations'].append(dict(
            id=user_message_id,
            actor=who,
            text=body.text,
            time=now(),
            has_image=bool(image),
        ))
    envelope = WebAdapter().normalize(who,dict(
        text=body.text,
        image=image,
        mime_type=body.mime_type,
        actor_name=actor_name,
        history=history,
    ))
    try:
        result=agent.run(envelope)
    except Exception as error:
        detail=str(error)
        api_key=os.getenv('GEMINI_API_KEY','')
        if api_key:
            detail=detail.replace(api_key,'[redacted]')
        detail=re.sub(r'AIza[0-9A-Za-z_-]{20,}','[redacted]',detail)
        detail=re.sub(r'(?i)(api[_ -]?key|authorization)(["\s:=]+)[^\s,;]+',r'\1\2[redacted]',detail)
        logger.error(
            'Agent request failed (actor=%s, mode=%s, type=%s): %s',
            who,
            os.getenv('AGENT_MODE','mock'),
            type(error).__name__,
            detail[:400] or 'No error detail',
        )
        try:
            result=agent.fallback(envelope)
        except Exception:
            logger.exception('Local agent fallback failed (actor=%s)',who)
            raise
        with app.state.store.transaction() as d:
            event(d,who,'agent.error',{
                'error_type':type(error).__name__,
                'mode':os.getenv('AGENT_MODE','mock'),
                'message':'Provider failure; a local conversational reply was used',
            })
    with app.state.store.transaction() as d:
        user_message=next((message for message in d['conversations'] if message['id']==user_message_id),None)
        if user_message is None:
            raise HTTPException(409,'Chat was cleared while this reply was being generated. Send a new message.')
        if result.get('analysis'):
            analysis=result['analysis']
            analysis['schema_version']=1
            analysis['source']=result.get('analysis_source','local')
            analysis['reported_by']=who
            analysis['source_message_id']=user_message_id
            user_message['analysis']=analysis
            result['analysis']=analysis
        if result.get('extraction'):
            extraction=result['extraction']
            extraction.setdefault('source_message_id',user_message_id)
            extraction.setdefault('reported_by',who)
            extraction['updated_by']=who
            user_message['extraction']=extraction
        reply_context=None
        if (result.get('extraction') or {}).get('status')=='needs_clarification':
            reply_context={'kind':'expense_mention','message_id':user_message_id}
        d['conversations'].append(dict(
            id=uid(),
            actor='bouncer',
            text=result['reply'],
            time=now(),
            has_image=False,
            reply_context=reply_context,
        ))
    return result

@app.post('/api/chat/clear')
def clear_chat(who=Depends(actor)):
    if not DEMO: raise HTTPException(403,'Clearing messages is available only in demo mode')
    with app.state.store.transaction() as d:
        count=len(d['conversations'])
        d['conversations']=[]
        event(d,who,'chat.cleared',{'messages_removed':count})
    return {'ok':True,'messages_removed':count}

@app.post('/api/vote')
def vote(body:Vote,who=Depends(actor)):
    with app.state.store.transaction() as d:
        p=find(d,'proposals',body.proposal_id)
        if p['status']!='eligible': raise HTTPException(409,'Only eligible proposals can receive votes')
        d['votes']=[v for v in d['votes'] if v['actor']!=who]
        d['votes'].append(dict(id=uid(),actor=who,proposal_id=p['id']))
        event(d,who,'vote.cast',{'proposal_id':p['id']}); return {'ok':True}

@app.post('/api/resolve')
def close(who=Depends(actor)):
    with app.state.store.transaction() as d: return resolve(d,who)

@app.post('/api/payments/{id}/ack')
def ack(id:str,body:Acknowledge,who=Depends(actor)):
    with app.state.store.transaction() as d:
        p=find(d,'payments',id)
        if who!=p['sender' if body.kind=='sent' else 'receiver']: raise HTTPException(403,'Only the corresponding party may acknowledge')
        if not p[body.kind]:
            p[body.kind]=True; p[body.kind+'_at']=now()
            p['status']='acknowledged' if p['sent'] and p['received'] else 'awaiting_counterparty'
            event(d,who,'payment.'+body.kind,dict(payment_id=id,status=p['status'],note='Member attestation only; no bank verification or money movement'))
        return p

@app.post('/api/tickets/{id}/cancel')
def cancel(id:str,body:Cancel,who=Depends(actor)):
    with app.state.store.transaction() as d:
        t=find(d,'tickets',id)
        allowed=t['owner']==who and t['simulated'] and body.approved
        event(d,who,'ticket.cancel',{'ticket':id,'allowed':allowed,'simulated':t['simulated']})
        if allowed: t['status']='cancelled'; return t
        return {'status':'blocked','reason':'Requires ticket owner approval and simulated ticket. No live cancellation integration installed.'}

app.mount('/',StaticFiles(directory=Path(__file__).parent/'static',html=True),name='web')

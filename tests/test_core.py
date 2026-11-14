"""Offline domain tests: python -m unittest discover -s tests -p test_core.py -v"""
import unittest, os, tempfile
from unittest.mock import MagicMock
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from app.seed import seed
from app.models import Proposal
from app.service import propose, resolve, gate
from app.store import Store
from app.errors import DomainError

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.d=seed();os.environ['DEMO_MODE']='true'
        self.p=dict(title='Garden dinner',category='food',cost_cents=3000,venue_id='demo-garden',start='2026-11-21T19:00:00-05:00',end='2026-11-21T20:00:00-05:00')
    def submit(self,**kw):return propose(self.d,'alex',self.p|kw)
    def votes(self,id):self.d['votes']=[dict(id=m['id'],actor=m['id'],proposal_id=id) for m in self.d['members']]
    def test_block_alcohol(self):self.assertEqual(self.submit(title='tequila',tags=['alcohol'])['decision']['outcome'],'blocked')
    def test_claims_cannot_verify(self):self.assertEqual(self.submit(venue_id=None,claims=['halal','vegetarian','nut-free'])['decision']['outcome'],'review')
    def test_transport(self):self.assertEqual(self.submit(transport='car')['decision']['outcome'],'blocked')
    def test_budget(self):self.assertEqual(self.submit(cost_cents=5001)['decision']['outcome'],'blocked')
    def test_unknown_health(self):
        self.d['members'][0]['requirements']=['low-sodium']
        self.assertEqual(self.submit()['decision']['outcome'],'review')
    def test_schedule(self):
        p=self.submit()['proposal'];self.votes(p['id']);resolve(self.d,'alex')
        self.assertEqual(self.submit()['decision']['outcome'],'blocked')
    def test_recheck(self):
        p=self.submit()['proposal'];self.votes(p['id']);self.d['policies'][-1]['cap_cents']=1
        self.assertIsNone(resolve(self.d,'alex')['winner'])
    def test_quorum(self):
        self.submit()
        with self.assertRaises(DomainError):resolve(self.d,'alex')
    def test_organizer(self):
        p=self.submit()['proposal'];self.votes(p['id'])
        with self.assertRaises(DomainError):resolve(self.d,'sara')
    def test_cents(self):
        p=self.submit(category='expense',cost_cents=1001)['proposal'];self.votes(p['id']);resolve(self.d,'alex')
        self.assertEqual(sum(self.d['expenses'][0]['allocations'].values()),1001)
        self.assertEqual(len(self.d['payments']),2)
    def test_tie(self):
        rows=[self.submit(cost_cents=n)['proposal'] for n in [3000,2500,4000]]
        self.d['votes']=[dict(id=m['id'],actor=m['id'],proposal_id=p['id']) for m,p in zip(self.d['members'],rows)]
        self.assertEqual(resolve(self.d,'alex')['winner']['cost_cents'],2500)
    def test_invalid_time(self):
        with self.assertRaises(ValueError):Proposal.model_validate(self.p|{'start':'2026-11-21T19:00:00'})
    def test_no_forged_actor(self):
        with self.assertRaises(ValueError):self.submit(actor='sara')
    def test_no_production_demo_evidence(self):
        os.environ['DEMO_MODE']='false'
        self.assertEqual(self.submit()['decision']['outcome'],'review')
    def test_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ['STORAGE']='sqlite';os.environ['SQLITE_PATH']=temp+'/test.sqlite'
            store=Store()
            with self.assertRaises(RuntimeError):
                with store.transaction() as d:d['expenses'].append({'id':'bad'});raise RuntimeError()
            with store.transaction() as d:self.assertEqual(d['expenses'],[])

class MongoStoreTests(unittest.TestCase):
    def test_insert_does_not_add_mongo_id_to_returned_document(self):
        store=Store.__new__(Store);store.mongo=True
        session=MagicMock()
        store.client=MagicMock()
        store.client.start_session.return_value.__enter__.return_value=session
        collections={}
        def collection(name):
            if name not in collections:
                collections[name]=MagicMock()
                collections[name].find.return_value=[]
            return collections[name]
        store.db=MagicMock()
        store.db.__getitem__.side_effect=collection
        store.db.groups=collection('groups')
        def insert(document,**kwargs): document['_id']=ObjectId()
        collection('proposals').insert_one.side_effect=insert

        proposal={'id':'proposal-1','title':'Chinese restaurant'}
        with store.transaction() as data:
            data['proposals'].append(proposal)

        self.assertEqual(jsonable_encoder(proposal),{'id':'proposal-1','title':'Chinese restaurant'})

if __name__=='__main__':unittest.main()

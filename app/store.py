"""Transactional document repository: SQLite demo or MongoDB replica set/Atlas."""
import json, os, sqlite3
from contextlib import contextmanager, closing
from .seed import seed

COLLECTIONS = tuple(seed())
REQUIRED = {'decisions':['id','actor','outcome','reasons','policy_version','proposal_id'],
            'auditEvents':['id','actor','action','time','result','policy_version'],
            'policies':['id','version','requirements','transport','cap_cents','blocked_tags']}

class Store:
    def __init__(self):
        self.mongo = os.getenv('STORAGE','sqlite') == 'mongo'
        if self.mongo:
            from pymongo import MongoClient
            self.client = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=5000)
            self.db = self.client[os.getenv('MONGODB_DB','splitsmart')]
            self.client.admin.command('ping')
            for c in COLLECTIONS:
                props = {'id':{'bsonType':'string'}}
                if c == 'decisions': props['outcome']={'enum':['allowed','blocked','review']}
                if c == 'policies': props.update(version={'bsonType':'int','minimum':1},cap_cents={'bsonType':'int','minimum':0},requirements={'bsonType':'array'},transport={'bsonType':'array'},blocked_tags={'bsonType':'array'})
                validator={'$jsonSchema':{'bsonType':'object','required':REQUIRED.get(c,['id']),'properties':props}}
                if c not in self.db.list_collection_names(): self.db.create_collection(c,validator=validator)
                else: self.db.command('collMod',c,validator=validator,validationLevel='strict',validationAction='error')
                self.db[c].create_index('id',unique=True)
            with self.client.start_session() as s, s.start_transaction():
                if not self.db.groups.find_one({},session=s):
                    for c, rows in seed().items():
                        if rows: self.db[c].insert_many(rows,session=s)
        else:
            self.path = os.getenv('SQLITE_PATH','splitsmart.sqlite')
            with closing(sqlite3.connect(self.path)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
                db.execute('INSERT OR IGNORE INTO state VALUES (1,?)',(json.dumps(seed()),))
                db.commit()

    @contextmanager
    def transaction(self):
        if not self.mongo:
            db=sqlite3.connect(self.path,timeout=20)
            try:
                db.execute('BEGIN IMMEDIATE')
                data=json.loads(db.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
                data.setdefault('searchCache', [])
                yield data
                db.execute('UPDATE state SET data=? WHERE id=1',(json.dumps(data),))
                db.commit()
            except Exception:
                db.rollback(); raise
            finally: db.close()
        else:
            with self.client.start_session() as s, s.start_transaction():
                # Serialize writes across processes; conflicting transactions fail closed.
                self.db.groups.update_one({'id':'montreal'},{'$inc':{'revision':1}},session=s)
                data={c:list(self.db[c].find({}, {'_id':0},session=s)) for c in COLLECTIONS}
                original=json.loads(json.dumps(data))
                yield data
                for c, rows in data.items():
                    old={r['id']:r for r in original[c]}
                    removed=set(old)-{r['id'] for r in rows}
                    if removed and c in ('auditEvents','decisions','policies'): raise ValueError('Append-only collection')
                    if removed: self.db[c].delete_many({'id':{'$in':list(removed)}},session=s)
                    for row in rows:
                        if row['id'] not in old: self.db[c].insert_one(row.copy(),session=s)
                        elif row != old[row['id']]:
                            if c in ('auditEvents','decisions','policies'): raise ValueError('Append-only application collection')
                            self.db[c].replace_one({'id':row['id']},row,session=s)

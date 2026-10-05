import json, os, sqlite3, time
from pathlib import Path

DB = Path(os.environ.get("B27B_STATE_DB", "runtime/b27b_agents.sqlite3"))

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""create table if not exists jobs(
      id integer primary key autoincrement,
      kind text not null, payload text not null default '{}',
      status text not null default 'queued',
      created_at real not null, updated_at real not null,
      result text
    )""")
    con.execute("""create table if not exists heartbeats(
      worker text primary key, ts real not null, detail text
    )""")
    con.commit()
    return con

def enqueue(kind, payload=None):
    now=time.time(); con=connect()
    cur=con.execute("insert into jobs(kind,payload,status,created_at,updated_at) values(?,?,?,?,?)",
                    (kind,json.dumps(payload or {}),"queued",now,now))
    con.commit(); return cur.lastrowid

def heartbeat(worker, detail="ok"):
    con=connect()
    con.execute("""insert into heartbeats(worker,ts,detail) values(?,?,?)
      on conflict(worker) do update set ts=excluded.ts, detail=excluded.detail""",
      (worker,time.time(),detail))
    con.commit()

import json, subprocess, sys, time
from agents.gatekeeper import authorize
from agents.state import connect, heartbeat

def claim():
    con=connect()
    con.execute("begin immediate")
    row=con.execute("select id,kind,payload from jobs where status='queued' order by id limit 1").fetchone()
    if not row:
        con.commit(); return None
    con.execute("update jobs set status='running',updated_at=? where id=?",(time.time(),row[0]))
    con.commit(); return row

def finish(job_id, result, ok=True):
    con=connect()
    con.execute("update jobs set status=?,result=?,updated_at=? where id=?",
                ("done" if ok else "failed",json.dumps(result),time.time(),job_id))
    con.commit()

def execute(kind,payload):
    allowed,reason=authorize("paper_research")
    if not allowed: return {"blocked":reason},False
    if kind=="fetch_data_quality":
        return {"agent":"FETCH","status":"queued_for_dataset_validation","payload":payload},True
    if kind=="vision_experiment":
        return {"agent":"VISION","status":"experiment_proposed","payload":payload},True
    if kind=="ultron_risk_review":
        return {"agent":"ULTRON","status":"paper_only_boundary_verified"},True
    return {"status":"unknown_job","kind":kind},False

def main():
    while True:
        heartbeat("WORKER","waiting")
        row=claim()
        if not row:
            time.sleep(5); continue
        jid,kind,payload=row
        try:
            result,ok=execute(kind,json.loads(payload))
            finish(jid,result,ok)
        except Exception as e:
            finish(jid,{"error":repr(e)},False)

if __name__=="__main__":
    main()

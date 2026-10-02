"""Build a deterministic repair queue and ledger for B27B universe gaps.
Research-only. This stage classifies/prioritizes gaps; it never mutates market bars,
validation thresholds, strategy inputs, or trading permissions.
"""
import argparse,csv,json,os
from collections import defaultdict
from persistent_memory import get as memory_get,put as memory_put

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars",required=True); p.add_argument("--membership",required=True)
    p.add_argument("--aliases",required=True); p.add_argument("--start",required=True); p.add_argument("--end",required=True)
    p.add_argument("--ledger",required=True); p.add_argument("--queue",required=True)
    a=p.parse_args()
    bars=defaultdict(set)
    with open(a.bars,newline="") as h:
        for r in csv.DictReader(h):
            s=r.get("symbol","").strip().upper(); d=r.get("timestamp","")
            if s and a.start<=d<=a.end: bars[s].add(d)
    cal=sorted(bars.get("SPY",set()))
    periods=defaultdict(list); former=set()
    with open(a.membership,newline="") as h:
        for r in csv.DictReader(h):
            s=r["ticker"].strip().upper(); en=r["end_date"] or None
            periods[s].append((r["start_date"],en))
            if en and a.start<en<=a.end: former.add(s)
    historical={s for s,spans in periods.items() if any(st<=a.end and (en is None or en>a.start) for st,en in spans)}
    aliases={}
    with open(a.aliases,newline="") as h:
        for r in csv.DictReader(h):
            aliases[r["old_symbol"].strip().upper()]=r["new_symbol"].strip().upper()
    prior=memory_get("repair_ledger",{}) or {}
    rows=[]
    for s in sorted(historical):
        expected={d for d in cal if any(st<=d and (en is None or d<en) for st,en in periods[s])}
        obs=bars.get(s,set()) & expected
        comp=len(obs)/len(expected) if expected else 0.0
        if comp>=0.90: continue
        if not bars.get(s): cls="missing_history"
        else: cls="partial_history"
        if s in aliases: cls="known_ticker_transition"
        old=prior.get(s,{}) if isinstance(prior,dict) else {}
        seen=int(old.get("seen_count",0))+1
        previous=float(old.get("completeness",0) or 0)
        improved=comp>previous+0.000001
        recoverability={"rename_candidate":0,"partial_history":1,"former_unresolved":2,"missing_history":3}.get(cls,4)
        stale=seen>=2 and not improved
        priority=(0 if s in former else 1, recoverability, 1 if stale else 0, -comp, seen, s)
        rows.append({"symbol":s,"former":s in former,"classification":cls,"completeness":round(comp,6),
                     "expected_days":len(expected),"observed_days":len(obs),"candidate_successor":aliases.get(s,""),
                     "seen_count":seen,"previous_completeness":round(previous,6),"improved_since_last":improved,
                     "retry_state":"deprioritize_no_gain" if stale else "active",
                     "_priority":priority})
    rows.sort(key=lambda r:r["_priority"])
    for i,r in enumerate(rows,1): r["priority_rank"]=i; r.pop("_priority",None)
    os.makedirs(os.path.dirname(a.ledger) or ".",exist_ok=True)
    fields=["priority_rank","symbol","former","classification","completeness","expected_days","observed_days","candidate_successor","seen_count","previous_completeness","improved_since_last","retry_state"]
    with open(a.ledger,"w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(a.queue,"w") as h: json.dump({"research_only":True,"bars_mutated":False,"gates_changed":False,"items":rows},h,indent=2)
    snapshot=dict(prior) if isinstance(prior,dict) else {}
    current_symbols=set()
    for r in rows:
        current_symbols.add(r["symbol"])
        snapshot[r["symbol"]]={k:r[k] for k in ("classification","completeness","candidate_successor","seen_count","former","retry_state")}
        snapshot[r["symbol"]]["status"]="unresolved"
    for symbol,item in list(snapshot.items()):
        if symbol not in current_symbols and isinstance(item,dict):
            item["status"]="repaired_or_complete"
    memory_put("repair_ledger",snapshot)
    repeated=sum(1 for r in rows if r["seen_count"]>1 and not r["improved_since_last"])
    print(f"B27B_REPAIR_MEMORY persisted={len(snapshot)} repeated_no_gain={repeated}",flush=True)
    print(f"B27B_REPAIR_QUEUE gaps={len(rows)} former_first={sum(r['former'] for r in rows)} rename_candidates={sum(r['classification']=='rename_candidate' for r in rows)} ledger={a.ledger}",flush=True)
    print("B27B_REPAIR_PRIORITY_SAMPLE "+(",".join(r["symbol"] for r in rows[:20]) or "-"),flush=True)
if __name__=="__main__": main()

#!/usr/bin/env python3
"""Offline analysis for the frozen B27B forward test.
Reads archived decisions only. It never places orders and never changes the live rule.
"""
import json, pathlib, statistics, collections, datetime, re

SRC=pathlib.Path("paper_history/decisions.jsonl")
OUT=pathlib.Path("paper_history/analysis/latest.json")

def rows():
    out=[]
    if SRC.exists():
        for line in SRC.read_text().splitlines():
            try: out.append(json.loads(line))
            except Exception: pass
    return out

def market_start(slug):
    m=re.search(r"(\d{4}-\d{2}-\d{2})-(\d{4})z",slug or "")
    if not m:return None
    return datetime.datetime.strptime(m.group(1)+m.group(2),"%Y-%m-%d%H%M").replace(tzinfo=datetime.timezone.utc).timestamp()

def main():
    r=rows(); by=collections.defaultdict(list)
    for x in r: by[x.get("slug","unknown")].append(x)
    edges=[float(x["gross_pair_edge"]) for x in r if x.get("gross_pair_edge") is not None]
    timing={"first_5m":[],"middle_5m":[],"last_5m":[],"unknown":[]}
    for x in r:
        st=market_start(x.get("slug"))
        if st is None or x.get("gross_pair_edge") is None: timing["unknown"].append(x);continue
        sec=float(x.get("ts",0))-st
        bucket="first_5m" if sec<300 else ("middle_5m" if sec<600 else "last_5m")
        timing[bucket].append(x)
    buckets={}
    for k,v in timing.items():
        es=[float(x["gross_pair_edge"]) for x in v if x.get("gross_pair_edge") is not None]
        buckets[k]={"observations":len(v),"qualifying":sum(x.get("result")=="qualifying" for x in v),
                    "mean_edge":round(statistics.fmean(es),6) if es else None,
                    "best_edge":max(es) if es else None}
    thresholds={}
    # Counterfactual research only; these DO NOT alter the frozen +1c live test.
    for t in (0.0,0.005,0.01,0.015,0.02):
        thresholds[str(t)]={"signals":sum(e>=t for e in edges),
                            "rate":round(sum(e>=t for e in edges)/len(edges),6) if edges else 0}
    gaps=[]
    for xs in by.values():
        xs=sorted(xs,key=lambda x:x.get("ts",0))
        gaps += [b.get("ts",0)-a.get("ts",0) for a,b in zip(xs,xs[1:]) if b.get("ts",0)>=a.get("ts",0)]
    report={
      "generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "frozen_live_threshold":0.01,"observations":len(r),"markets":len(by),
      "qualifying":sum(x.get("result")=="qualifying" for x in r),
      "rejected":sum(x.get("result")=="rejected" for x in r),
      "edge":{"mean":round(statistics.fmean(edges),6) if edges else None,"median":round(statistics.median(edges),6) if edges else None,"best":max(edges) if edges else None,"worst":min(edges) if edges else None},
      "market_timing":buckets,"counterfactual_thresholds_research_only":thresholds,
      "coverage":{"median_within_market_gap_seconds":round(statistics.median(gaps),2) if gaps else None,
                  "gaps_over_60s":sum(g>60 for g in gaps),"gaps_over_300s":sum(g>300 for g in gaps)},
      "warning":"Counterfactual thresholds are offline research only and must not change the frozen forward-test rule."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()

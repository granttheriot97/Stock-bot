"""Build persistent ticker case files, assignments, activity, and coverage history. Research-only."""
import argparse,json,time
from persistent_memory import get as get,put as put
def main():
 p=argparse.ArgumentParser();p.add_argument("--queue",required=True);p.add_argument("--partials",required=True);a=p.parse_args()
 def rd(path,d):
  try:
   with open(path) as h:return json.load(h)
  except:return d
 q=rd(a.queue,{"items":[]});pr=rd(a.partials,{"results":[]});ranges={x["symbol"]:x for x in pr.get("results",[])}
 cases={};tasks=[];now=time.time()
 for x in q.get("items",[]):
  s=x["symbol"];cls=x.get("classification");owner="ARCHIVIST";status="INVESTIGATING" if x.get("retry_state")=="active" else "NEEDS EVIDENCE"
  if cls=="rename_candidate":owner="ORACLE"
  task="classify corporate fate" if cls=="former_unresolved" else "validate successor and effective date" if cls=="rename_candidate" else "recover only missing date ranges" if cls=="partial_history" else "locate legitimate historical source"
  cases[s]={"symbol":s,"classification":cls,"status":status,"owner":owner,"completeness":x.get("completeness"),"missing":ranges.get(s,{}).get("ranges",[]),"next_action":task,"updated_at":now}
  tasks.append({"id":s+":"+cls,"symbol":s,"from":"RESEARCH DIRECTOR","to":owner,"status":"OPEN","task":task,"created_at":now})
  if cls in ("partial_history","missing_history","former_unresolved"):tasks.append({"id":s+":source","symbol":s,"from":owner,"to":"CIPHER","status":"OPEN","task":"identify legitimate recovery source","created_at":now})
 put("ticker_case_files",cases);put("agent_task_queue",tasks[-500:])
 activity={}
 for name in ("ARCHIVIST","ORACLE","CIPHER","PULSE"):
  mine=[x for x in tasks if x["to"]==name]
  activity[name]={"status":"INVESTIGATING" if mine else "MONITORING","current_mission":mine[0]["task"]+" • "+mine[0]["symbol"] if mine else "monitor research state","open_tasks":len(mine),"last_active":now}
 put("agent_activity",activity)
 hist=get("coverage_history",[]) or []
 try:
  import csv
  # coverage history is appended elsewhere from authoritative/incremental outputs; preserve structure here.
 except:pass
 put("coverage_history",hist[-250:])
 print("B27B_CASE_FILES cases="+str(len(cases))+" tasks="+str(len(tasks))+" active_agents="+str(sum(1 for x in activity.values() if x["open_tasks"])),flush=True)
if __name__=="__main__":main()

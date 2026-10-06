"""Persistent ticker cases and task lifecycle. Research-only; no gate/data authority."""
import argparse,json,time
from persistent_memory import get,put
def main():
 p=argparse.ArgumentParser();p.add_argument("--queue",required=True);p.add_argument("--partials",required=True);a=p.parse_args()
 def rd(path,d):
  try:return json.load(open(path))
  except:return d
 q=rd(a.queue,{"items":[]});pr=rd(a.partials,{"results":[]});ranges={x["symbol"]:x for x in pr.get("results",[])};now=time.time()
 old_cases=get("ticker_case_files",{}) or {};old_tasks=get("agent_task_queue",[]) or [];byid={x.get("id"):x for x in old_tasks if x.get("id")}
 cases={};active_symbols=set()
 def task(tid,s,frm,to,desc):
  old=byid.get(tid,{});status=old.get("status","OPEN")
  if status=="RESOLVED":status="OPEN"
  item={"id":tid,"symbol":s,"from":frm,"to":to,"status":status,"task":desc,"created_at":old.get("created_at",now),"updated_at":now,"evidence":old.get("evidence",[]),"history":old.get("history",[])}
  if not old:item["history"]=[{"time":now,"status":"OPEN","reason":"created"}]
  byid[tid]=item
 for x in q.get("items",[]):
  s=x["symbol"];active_symbols.add(s);cls=x.get("classification");owner="ORACLE" if cls=="rename_candidate" else "ARCHIVIST"
  old=old_cases.get(s,{}) if isinstance(old_cases,dict) else {}
  status=old.get("status","INVESTIGATING" if x.get("retry_state")=="active" else "NEEDS EVIDENCE")
  action="classify corporate fate" if cls=="former_unresolved" else "validate successor and effective date" if cls=="rename_candidate" else "recover only missing date ranges" if cls=="partial_history" else "locate legitimate historical source"
  cases[s]={"symbol":s,"classification":cls,"status":status,"owner":owner,"completeness":x.get("completeness"),"expected_days":x.get("expected_days"),"observed_days":x.get("observed_days"),"missing":ranges.get(s,{}).get("ranges",[]),"next_action":action,"updated_at":now,"history":old.get("history",[])}
  task(s+":"+cls,s,"RESEARCH DIRECTOR",owner,action)
  if cls in ("partial_history","missing_history","former_unresolved"):task(s+":source",s,owner,"CIPHER","identify legitimate recovery source")
 for tid,item in list(byid.items()):
  if item.get("symbol") not in active_symbols and not str(tid).startswith("human:") and item.get("status")!="RESOLVED":
   item["status"]="RESOLVED";item["updated_at"]=now;item.setdefault("history",[]).append({"time":now,"status":"RESOLVED","reason":"symbol cleared fixed completeness gate"})
 tasks=sorted(byid.values(),key=lambda x:x.get("updated_at",x.get("created_at",0)),reverse=True)[:500]
 put("ticker_case_files",cases);put("agent_task_queue",tasks)
 activity={}
 for name in ("ARCHIVIST","ORACLE","CIPHER","PULSE"):
  mine=[x for x in tasks if x.get("to")==name and x.get("status") not in ("RESOLVED","REJECTED")]
  activity[name]={"status":"INVESTIGATING" if mine else "MONITORING","current_mission":mine[0]["task"]+" • "+mine[0]["symbol"] if mine else "monitor research state","open_tasks":len(mine),"last_active":now}
 put("agent_activity",activity)
 print("B27B_CASE_FILES cases="+str(len(cases))+" tasks="+str(len(tasks))+" active_agents="+str(sum(1 for x in activity.values() if x["open_tasks"])),flush=True)
if __name__=="__main__":main()

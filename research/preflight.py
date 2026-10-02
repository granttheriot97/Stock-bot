"""Fail-closed preflight for B27B source integrity. No trading/data mutation."""
import ast,json,os,re,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors=[];checked=0
for base,_,names in os.walk(os.path.join(ROOT,"research")):
 for n in names:
  if n.endswith(".py"):
   p=os.path.join(base,n)
   try: ast.parse(open(p,encoding="utf-8").read(),filename=p);checked+=1
   except SyntaxError as e: errors.append(f"{os.path.relpath(p,ROOT)}:{e.lineno}:{e.msg}")
for p in ("research_service.py","research/pipeline.py"):
 q=os.path.join(ROOT,p)
 try: ast.parse(open(q,encoding="utf-8").read(),filename=q);checked+=1
 except SyntaxError as e: errors.append(f"{p}:{e.lineno}:{e.msg}")
pipe=open(os.path.join(ROOT,"research/pipeline.py"),encoding="utf-8").read()
stages=re.findall(r'stage\("([^"]+)"',pipe)
dupes=sorted({x for x in stages if stages.count(x)>1})
if dupes:errors.append("duplicate pipeline stages: "+",".join(dupes))
for p in ("research/agents/agent_policy.json","research/jarvis_policy.json"):
 try:json.load(open(os.path.join(ROOT,p),encoding="utf-8"))
 except Exception as e:errors.append(p+":"+type(e).__name__)
js=open(os.path.join(ROOT,"research_dashboard/app.js"),encoding="utf-8").read()
if "const STAGES=[" not in js:errors.append("dashboard stage registry missing")
if 'LIVE TRADING DISABLED' not in open(os.path.join(ROOT,"research_dashboard/index.html"),encoding="utf-8").read():errors.append("safety banner missing")
repair=open(os.path.join(ROOT,"research/self_repair.py"),encoding="utf-8").read()
if "def one(sym,job_start=None,job_end=None):" not in repair:errors.append("targeted repair worker missing range arguments")
if "pool.submit(one,s,lo,hi)" not in repair:errors.append("partial-history range jobs are not executed")
if "nasdaq_wiki" not in repair:errors.append("archival WIKI fallback missing")
print(f"B27B_PREFLIGHT python_files={checked} pipeline_stages={len(stages)} errors={len(errors)}")
for e in errors:print("B27B_PREFLIGHT_ERROR "+e)
raise SystemExit(1 if errors else 0)

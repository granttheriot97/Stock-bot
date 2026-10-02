"""Free Render-compatible B27B research service with streaming read-only telemetry."""
import json,os,subprocess,threading,time,mimetypes
from http.server import BaseHTTPRequestHandler,HTTPServer
S={"status":"starting","started_at":time.time(),"output":"","error":None,"checkpoint":None,"active_stage":None,"stage_started_at":None,"last_event":None,"event_count":0}
ROOT=os.path.dirname(os.path.abspath(__file__));DASH=os.path.join(ROOT,"research_dashboard")
def ingest(line,lines):
    line=line.rstrip("\n");lines.append(line)
    if len(lines)>4000:del lines[:-4000]
    S["output"]="\n".join(lines);S["last_event"]=line;S["event_count"]+=1
    if line.startswith("B27B_STAGE_START stage="):
        S["active_stage"]=line.split("stage=",1)[1].split()[0];S["stage_started_at"]=time.time()
    elif line.startswith("B27B_STAGE_COMPLETE stage="):
        finished=line.split("stage=",1)[1].split()[0]
        if S.get("active_stage")==finished:S["active_stage"]=None;S["stage_started_at"]=None
    print(line,flush=True)
def run():
    print("B27B_RESEARCH_START",flush=True);S["status"]="running"
    timeout=int(os.getenv("B27B_RESEARCH_TIMEOUT","3600"));started=time.time();lines=[]
    try:
        p=subprocess.Popen(["sh","research/run_research.sh"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        while True:
            line=p.stdout.readline()
            if line:ingest(line,lines)
            if p.poll() is not None:
                for rest in p.stdout:ingest(rest,lines)
                break
            if time.time()-started>timeout:
                p.kill();p.wait();raise TimeoutError(f"research exceeded {timeout}s")
        S["returncode"]=p.returncode;S["status"]="complete" if p.returncode==0 else "failed"
        if S["status"]!="running":S["active_stage"]=None;S["stage_started_at"]=None
        print("B27B_RESEARCH_STATUS",S["status"],"RETURNCODE",p.returncode,flush=True)
    except Exception as e:
        S.update(status="failed",error=repr(e),active_stage=None,stage_started_at=None);print("B27B_RESEARCH_ERROR",repr(e),flush=True)
def snapshot():
    state=dict(S);state["server_time"]=time.time()
    try:
        with open(os.path.join(os.getenv("B27B_STATE_DIR","/tmp/b27b_state"),"manifest.json")) as h:state["checkpoint"]=json.load(h)
    except Exception:pass
    return state
class H(BaseHTTPRequestHandler):
    def send_bytes(self,b,ctype):
        self.send_response(200);self.send_header("Content-Type",ctype);self.send_header("Cache-Control","no-store, no-cache, must-revalidate");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        route=self.path.split("?",1)[0].rstrip("/") or "/"
        if route=="/api/status":return self.send_bytes(json.dumps(snapshot()).encode(),"application/json")
        if route in ("/","/command-center"):path=os.path.join(DASH,"index.html")
        elif route.startswith("/command-center/"):
            rel=route[len("/command-center/"):]
            if rel not in ("app.js","style.css"):self.send_error(404);return
            path=os.path.join(DASH,rel)
        else:self.send_error(404);return
        try:
            with open(path,"rb") as h:b=h.read()
            self.send_bytes(b,mimetypes.guess_type(path)[0] or "application/octet-stream")
        except FileNotFoundError:self.send_error(404)
    def log_message(self,*a):pass
threading.Thread(target=run,daemon=True).start()
HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),H).serve_forever()

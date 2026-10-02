"""Free Render-compatible B27B research service with streaming research logs and read-only command center."""
import json,os,subprocess,threading,time,mimetypes
from http.server import BaseHTTPRequestHandler,HTTPServer
S={"status":"starting","started_at":time.time(),"output":"","error":None,"checkpoint":None}
ROOT=os.path.dirname(os.path.abspath(__file__))
DASH=os.path.join(ROOT,"research_dashboard")
def run():
    print("B27B_RESEARCH_START",flush=True)
    timeout=int(os.getenv("B27B_RESEARCH_TIMEOUT","3600"));started=time.time();lines=[]
    try:
        p=subprocess.Popen(["sh","research/run_research.sh"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        while True:
            line=p.stdout.readline()
            if line:
                line=line.rstrip("\n");lines.append(line)
                if len(lines)>4000:lines=lines[-4000:]
                S["output"]="\n".join(lines);print(line,flush=True)
            if p.poll() is not None:
                for rest in p.stdout:
                    rest=rest.rstrip("\n");lines.append(rest);print(rest,flush=True)
                break
            if time.time()-started>timeout:
                p.kill();p.wait();raise TimeoutError(f"research exceeded {timeout}s")
        S["output"]="\n".join(lines[-4000:]);S["returncode"]=p.returncode
        S["status"]="complete" if p.returncode==0 else "failed"
        print("B27B_RESEARCH_STATUS",S["status"],"RETURNCODE",p.returncode,flush=True)
    except Exception as e:
        S.update(status="failed",error=repr(e));print("B27B_RESEARCH_ERROR",repr(e),flush=True)
def snapshot():
    state=dict(S)
    try:
        with open(os.path.join(os.getenv("B27B_STATE_DIR","/tmp/b27b_state"),"manifest.json")) as h:state["checkpoint"]=json.load(h)
    except Exception:pass
    return state
class H(BaseHTTPRequestHandler):
    def send_bytes(self,b,ctype):
        self.send_response(200);self.send_header("Content-Type",ctype);self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        route=self.path.split("?",1)[0].rstrip("/") or "/"\n        if route=="/api/status":
            return self.send_bytes(json.dumps(snapshot()).encode(),"application/json")
        if route=="/" or route=="/command-center":
            path=os.path.join(DASH,"index.html")
        elif self.path.startswith("/command-center/"):
            rel=self.path[len("/command-center/"):].split("?",1)[0]
            if rel not in ("app.js","style.css"):self.send_error(404);return
            path=os.path.join(DASH,rel)
        else:
            return self.send_bytes(json.dumps(snapshot()).encode(),"application/json")
        try:
            with open(path,"rb") as h:b=h.read()
            self.send_bytes(b,mimetypes.guess_type(path)[0] or "application/octet-stream")
        except FileNotFoundError:self.send_error(404)
    def log_message(self,*a):pass
threading.Thread(target=run,daemon=True).start()
HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),H).serve_forever()

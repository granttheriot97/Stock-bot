"""Free Render-compatible B27B research service with streaming research logs."""
import json,os,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,HTTPServer
S={"status":"starting","started_at":time.time(),"output":"","error":None,"checkpoint":None}
def run():
    print("B27B_RESEARCH_START",flush=True)
    timeout=int(os.getenv("B27B_RESEARCH_TIMEOUT","3600"))
    started=time.time()
    lines=[]
    try:
        p=subprocess.Popen(["sh","research/run_research.sh"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        while True:
            line=p.stdout.readline()
            if line:
                line=line.rstrip("\n")
                lines.append(line)
                if len(lines)>4000: lines=lines[-4000:]
                S["output"]="\n".join(lines)
                print(line,flush=True)
            if p.poll() is not None:
                for rest in p.stdout:
                    rest=rest.rstrip("\n");lines.append(rest);print(rest,flush=True)
                break
            if time.time()-started>timeout:
                p.kill();p.wait()
                raise TimeoutError(f"research exceeded {timeout}s")
        S["output"]="\n".join(lines[-4000:])
        S["returncode"]=p.returncode
        S["status"]="complete" if p.returncode==0 else "failed"
        print("B27B_RESEARCH_STATUS",S["status"],"RETURNCODE",p.returncode,flush=True)
    except Exception as e:
        S.update(status="failed",error=repr(e))
        print("B27B_RESEARCH_ERROR",repr(e),flush=True)
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        state=dict(S)
        try:
            with open(os.path.join(os.getenv("B27B_STATE_DIR","/tmp/b27b_state"),"manifest.json")) as h:
                state["checkpoint"]=json.load(h)
        except Exception:
            pass
        b=json.dumps(state).encode()
        self.send_response(200);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*a): pass
threading.Thread(target=run,daemon=True).start()
HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),H).serve_forever()

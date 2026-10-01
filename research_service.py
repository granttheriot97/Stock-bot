"""Free Render-compatible B27B research service. Runs research once at startup and exposes output."""
import json,os,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,HTTPServer
S={"status":"starting","started_at":time.time(),"output":"","error":None}
def run():
    try:
        p=subprocess.run(["sh","research/run_research.sh"],capture_output=True,text=True,timeout=900)
        S["output"]=p.stdout[-200000:];S["error"]=p.stderr[-20000:] or None
        S["status"]="complete" if p.returncode==0 else "failed";S["returncode"]=p.returncode
    except Exception as e:S.update(status="failed",error=repr(e))
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b=json.dumps(S).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*a):pass
threading.Thread(target=run,daemon=True).start()
HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),H).serve_forever()

"""Free Render-compatible B27B research service. Runs research once at startup and exposes + logs output."""
import json,os,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,HTTPServer
S={"status":"starting","started_at":time.time(),"output":"","error":None}
def run():
    print("B27B_RESEARCH_START",flush=True)
    try:
        p=subprocess.run(["sh","research/run_research.sh"],capture_output=True,text=True,timeout=900)
        S["output"]=p.stdout[-200000:];S["error"]=p.stderr[-20000:] or None
        S["status"]="complete" if p.returncode==0 else "failed";S["returncode"]=p.returncode
        lines=[x for x in p.stdout.splitlines() if x.strip()]
        diagnostics=[x for x in lines if x.startswith("B27B_")]
        results=[x for x in lines if "," in x and not x.startswith("symbol,") and not x.startswith("B27B_")]
        passes=[x for x in results if x.rstrip().endswith(",True")]
        print("B27B_RESEARCH_STATUS",S["status"],"ROWS",len(results),"PASSES",len(passes),flush=True)
        print("B27B_PASSING_RESULTS_BEGIN",flush=True)
        for x in passes: print(x,flush=True)
        print("B27B_PASSING_RESULTS_END",flush=True)
        print("B27B_DIAGNOSTICS_BEGIN",flush=True)
        for x in diagnostics: print(x,flush=True)
        print("B27B_DIAGNOSTICS_END",flush=True)
        print("B27B_ALL_RESULTS_BEGIN",flush=True)
        for x in results: print(x,flush=True)
        print("B27B_ALL_RESULTS_END",flush=True)
        if p.stderr: print("B27B_RESEARCH_STDERR",p.stderr[-10000:],flush=True)
    except Exception as e:
        S.update(status="failed",error=repr(e));print("B27B_RESEARCH_ERROR",repr(e),flush=True)
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b=json.dumps(S).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*a):pass
threading.Thread(target=run,daemon=True).start()
HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),H).serve_forever()

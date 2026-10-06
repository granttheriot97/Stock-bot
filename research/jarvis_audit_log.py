"""Append-only, hash-chained JARVIS audit records. Local durability only."""
import hashlib,json,os,sys,time
LOG=os.getenv("B27B_JARVIS_AUDIT_LOG","/tmp/b27b_jarvis_audit.jsonl")
def last_hash():
    try:
        last=""
        with open(LOG) as h:
            for line in h:
                if line.strip(): last=json.loads(line)["hash"]
        return last
    except FileNotFoundError:return ""
def main():
    event={"time":time.time(),"event":sys.argv[1] if len(sys.argv)>1 else "audit","previous_hash":last_hash()}
    raw=json.dumps(event,sort_keys=True,separators=(",",":")).encode()
    event["hash"]=hashlib.sha256(raw).hexdigest()
    with open(LOG,"a") as h:
        h.write(json.dumps(event,sort_keys=True)+"\n");h.flush();os.fsync(h.fileno())
    print("B27B_JARVIS_AUDIT "+event["hash"],flush=True)
if __name__=="__main__":main()

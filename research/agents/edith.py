"""EDITH: append-only experiment ledger with hash chaining."""
import hashlib,json,os,sys,time
LOG=os.getenv("B27B_EDITH_LOG","/tmp/b27b_edith.jsonl")
def last():
    try:
        x=""
        for line in open(LOG):
            if line.strip():x=json.loads(line)["hash"]
        return x
    except FileNotFoundError:return ""
def main():
    payload=" ".join(sys.argv[1:])[:12000]
    e={"agent":"EDITH","time":time.time(),"previous_hash":last(),"payload":payload}
    e["hash"]=hashlib.sha256(json.dumps(e,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    with open(LOG,"a") as h:h.write(json.dumps(e,sort_keys=True)+"\n");h.flush();os.fsync(h.fileno())
    print("B27B_EDITH "+e["hash"],flush=True)
if __name__=="__main__":main()

"""FRIDAY: repair-plan generator. Produces proposals only; never edits/deploys."""
import json,os,sys,time
ALLOWED={"retry_fetch","resume_stage","rebuild_checkpoint","refetch_symbol","restart_failed_operational_stage"}
FORBIDDEN={"change_strategy","change_gate","change_risk","deploy","trade","brokerage","self_modify"}
def main():
    issue=" ".join(sys.argv[1:])[:2000]
    proposal={"agent":"FRIDAY","time":time.time(),"issue":issue,"mode":"proposal_only","allowed_repairs":sorted(ALLOWED),"forbidden":sorted(FORBIDDEN),"requires_human_or_supervisor_approval":True}
    path=os.getenv("B27B_FRIDAY_REPORT","/tmp/b27b_friday_proposal.json")
    with open(path,"w") as h:json.dump(proposal,h,indent=2)
    print("B27B_FRIDAY_PROPOSAL "+json.dumps(proposal,separators=(",",":")),flush=True)
if __name__=="__main__":main()

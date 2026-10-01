"""ULTRON: adversarial research tester. Cannot improve/tune strategy parameters."""
import json,os,time
TESTS=["higher_costs","delayed_execution","delete_one_name","random_placebo","period_sensitivity","missing_data_sensitivity","benchmark_comparison"]
def main():
    r={"agent":"ULTRON","time":time.time(),"mode":"adversarial_only","tests":TESTS,"may_loosen_gates":False,"may_select_winners":False,"may_trade":False}
    path=os.getenv("B27B_ULTRON_PLAN","/tmp/b27b_ultron_plan.json")
    with open(path,"w") as h:json.dump(r,h,indent=2)
    print("B27B_ULTRON_PLAN "+json.dumps(r,separators=(",",":")),flush=True)
if __name__=="__main__":main()

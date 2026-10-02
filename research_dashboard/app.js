const $=id=>document.getElementById(id);
const roles=[
["Controller",["agent_security","agent_supervisor","membership_boundary_tests","specialist_security_tests","former_probe","fetch_agent","repair_queue","secondary_source_probe","universe_audit","optimizer_summary"],"⌘"],
["Former Tickers",["specialist_former_tickers"],"↺"],
["Corporate Actions",["specialist_corporate_actions"],"⇄"],
["Data Sources",["specialist_data_sources"],"◉"],
["Bottlenecks",["specialist_bottlenecks"],"⌁"],
["WATCHDOG",["watchdog_pre_experiments"],"◈"],
["GATEKEEPER",["gatekeeper"],"⚿"],
["JARVIS",["jarvis_audit"],"J"],
["VISION",["vision_multi_strategy"],"V"],
["ULTRON",["ultron_adversarial"],"U"]
];
function state(v){if(!v)return["WAITING","muted"];if(v.status==="complete")return["COMPLETE","status"];if(v.status==="failed")return["FAILED","failed"];if(v.status==="started"||v.status==="running")return["RUNNING","running"];return[String(v.status||"WAITING").toUpperCase(),"muted"]}
function pct(n){return Math.max(0,Math.min(100,n||0))}
function audit(o){let a=[...(o||"").matchAll(/B27B_UNIVERSE_AUDIT[^\n]*coverage=(0?\.\d+|1(?:\.0+)?)?[^\n]*former_coverage=(0?\.\d+|1(?:\.0+)?)?/g)];if(!a.length)return{};let m=a[a.length-1];return{overall:+m[1]*100,former:+m[2]*100}}
function roleState(cp,keys){let found=keys.map(k=>[k,cp[k]]).filter(x=>x[1]);if(!found.length)return{label:"WAITING",cls:"muted",detail:"awaiting stage"};let running=found.find(x=>["started","running"].includes(x[1].status));if(running)return{label:"ACTIVE",cls:"running",detail:running[0].replaceAll("_"," ")};let failed=[...found].reverse().find(x=>x[1].status==="failed");if(failed)return{label:"BLOCKED",cls:"failed",detail:failed[0].replaceAll("_"," ")};let last=found[found.length-1];return{label:last[1].status==="complete"?"COMPLETE":"WAITING",cls:last[1].status==="complete"?"status":"muted",detail:last[0].replaceAll("_"," ")}}
async function tick(){try{let r=await fetch("/api/status",{cache:"no-store"});let d=await r.json(),cp=(d.checkpoint||{}).stages||{},vals=Object.values(cp),done=vals.filter(x=>x.status==="complete").length,total=Math.max(vals.length,1),p=Math.round(done/total*100);
$("system").textContent=d.status==="failed"?"RESEARCH BLOCKED":d.status==="complete"?"AUDIT COMPLETE":"RESEARCH ACTIVE";$("sub").textContent=d.error||"Controller orchestrating read-only research stages";$("progress").textContent=p+"%";
let cv=audit(d.output);if(cv.overall!=null){$("coverage").textContent=cv.overall.toFixed(1)+"%";$("coverageBar").style.width=pct(cv.overall)+"%"}if(cv.former!=null){$("former").textContent=cv.former.toFixed(1)+"%";$("formerBar").style.width=pct(cv.former)+"%"}
let gate=cp.gatekeeper;if(gate&&gate.status==="complete"){$("gate").textContent="CHECKED";$("gateReason").textContent="See latest Gatekeeper evidence"}else{$("gate").textContent="LOCKED";$("gateReason").textContent="Downstream work remains fail-closed"}
let health=[...(d.output||"").matchAll(/B27B_SELF_REPAIR_CONTROL[^\n]*status=(\w+)/g)];$("providers").textContent=health.length?(health[health.length-1][1]==="HEALTHY"?"HEALTHY":"DEGRADED"):"—";
$("team").innerHTML=roles.map(([name,keys,icon])=>{let x=roleState(cp,keys);return '<div class="agent"><b><i class="agentIcon '+name.toLowerCase()+'">'+icon+'</i>'+name+'</b><span class="'+x.cls+'">● '+x.label+'</span><span class="muted">'+x.detail+'</span></div>'}).join("");
$("pipeline").innerHTML=Object.entries(cp).slice(-18).map(([name,v])=>{let [s,c]=state(v);return '<div class="stage"><b>'+name.replaceAll("_"," ")+'</b><span class="'+c+'">'+s+'</span><span class="muted">attempt '+(v.attempt||"—")+'</span></div>'}).join("");
let lines=(d.output||"").split("\n").filter(x=>/B27B_(SPECIALIST|RENAME|SECONDARY|REPAIR|UNIVERSE|GATE|OPTIMIZER|STAGE_(START|COMPLETE))/.test(x));$("results").textContent=lines.slice(-35).join("\n")||"Waiting for research output…";$("updated").textContent="Updated "+new Date().toLocaleTimeString()}catch(e){$("system").textContent="TELEMETRY OFFLINE";$("sub").textContent=e.message}}
tick();setInterval(tick,3000);
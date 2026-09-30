import json, math, random, time
from dataclasses import dataclass

@dataclass
class State:
    cash: float = 100.0
    up: float = 0.0
    down: float = 0.0
    peak_equity: float = 100.0
    fills: int = 0
    merges: int = 0

class B27BPaperEngine:
    def __init__(self, cfg):
        self.c=cfg; self.s=State(cash=cfg["starting_cash"], peak_equity=cfg["starting_cash"])

    def equity(self, up_mid=.5, down_mid=.5):
        return self.s.cash + self.s.up*up_mid + self.s.down*down_mid

    def risk_ok(self, up_bid, up_ask, down_bid, down_ask):
        if max(up_ask-up_bid, down_ask-down_bid) > self.c["max_market_spread"]: return False
        unmatched=abs(self.s.up-self.s.down)
        if unmatched > self.c["max_unmatched_shares"]: return False
        if self.s.up+self.s.down > self.c["max_total_inventory"]: return False
        eq=self.equity((up_bid+up_ask)/2,(down_bid+down_ask)/2)
        self.s.peak_equity=max(self.s.peak_equity,eq)
        if eq < self.s.peak_equity*(1-self.c["max_drawdown_fraction"]): return False
        return True

    def desired_quotes(self, up_bid, up_ask, down_bid, down_ask):
        if not self.risk_ok(up_bid,up_ask,down_bid,down_ask): return None
        imbalance=self.s.up-self.s.down
        skew=max(-self.c["max_quote_skew"],min(self.c["max_quote_skew"],imbalance*self.c["inventory_skew_per_share"]))
        up=max(.01,min(.99,up_bid-skew))
        down=max(.01,min(.99,down_bid+skew))
        if up+down > 1-self.c["pair_edge_required"]: return None
        return round(up,4),round(down,4)

    def fill(self, side, price, qty):
        cost=price*qty + self.c["modeled_cost_per_share"]*qty
        if cost>self.s.cash: return
        self.s.cash-=cost
        if side=="UP": self.s.up+=qty
        else: self.s.down+=qty
        self.s.fills+=1

    def merge(self):
        qty=min(self.s.up,self.s.down)
        if qty<=0:return
        self.s.up-=qty; self.s.down-=qty; self.s.cash+=qty; self.s.merges+=1

def main():
    with open("config.json") as f: cfg=json.load(f)
    e=B27BPaperEngine(cfg)
    print("B27B PAPER ENGINE STARTED", flush=True)
    print("PAPER ONLY - no credentials, signing, or live orders", flush=True)
    while True:
        # Synthetic heartbeat until a suitable lawful live market feed is configured.
        mid=max(.1,min(.9,.5+random.gauss(0,.015)))
        spread=.02
        ub,ua=mid-spread/2,mid+spread/2
        db,da=1-mid-spread/2,1-mid+spread/2
        q=e.desired_quotes(ub,ua,db,da)
        if q and random.random()<.02:
            side=random.choice(["UP","DOWN"])
            e.fill(side,q[0] if side=="UP" else q[1],cfg["base_order_shares"])
            e.merge()
        print(json.dumps({"status":"paper","cash":round(e.s.cash,2),"up":e.s.up,"down":e.s.down,"fills":e.s.fills,"merges":e.s.merges}),flush=True)
        time.sleep(60)

if __name__=="__main__": main()

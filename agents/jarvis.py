import time
from agents.state import enqueue, heartbeat

BASELINE = [
    ("fetch_data_quality", {"scope":"paper"}),
    ("ultron_risk_review", {"scope":"paper"}),
    ("vision_experiment", {"objective":"improve out-of-sample robustness"})
]

def seed_if_needed():
    from agents.state import connect
    con=connect()
    n=con.execute("select count(*) from jobs where status in ('queued','running')").fetchone()[0]
    if n == 0:
        for kind,payload in BASELINE:
            enqueue(kind,payload)

def main():
    while True:
        heartbeat("JARVIS","orchestrating")
        seed_if_needed()
        time.sleep(30)

if __name__ == "__main__":
    main()

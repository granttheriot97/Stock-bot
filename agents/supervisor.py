import subprocess, sys, time

COMMANDS={
 "jarvis":[sys.executable,"-m","agents.jarvis"],
 "worker":[sys.executable,"-m","agents.worker"],
}
procs={}

def start(name):
    procs[name]=subprocess.Popen(COMMANDS[name])

def main():
    for name in COMMANDS: start(name)
    while True:
        time.sleep(5)
        for name,p in list(procs.items()):
            if p.poll() is not None:
                start(name)

if __name__=="__main__":
    main()

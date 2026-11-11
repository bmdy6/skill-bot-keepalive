#!/usr/bin/env python3
"""Bounded minute-heartbeat loop for bot-keepalive.

Usage:
  python3 -u heartbeat_loop.py --dir RUN_DIR --run-id ID --start EPOCH --deadline EPOCH [--interval 60] [--tz-offset 8]

Writes RUN_DIR/heartbeats.jsonl (one line per heartbeat) and RUN_DIR/events.jsonl,
writes a kind=final line at the deadline, then exits. A flock on RUN_DIR/run.lock
keeps a single loop per run, and nothing is written after the final line.
"""
import json, time, datetime, os, sys, fcntl, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
ap.add_argument("--run-id", required=True)
ap.add_argument("--start", type=float, required=True)
ap.add_argument("--deadline", type=float, required=True)
ap.add_argument("--interval", type=float, default=60.0)
ap.add_argument("--tz-offset", type=float, default=0.0, help="hours from UTC for timestamps")
a = ap.parse_args()

P = os.path.abspath(a.dir)
os.makedirs(P, exist_ok=True)
START = a.start
DEADLINE = a.deadline
RUN_ID = a.run_id
INTERVAL = a.interval
TZ = datetime.timezone(datetime.timedelta(hours=a.tz_offset))
HS_PATH = os.path.join(P, "heartbeats.jsonl")
EV_PATH = os.path.join(P, "events.jsonl")
PID_PATH = os.path.join(P, "loop.pid")
LOCK_PATH = os.path.join(P, "run.lock")

def stamp(t):
    return datetime.datetime.fromtimestamp(t, TZ).isoformat()

def load_hs():
    if not os.path.exists(HS_PATH):
        return []
    with open(HS_PATH) as f:
        return [json.loads(x) for x in f if x.strip()]

def append_jsonl(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())

def already_final(hs=None):
    hs = load_hs() if hs is None else hs
    return bool(hs) and hs[-1].get("kind") == "final"

lockf = open(LOCK_PATH, "a+")
try:
    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.stderr.write("lock held; another loop is running\n")
    sys.exit(0)

pid = os.getpid()
now = time.time()
lockf.seek(0)
lockf.truncate()
lockf.write(json.dumps({"run_id": RUN_ID, "pid": pid, "acquired": now, "acquired_at": stamp(now)}) + "\n")
lockf.flush()
os.fsync(lockf.fileno())
with open(PID_PATH, "w") as f:
    f.write(str(pid) + "\n")
    f.flush()
    os.fsync(f.fileno())

hs = load_hs()
if already_final(hs):
    append_jsonl(EV_PATH, {"event": "loop_exit_already_final", "pid": pid, "epoch": time.time(), "timestamp": stamp(time.time()), "run_id": RUN_ID})
    sys.exit(0)

append_jsonl(EV_PATH, {
    "event": "loop_start",
    "run_id": RUN_ID,
    "pid": pid,
    "epoch": now,
    "timestamp": stamp(now),
    "resume_from_seq": hs[-1]["seq"] if hs else 0,
    "official_start_epoch": START,
    "deadline_epoch": DEADLINE,
})

def write_hb(kind):
    now = time.time()
    hs = load_hs()
    if already_final(hs):
        return None
    last_epoch = hs[-1]["epoch"] if hs else START
    seq = (hs[-1]["seq"] if hs else 0) + 1
    h = {
        "epoch": now,
        "timestamp": stamp(now),
        "monotonic": time.monotonic(),
        "leg": 1,
        "kind": kind,
        "status": "success",
        "seq": seq,
        "gap": now - last_epoch,
        "pid": pid,
        "source": "background_loop",
    }
    append_jsonl(HS_PATH, h)
    return h

hs = load_hs()
if not hs:
    kind = "final" if time.time() >= DEADLINE else "normal"
    write_hb(kind)
    if kind == "final":
        append_jsonl(EV_PATH, {"event": "deadline_stop", "pid": pid, "epoch": time.time(), "timestamp": stamp(time.time()), "run_id": RUN_ID})
        sys.exit(0)

while True:
    if already_final():
        sys.exit(0)
    now = time.time()
    hs = load_hs()
    last = hs[-1]["epoch"] if hs else START
    if now >= DEADLINE:
        if not already_final(hs):
            write_hb("final")
            append_jsonl(EV_PATH, {"event": "deadline_stop", "pid": pid, "epoch": time.time(), "timestamp": stamp(time.time()), "run_id": RUN_ID})
        sys.exit(0)
    target = last + INTERVAL
    if target >= DEADLINE or (DEADLINE - last) <= INTERVAL:
        target = DEADLINE
    remain = target - time.time()
    if remain > 0:
        time.sleep(remain)
        continue
    kind = "final" if time.time() >= DEADLINE else "normal"
    write_hb(kind)
    if kind == "final":
        append_jsonl(EV_PATH, {"event": "deadline_stop", "pid": pid, "epoch": time.time(), "timestamp": stamp(time.time()), "run_id": RUN_ID})
        sys.exit(0)

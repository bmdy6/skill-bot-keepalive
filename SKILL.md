---
name: bot-keepalive
description: Use when an agent must keep a bounded background guard running for a set time (e.g. 1–3 h) with minute heartbeats, ~30-minute relays, a hard deadline, and a verifiable stop and usage report, while spending as little quota as possible. It does not promise the machine never sleeps.
---
# bot-keepalive (lean mode)

A small background script writes the minute heartbeats. The agent only checks in every 10–13 minutes, so one hour costs roughly 6–15 tool calls instead of ~130.

## Rules
- Wait with the platform's await tool (e.g. `AwaitShell`, max ~13 min per call). Never `sleep` in a foreground shell call; `sleep` inside the background script is fine.
- Only the parent agent creates or relays the guard. The guard never spawns sub-agents.
- Don't touch other keepalive scripts, network settings, scheduled routines or user work. Don't kill shared processes.
- Report only what you measured.

## Steps
1. **Set up the run.** Confirm the duration the user authorized. Create a fresh run dir, a unique run ID, a start epoch (`date +%s`) and a deadline = start + duration. The deadline never changes unless the user explicitly extends it.
2. **Read usage once** at the start and save the raw result. If you can't read it, write `unavailable`; don't guess.
3. **Start the loop fast** (aim for the first heartbeat within a few dozen seconds of the start):
   `nohup python3 -u scripts/heartbeat_loop.py --dir RUN_DIR --run-id ID --start START --deadline DEADLINE --tz-offset H > RUN_DIR/loop.out 2>&1 &`
   Start it as a background shell job and record the PID. The script writes a heartbeat immediately, then every 60 s. At the deadline it writes `kind=final` and exits. A flock keeps one loop per run, and nothing is written after `final`.
4. **Check in rarely.** Await the background job in 10–13 min chunks. After each chunk run one quick check: the log tail, whether the PID is alive and the max gap so far. If the loop dies before the deadline, restart it once and log that. Never start a second loop while the PID is alive.
5. **Relay** about every 30 min (never later than 45). Return `RELAY` with the loop still running. The parent resumes the same worker with the same deadline.
6. **Stop.** After the deadline, confirm the loop wrote `final` and exited. Write `summary.json` (FINAL) and release the lock.
7. **Report:**
   - heartbeats and successes
   - the delay before the first heartbeat
   - the max adjacent gap
   - every gap over 90 s, with times
   - how late the stop was
   - restarts, relays and total tool calls
   - the usage change

   Usage windows are usually account-wide and shared, so the change can't be attributed only to this run.

## Alternative: per-minute agent heartbeats
Use this only when the user wants the agent itself to wake every minute. Run a serial await, then write the heartbeat in a separate shell call. Wait max(5, 55 − elapsed − last latency) seconds. If a write would land under 50 s, log `early_attempt` and wait once more to about 52 s. This costs several times more quota, and platform stalls can still cause gaps of 100–230 s.

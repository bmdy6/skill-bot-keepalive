# bot-keepalive

Keep an agent's background guard alive for a bounded time with minute heartbeats, while using about a tenth of the quota.

[简体中文](README.zh-CN.md) · [MIT](LICENSE)

## Quick start

```sh
gh repo clone bmdy6/skill-bot-keepalive .agents/skills/bot-keepalive
```

Then tell your agent:

> Use bot-keepalive to keep the guard running for 1 hour.

## How it works

- `scripts/heartbeat_loop.py` runs in the background. It appends one heartbeat per minute to `heartbeats.jsonl`, writes a `final` line at the deadline and exits by itself.
- The agent awaits that job in 10–13 minute chunks, relays about every 30 minutes and writes a `summary.json` at the end.

## Measured (one 1-hour trial)

| | Per-minute agent heartbeats | Lean mode (this skill) |
|---|---|---|
| Agent tool calls per hour | ~130 | 15 |
| Max gap between heartbeats | 87–234 s across runs | 60 s |
| Heartbeats | 62–66 / hour, all written | 60 / 60, all written |

Usage counters are usually shared account-wide, so treat any quota comparison as indicative only.

## Boundaries

It does not stop the computer from sleeping. It does not touch your network, other keepalive scripts or scheduled tasks. It stops at the deadline and never auto-repeats.

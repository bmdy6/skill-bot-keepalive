# bot-keepalive

Keep your client connected to remote sessions on a Grok cloud computer to keep using Claude.

[简体中文](README.md) · [MIT](LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/hero-dark.png">
  <img src="docs/readme/hero-light.png" alt="A short run of heartbeats.jsonl, ending with a final line" width="838">
</picture>

Keepalive step only: `scripts/heartbeat_loop.py`, interval 2 seconds, ending with `final`. Normally it writes once a minute until the deadline you set.

## Quick start

```sh
gh repo clone bmdy6/skill-bot-keepalive .agents/skills/bot-keepalive
```

Then tell your agent:

> Use bot-keepalive to check the remote session connection, then keep it alive for 1 hour.

Requires Python 3, a skill-capable agent, `gh` and network access.

## What you get

- **Connection checks.** Say “not connected”; the agent checks network → SSH → service → client → reboot status and identifies the failing layer.
- **Keepalive.** `scripts/heartbeat_loop.py` appends one line per minute to `heartbeats.jsonl`. The agent watches about every 10 minutes. One hour uses roughly 6–15 agent tool calls instead of about 130.
- **Disconnect repair.** After consecutive ping failures, `scripts/netwatch.sh` runs gentle rebind and restun commands.

## How it works

1. The agent checks the connection layers above and reports the failing layer.
2. The agent starts the script, which writes a heartbeat immediately and then every 60 seconds.
3. The agent checks about every 10 minutes and relays about every 30 minutes. If awaiting stops, the machine may sleep.
4. At the deadline the script writes a `final` line and exits; the agent writes `summary.json` and reports what it measured.

## Measured (one 1-hour trial)

| | Per-minute agent heartbeats | Lean mode (this skill) |
|---|---|---|
| Agent tool calls per hour | ~130 | 15 |
| Max gap between heartbeats | 87–234 s across runs | 60 s |
| Heartbeats | 62–66 / hour, all written | 60 / 60, all written |

Usage counters are usually account-wide, so quota comparisons are indicative only.

## Lesson from testing

The agent's await keeps the cloud machine awake, not the script. After the agent stops awaiting, the machine sleeps and heartbeats pause. The agent must await in ~10 minute chunks until the deadline.

## Options

| Option | Purpose |
|---|---|
| Duration | Authorized duration; the example requests 1 hour. Only you can extend the deadline. |
| Lean mode | The default. A background script writes heartbeats; the agent checks about every 10 minutes. |
| Per-minute agent heartbeats | Use this only when you ask the agent itself to wake every minute. It costs several times more quota. |


## Auto-heal disconnects

Public endpoint changes can stale the cloud-to-peer DERP path while the reverse path still works. By default, `scripts/netwatch.sh` pings every 30 seconds; after 2 consecutive failures it runs gentle `debug rebind` and `debug restun`, at most once per minute, and logs repairs without quota usage. It never runs `down`/`up`, restarts tailscaled, or touches the client or remote daemon.

Successful pings do not prove the client is connected; check service connections and client logs too.

Start with nohup; a supervisor can restart a missing process. Duplicate starts exit 0 via flock:

```sh
nohup env TS_CLI=/path/to/tailscale TS_SOCKET=/path/to/ts.sock PEER_IP=100.x.x.x \
  LOG=netwatch.log bash scripts/netwatch.sh >/dev/null 2>&1 &
```

## FAQ and boundaries

**Does it guarantee no disconnects or sleep?** No. Neither uninterrupted connections nor an always-awake computer are guaranteed.

**Is the script enough?** No. Without the agent awaiting, sleep pauses heartbeats.

**Does it start again after the deadline?** No. It stops and never auto-repeats.

**Can I attribute the usage change to this run alone?** No. Usage windows are usually shared account-wide.

**Does it change my network or other tasks?** Keepalive does not; netwatch only performs the gentle repairs described above.

<details><summary>Rights and legal detail</summary>

Released under the MIT License. The skill guides connection checks, keepalive and gentle disconnect repair within the authorized time. It guarantees neither uninterrupted connections nor an always-awake computer, never auto-repeats, and does not attribute shared account usage to one run alone.

</details>

## Contributing

Open a reproducible issue or pull request.

## License

[MIT](LICENSE).

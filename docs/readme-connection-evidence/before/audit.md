# README audit

Score: 67/100

| Check | Result | Evidence |
|---|---|---|
| V2 | pass | Passed |
| V3 | pass | Passed |
| V4 | pass | Passed |
| V5 | fail | Unbacked claim: One hour uses roughly 6–15 agent tool calls instead of about 130.; Unbacked claim: 一小时大约只要 6 到 15 次工具调用，而不是大约 130 次。; Unbacked claim: `scripts/heartbeat_loop.py` appends one line per minute to `heartbeats.jsonl`.; Unbacked claim: `scripts/heartbeat_loop.py` 每分钟往 `heartbeats.jsonl` 追加一行。; Unbacked claim: At the deadline the script writes a `final` line and exits; the agent writes `summary.json` and reports what it measured.; Unbacked claim: 到截止时间脚本会写一条 `final` 后退出，agent 再写出 `summary.json`，并报告实际测到的结果。; Invalid supplemental fact source: lean-tool-calls; Invalid supplemental fact source: minute-heartbeats-script; Invalid supplemental fact source: agent-checks-10min; Invalid supplemental fact source: await-keeps-awake; Invalid supplemental fact source: freeze-lesson; Invalid supplemental fact source: no-never-sleep-promise; Invalid supplemental fact source: heartbeat-every-60s-skill; Invalid supplemental fact source: relay-30min; Invalid supplemental fact source: await-10min-chunks; Invalid supplemental fact source: summary-json; Invalid supplemental fact source: shared-usage; Invalid supplemental fact source: deadline-unless-extended; Invalid supplemental fact source: dont-touch-network; Invalid supplemental fact source: alt-per-minute-cost |
| V6 | fail | Word budget: 508 > 400 |
| V7 | pass | Passed |

github-api

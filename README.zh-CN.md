# bot-keepalive

在限定时间内，让 agent 的后台守护每分钟心跳一次，额度只花原来的十分之一左右。

[English](README.md) · [MIT](LICENSE)

## 快速开始

```sh
gh repo clone bmdy6/skill-bot-keepalive .agents/skills/bot-keepalive
```

然后告诉你的 agent：

> 用 bot-keepalive 保活一小时。

## 工作方式

- `scripts/heartbeat_loop.py` 在后台跑，每分钟往 `heartbeats.jsonl` 写一条心跳，到截止时间写一条 `final` 后自己退出。
- agent 每 10 到 13 分钟看一眼，大约 30 分钟接力一次，结束时写 `summary.json`。

## 实测（一次一小时）

| | 旧办法：agent 每分钟自己写 | 省额度模式（本技能） |
|---|---|---|
| 每小时工具调用 | 约 130 次 | 15 次 |
| 心跳最大间隔 | 87 到 234 秒（多次运行） | 60 秒 |
| 心跳 | 每小时 62 到 66 次，全部写成功 | 60 次，全部写成功 |

额度一般是整个账户共用的，所以额度对比只能当参考。

## 边界

它不能阻止电脑休眠，不动网络、别的保活脚本或定时任务。到截止时间就停，不会自动续跑。

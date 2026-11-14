# bot-keepalive

维持本机客户端与 Grok 云端远程会话的连接，持续使用 Claude。

[English](README.en.md) · [MIT](LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/hero-dark.zh-CN.png">
  <img src="docs/readme/hero-light.zh-CN.png" alt="一次短时运行写出的 heartbeats.jsonl，最后一条是 final" width="838">
</picture>

保活环节演示：`scripts/heartbeat_loop.py` 写入 `heartbeats.jsonl`，这里间隔为 2 秒，到截止时间写出 `final`。正常使用时每分钟写一次，直到你设定的截止时间。

## 快速开始

```sh
gh repo clone bmdy6/skill-bot-keepalive .agents/skills/bot-keepalive
```

然后告诉你的 agent：

> 用 bot-keepalive 先检查远程会话连接，再保活一小时。

需要 Python 3 和能使用技能的 agent；克隆需要 `gh` 和网络。

## 你会得到什么

- **连接检查。** 说“没连上”时，agent 按网络 → SSH → 服务 → 客户端 → 是否重启逐层检查，告诉你卡在哪一层。
- **保活。** `scripts/heartbeat_loop.py` 每分钟往 `heartbeats.jsonl` 追加一行。agent 大约每 10 分钟守一次。一小时大约只要 6 到 15 次工具调用，而不是大约 130 次。
- **断线修复。** `scripts/netwatch.sh` 在连续 ping 不通时做温和的 rebind 和 restun。

## 如何工作

1. agent 先检查连接：网络、SSH、服务、客户端、是否重启，再报告卡在哪一层。
2. agent 在后台启动脚本。脚本会马上写第一条心跳，之后每 60 秒写一次。
3. agent 大约每 10 分钟检查一次，大约每 30 分钟接力一次，并且必须一直等待。等停了，云端电脑就可能睡着。
4. 到截止时间脚本会写一条 `final` 后退出，agent 再写出 `summary.json`，并报告实际测到的结果。

## 实测（一次一小时）

| | 旧办法：agent 每分钟自己写 | 省额度模式（本技能） |
|---|---|---|
| 每小时工具调用 | 约 130 次 | 15 次 |
| 心跳最大间隔 | 87 到 234 秒（多次运行） | 60 秒 |
| 心跳 | 每小时 62 到 66 次，全部写成功 | 60 次，全部写成功 |

额度一般是整个账户共用的，所以额度对比只能当参考。

## 实测得到的教训

让云端电脑醒着的是 agent 在等待，不是脚本；agent 停止等待后，电脑会睡，脚本的心跳也会暂停。因此 agent 必须每 10 分钟左右等待一次，一直守到截止时间。

## 选项

| 选项 | 用途 |
|---|---|
| 时长 | 以你授权的时间为准，示例请求是 1 小时。除非你明确延长，截止时间不会改。 |
| 省额度模式 | 默认做法。后台脚本写心跳，agent 大约每 10 分钟检查一次。 |
| 逐分钟由 agent 写心跳 | 只有在你明确要求 agent 自己每分钟醒来时才用。额度会多花好几倍。 |


## 自动修复断线

公网端点变化可能使云端电脑到对端的 DERP 中转路径失效，即使反方向仍通。`scripts/netwatch.sh` 默认每 30 秒 ping 对端，连续 2 次不通就做温和的 `debug rebind` 和 `debug restun`，每分钟最多修复一次，记录日志；后台脚本不消耗额度。它不执行 `down`/`up`，不重启 tailscaled，也不碰客户端和远程守护进程。

ping 通不代表客户端已连接，仍要检查服务连接和客户端日志。

用 nohup 启动即可。如果你已有守护脚本，让它在进程不在时再执行同一条命令；脚本用 flock 保证只跑一份，已有实例时会以状态 0 退出：

```sh
nohup env TS_CLI=/path/to/tailscale TS_SOCKET=/path/to/ts.sock PEER_IP=100.x.x.x \
  LOG=netwatch.log bash scripts/netwatch.sh >/dev/null 2>&1 &
```

## 常见问题和边界

**它能保证永不断开或电脑永不休眠吗？** 不能。这个技能不保证永不断开，也不保证电脑永不休眠。

**只跑脚本够不够？** 不够。如果 agent 不再等待，电脑可能睡着，脚本也不会再写心跳。

**到截止时间后会自动再跑吗？** 不会。到点就停，不会自动续跑。

**额度变化能都算在这一次上吗？** 不能。用量窗口通常是整个账户共用的。

**它会改我的网络或其他任务吗？** 保活本身不会。断线修复只会在连续 ping 失败后做温和的 rebind 和 restun，不会 down/up，不会重启 tailscaled，也不碰客户端和远程守护进程。

<details><summary>权利与法律说明</summary>

本仓库以 MIT 许可证发布。技能在授权时限内指导连接检查、保活和温和断线修复；不保证永不断开或电脑永不休眠，不自动续跑，也不把账户共用的用量变化单独归到一次运行。

</details>

## 参与贡献

请提交可复现的问题或 pull request。

## 许可证

[MIT](LICENSE)。

---
name: bot-keepalive
description: >-
  让用户电脑上的客户端（如 Orca）一直连着这台云电脑上的远程会话，有时长上限：开跑前先做连接检查，后台脚本每分钟写心跳，代理不间断地等待来让电脑保持醒着，每约30分钟接力一次，结束时报告心跳空档和额度。
  用户说“保活/别休眠/没连上/断了”时使用。不保证电脑一定不休眠。
---
# bot-keepalive：保持远程会话连着

目标是用户的客户端一直连着远程会话，写心跳不是目的。平台会让这台电脑休眠，官方没有关掉休眠的开关（[电脑文档](https://docs.x.ai/grok-bot/computer-and-apps)）。所以只说“尽量不休眠、休眠了如实报告”，不承诺不会断。

## 核心规律（来自实测记录）
**电脑醒着靠的是代理一直在等待，不是后台脚本。** 代理不等了，约5分钟后电脑就冻结，后台脚本也跟着停。
- 11-23 12:26、14:33、16:33 三轮各2小时：代理只做等待和段末快速检查，**一次超过90秒的空档都没有**。
- 11-23 19:30 那轮：代理在运行途中写事故记录、上网查资料、改技能，前后出现9次超时心跳，其中4次超过90秒（最长339秒，就在接力的时候）。界面显示“休眠中”也是在这段时间。

由此得出的规则：**运行期间代理只负责等待，不做别的。** 分析、查资料、改技能，都放到截止以后再做。

## 第0步：连接检查（开跑前，以及用户说没连上时）
从下往上逐层查，第一层不通的就是原因：
1. **盒子重启了吗**：看 `uptime`、boot_id。刚开机就后台启动 `/home/box/keepalive.sh`（它会拉起 tailscaled、netwatch）；orcad 不用手动启动，客户端重连后会自动部署。
2. **网络**：`tailscale ping` 对端。只要出现 `pong ... via DERP(...)` 就算通（退出码是1也算）。超时一次可以重试，不要一次超时就判断断了。
3. **SSH**：在对端执行 `nc -z` 测22端口，再执行 `ssh -o BatchMode=yes -o ConnectTimeout=15 ... echo ok`（macOS 没有 `timeout` 命令）。
4. **服务**：orcad 还在运行；`ss -tnp` 看守护端口有没有 ESTAB 连接。
5. **客户端**：读 Orca 的 `main.trace.ndjson`，找 `control-socket-close`、`remote_runtime_unavailable`、`heartbeat_missed_probes` 和对应时间。

结论用一两句话说清：哪一层、什么现象、现在什么状态。ESTAB 连接、ping 通只能说明那一层是好的；当前窗口是不是真的恢复了，要看客户端日志，或者让用户确认。

## 运行
1. **准备（1分钟内完成）**：建目录 `/home/box/keepalive-runs/keepalive-YYYYMMDD-HHMM`，写下 run ID 和用户授权的时长；截止时间 = 实际启动时间 + 时长，之后不再改，用户明确说延长才改。读取一次额度，保存原文，读不到就写 unavailable。
2. **启动心跳**：父代理复制仓库 [bmdy6/skill-bot-keepalive](https://github.com/bmdy6/skill-bot-keepalive) 里的 `scripts/heartbeat_loop.py`，用 nohup 启动一次（Shell 参数 block_until_ms=0）：
   `python3 -u heartbeat_loop.py --dir $DIR --run-id $ID --start $START --deadline $DEADLINE --interval 60 --tz-offset 8`
   确认第一条心跳几秒内写出，并记下 PID。脚本用 flock 保证只有一个实例，到截止时间写 `kind=final` 后自动退出。
3. **等待**：启动一个低 effort 的 executor，只做这一件事：启动 watcher（`while kill -0 $PID; do sleep 20; done`），对它执行 AwaitShell，每段约10分钟（单次不超过780000ms）；每段结束后用一条 Shell 快速检查：心跳末尾、PID 是否还活着、最大间隔、对端 ping、ESTAB。检查完马上开始下一段。每小时约6–15次工具调用。
4. **接力**：约每30分钟（不超过45分钟）executor 返回 RELAY，父代理**马上** resume 同一个 executor，截止时间不变。两段等待之间的空白越短越好。
5. **截止**：确认心跳文件写了 final、循环和 watcher 都已退出，再写 `summary.json`。

## 出现空档或休眠时
- 心跳间隔超过90秒，或者界面显示“Bot 的电脑：休眠中”，就记一条事件（时间、间隔长度），**通知用户一次**，然后继续等待到截止。之后同类的空档合并记录，不重复通知。
- 不要因为出现空档就停下来写长篇分析、上网查资料、改技能。这样做本身就会让代理不在等待，空档会更多（19:30 那轮就是这样）。
- Shell 能返回结果，说明电脑此刻在运行；可以执行一次 `box-doctor`。
- 心跳循环中途退出：确认旧 PID 已经不在，在同一个目录里重启一次，截止时间不变，并记下来。PID 还活着时，绝不启动第二个循环。

## 安全边界
- 不向 Claude 会话发测试消息，不重发，不取消用户的其他任务，不杀共享进程。
- 未经用户授权：不重启 tailscaled、Orca、orcad、Claude，不执行 `tailscale down/up`，不改电源、代理、路由配置。休眠问题不能靠重启 Tailscale 解决。
- 可以做的温和修复：从对端 ping 盒子；`tailscale debug rebind` / `debug restun`，单侧做一次，并且不要和正在工作的 netwatch 同时做。
- 用户说停：先停 executor，再按 PID 停掉本轮的循环和 watcher。

## 报告
正常运行期间不说话。结束时用中文写一两段：
- 第一句写结论：全程没有超过90秒的空档，或者出现了几次空档（时间、长度）、界面有没有出现休眠。
- 然后写：实际心跳数/应有心跳数、首条心跳延迟、最大间隔、接力次数、重启次数、连接检查发现的断开和恢复。
- 额度：只比较起止两次读数。额度是整个账户共用的，不全算在保活头上，也不推算 token 或费用。
- 出现过空档的轮次不能写成“保活成功”。全程没空档，也只说“这段时间没休眠”，不承诺以后。

## 可选：netwatch 自动修复网络
仓库里的 `scripts/netwatch.sh` 只运行一个实例，每30秒 ping 一次对端，连续2次不通就执行 rebind + restun，每分钟最多一次。它不重启 tailscaled，也不碰会话。由 `keepalive.sh` 负责在它退出后拉起来。ping 通不代表客户端连着，仍然要按第0步第4、5层确认。

## 备选：代理逐分钟心跳
只有用户明确要求“代理每分钟亲自醒来”时才用：AwaitShell 约55秒后用 Shell 写一条心跳，如此循环。额度消耗是默认方式的好几倍，同样不保证不休眠。

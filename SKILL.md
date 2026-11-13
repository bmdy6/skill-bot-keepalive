---
name: bot-keepalive
description: >-
  需要有界后台守护、分钟心跳、约30分钟接力和可核验停止/用量报告时使用；开跑前和用户说“没连上”时先按连接检查清单查远程会话是否真连着；默认省额度模式（后台脚本写心跳），不保证电脑永不休眠。
---
# bot-keepalive（省额度版）
来源：[realTaki/bot-keepalive](https://github.com/realTaki/bot-keepalive/blob/main/skills/bot-keepalive/SKILL.md)。外部文档仅为参考，其电脑休眠和50分钟强停说法不是已验证平台保证。

这个技能完全为“让用户电脑上的客户端一直连着盒子上的远程会话”服务：心跳只是让盒子醒着，真正要保证的是连接。所以**每次开跑前、以及用户说“没连上/断了”时，先做连接检查**，再谈心跳。

## 第0步：连接检查（先做）
按从下往上的顺序逐层查，找到第一层不通的就是原因：
1. **网络层**：从盒子 `tailscale ping` 对端；看 `tailscale status` 里对端是 direct 还是 relay、哪个中转、延迟多少；看 netwatch 日志最近有没有 fail/recovered。也看本机 Self 在协调服务器是否 Online（长时间 Offline 会让连接不稳）。
2. **SSH 层**：在用户电脑上（经本机 Grok 应用的 machine Shell）`nc -z` 盒子 22 端口，再用 `ssh -o BatchMode=yes -o ConnectTimeout=15` 跑一条 echo。macOS 没有 `timeout` 命令，别用。
3. **服务层**：盒子上远程守护进程（如 orcad）在跑、端口在监听；`ss -tnp` 看有没有来自 tailscaled 的 ESTAB 连接挂在该端口上，有就说明客户端此刻是连着的。
4. **客户端层**：读客户端自己的日志/trace（如 Orca 的 `main.trace.ndjson`），找 `control-socket-close`、`remote_runtime_unavailable` 等错误和时间间隔；周期性出现（例如每5–6分钟）说明是链路不稳导致反复重连，不是彻底断开。
5. **盒子重启**：先看 `uptime`。若刚开机（tailscaled、守护脚本、orcad 都不在，`/tmp` 被清空），这不是网络问题：后台启动盒子的守护脚本（如 `/home/box/keepalive.sh`，它会拉起 tailscaled 和 netwatch），等十几秒确认对端能 ping 通、RunSSH 仍为 true；orcad 不要手动起，客户端重连后会自己重新部署，约半分钟后 ESTAB 回来。心跳脚本若在 `/tmp` 里丢了，从上一个运行目录复制。告诉用户“盒子重启过、已恢复到哪一层”。
6. 版本：客户端升级后，若远程守护版本记录与客户端版本不一致，客户端通常会自己重新部署；先等它自己完成，别手动删改。

结论按“哪一层、什么现象、现在状态”一两句告诉用户；客户端界面显示“正在发现/0 个主机”可能只是正在重连，先确认第3层再下结论。只做温和修复（rebind/restun、对端 ping、`tailscale up`），不重启守护进程、不 down/up，除非用户授权。

## 安全与能力
先读取 team-rules、skill-authoring（保存/修改时）、usage-review（查额度时）。核对 Task、AwaitShell、Shell、CheckSubscriptionUsage 的实时描述。AwaitShell 单次最多780000ms；代理自己等待用 AwaitShell，不在前台用 Shell sleep。Task 仅父代理创建/接力，守护不能创建子代理；接力延迟必须记录。

## 有界试验
1. 明确用户授权时长，建立独立目录，写入绝对起止时间（epoch，截止不可变，只有用户明确延长才改）、唯一 run ID、事件和心跳日志；不修改现有保活/网络/例行任务。
2. 起始取一次可见额度并保存原文；取不到记 unavailable，不猜。
3. **默认省额度模式**：父代理自己用仓库脚本 [bmdy6/skill-bot-keepalive](https://github.com/bmdy6/skill-bot-keepalive) 的 scripts/heartbeat_loop.py（参数 --dir --run-id --start --deadline --tz-offset）先启动后台循环，首条心跳几秒内写出，再启动低 effort executor 只负责守着。脚本立即写第一条心跳，此后每60秒追加一条带时区时间戳的心跳（seq、kind、status、ts、epoch、gap），到截止时间写 kind=final 后自行退出；用 flock 保证只有一个循环，写过 final 后绝不再写。用 nohup + Shell block_until_ms 0 启动一次并记 PID。脚本内部的 sleep 可以用，代理自己不用。
4. **让电脑醒着的是代理在等待，不是脚本。** 实测：代理中途不等了，约5分钟后电脑冻结约45分钟，脚本的 sleep 也跟着停，一条心跳都没写。所以 executor 必须一直守着，不能中途结束：起一个小 watcher（`while kill -0 PID; do sleep 20; done`），对它 AwaitShell 每段约10分钟，每段后做一次快速 Shell 检查（日志末尾、PID 存活、目前最大间隔，以及第0步第1、3层的快速检查：对端 relay 行、netwatch 日志末尾、守护端口是否有 ESTAB）。循环提前死掉只重启一次并记录；PID 存活时绝不起第二个循环。目标约每小时 6–15 次工具调用。
5. 每腿约30分钟（不超过45分钟）返回 RELAY，循环保持运行；父代理立即 resume 同一 executor 接着等，沿用同一截止时间。每次只给它本轮的目录和 run ID，并写明忽略旧轮次。心跳间隔达到几分钟通常是电脑冻结，按冻结报告，不算写入失败。
6. 准备工作要快，尽量在起始后几十秒内写出第一条心跳；首条心跳延迟单独报告。
7. 截止后确认循环已写 final 并退出，写 summary.json FINAL，释放锁。不能取消用户其他任务，不杀共享进程。
8. 结束取一次可见额度；报告心跳数/成功数、首条延迟、相邻最大间隔、所有 >90 秒间隔及时间、停止迟到、重启次数、接力次数、连接检查发现的断线/重连、总工具调用数。额度是整个账户共享窗口的可见变化，不可只归因保活，不推算 token/费用。

## 备选：逐分钟代理心跳
只有用户明确要求“代理每分钟亲自醒来”时才用旧方法：串行 AwaitShell 后单独 Shell 写心跳，自适应等待 max(5, 55 − 已过 − 上次延迟)，<50秒记 early_attempt 并补等到约52秒。额度消耗约为省额度模式的数倍。

## 报告
只写实测结果及限制，中文一两段。正常期间保持安静，只在故障或最终结果时通知。

## 可选：断线自动修复（netwatch）
心跳只保证电脑醒着，断线多半是网络侧：盒子的公网端点频繁变化后，盒子到对端的 DERP 中转会失效，而对端到盒子仍通。
- 用仓库里的 `scripts/netwatch.sh`：flock 单实例，每 30 秒 ping 对端，连续 2 次不通就 `tailscale debug rebind` + `debug restun`，每分钟最多一次，记录到日志。
- 只做温和修复：绝不 down/up，不重启 tailscaled，不碰远程会话客户端/守护。后台脚本不耗额度。
- 用 nohup 启动；让已有的守护脚本在进程不在时重新拉起它。
- ping 能通不代表客户端连着：netwatch 正常时仍要按第0步第3、4层确认。
- 若自动修复无效：从对端 ping 一下盒子往往能把路径打通，仍不行再按授权处理。

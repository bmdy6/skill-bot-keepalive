#!/bin/bash
# Optional Tailscale auto-heal watchdog for bot-keepalive.
# Gentle only: ping the peer, then debug rebind + restun.
# Never runs down/up and never restarts tailscaled.
#
# Required: TS_CLI and PEER_IP, or --cli and --peer.
# Optional: TS_SOCKET, INTERVAL (default 30), FAILS (default 2), LOG, LOCK,
#           or the matching --socket --interval --fails --log --lock flags.

usage() {
  cat <<'USAGE' >&2
Usage: netwatch.sh [--cli PATH] [--socket PATH] [--peer IP]
                   [--interval SECONDS] [--fails N] [--log PATH] [--lock PATH]

TS_CLI and PEER_IP are required (flags override environment variables).
INTERVAL defaults to 30, FAILS defaults to 2.
A flock on the lock file keeps a single instance; a second start exits 0.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --cli) TS_CLI=$2; shift 2 ;;
    --socket) TS_SOCKET=$2; shift 2 ;;
    --peer) PEER_IP=$2; shift 2 ;;
    --interval) INTERVAL=$2; shift 2 ;;
    --fails) FAILS=$2; shift 2 ;;
    --log) LOG=$2; shift 2 ;;
    --lock) LOCK=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

INTERVAL=${INTERVAL:-30}
FAILS=${FAILS:-2}
LOG=${LOG:-netwatch.log}
if [ -z "${LOCK:-}" ]; then
  if [ "${LOG%.log}" != "$LOG" ]; then
    LOCK=${LOG%.log}.lock
  else
    LOCK=${LOG}.lock
  fi
fi

if [ -z "${TS_CLI:-}" ] || [ -z "${PEER_IP:-}" ]; then
  echo "TS_CLI and PEER_IP are required" >&2
  usage
  exit 2
fi

case "$INTERVAL$FAILS" in
  *[!0-9]*) echo "INTERVAL and FAILS must be positive integers" >&2; exit 2 ;;
esac
if [ "$INTERVAL" -lt 1 ] || [ "$FAILS" -lt 1 ]; then
  echo "INTERVAL and FAILS must be positive integers" >&2
  exit 2
fi

mkdir -p "$(dirname -- "$LOG")" "$(dirname -- "$LOCK")"
exec 9>"$LOCK"
flock -n 9 || exit 0

# Build a command array so timeout(1) can exec the CLI (it cannot call a function).
ts_cmd=("$TS_CLI")
if [ -n "${TS_SOCKET:-}" ]; then
  ts_cmd+=(--socket="$TS_SOCKET")
fi

fails=0
last_fix=0
FIX_COOLDOWN=60

while true; do
  if timeout 8 "${ts_cmd[@]}" ping -c 1 --timeout 6s "$PEER_IP" >/dev/null 2>&1; then
    if [ "$fails" -ge "$FAILS" ]; then
      echo "$(date '+%F %T') recovered after $fails fails" >>"$LOG"
    fi
    fails=0
  else
    fails=$((fails + 1))
    now=$(date +%s)
    if [ "$fails" -ge "$FAILS" ] && [ $((now - last_fix)) -ge "$FIX_COOLDOWN" ]; then
      "${ts_cmd[@]}" debug rebind >/dev/null 2>&1
      "${ts_cmd[@]}" debug restun >/dev/null 2>&1
      last_fix=$now
      echo "$(date '+%F %T') $fails fails -> rebind+restun" >>"$LOG"
    fi
  fi
  sleep "$INTERVAL"
done

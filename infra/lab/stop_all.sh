#!/bin/sh
# From your own computer: stop our llama-server screen sessions on the lab machines and
# report anything of ours that is still running. Run it after every session.
#
# Usage: sh infra/lab/stop_all.sh [host ...]     (default: $LAB_HOSTS)
#   SCREEN_NAME  screen session name [srv]
HOSTS="$*"
[ -z "$HOSTS" ] && HOSTS="$LAB_HOSTS"
[ -z "$HOSTS" ] && { echo "usage: $0 host... (or set LAB_HOSTS)" >&2; exit 2; }
sn="${SCREEN_NAME:-srv}"

for h in $HOSTS; do
  ssh -o BatchMode=yes "$h" "
  screen -S $sn -X quit >/dev/null 2>&1
  for i in \$(seq 1 30); do pgrep -u \$(id -un) llama-server >/dev/null || break; sleep 1; done
  echo \"\$(hostname): llama-server left: \$(pgrep -u \$(id -un) llama-server | wc -l), screens: \$(screen -ls 2>/dev/null | grep -c -E 'Detached|Attached'), processes of mine: \$(ps -u \$(id -un) --no-headers | wc -l)\"
  "
done

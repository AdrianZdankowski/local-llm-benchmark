#!/bin/sh
# From your own computer: (re)start llama-server for one model on a lab machine, inside a
# detached screen session. Waits for the previous llama-server of yours to exit, then runs
# the guard on the machine and only starts if it passes.
#
# Usage: sh infra/lab/start_server.sh <host> <model-key> [port]
#
# Environment (defaults in brackets):
#   LAB_REPO     repository path on the lab machine, relative to the remote home  [local-llm-benchmark]
#   SCREEN_NAME  screen session name                                              [srv]
#   START_HOUR, END_HOUR   passed to the guard                                    [19, 7]
[ -n "$2" ] || { echo "usage: $0 <host> <model-key> [port]" >&2; exit 2; }
h="$1"; m="$2"; port="${3:-8080}"
repo="${LAB_REPO:-local-llm-benchmark}"
sn="${SCREEN_NAME:-srv}"
env="START_HOUR=${START_HOUR:-19} END_HOUR=${END_HOUR:-7}"

ssh -o BatchMode=yes "$h" "
screen -S $sn -X quit >/dev/null 2>&1
for i in \$(seq 1 60); do pgrep -u \$(id -un) llama-server >/dev/null || break; sleep 1; done
sleep 2
cd $repo || exit 1
mkdir -p logs
export $env
sh infra/lab/guard.sh || exit 1
screen -dmS $sn sh -c 'export $env GUARD=infra/lab/guard.sh; sh infra/llama_server/serve.sh $m $port > logs/srv-\$(hostname).log 2>&1'
echo \"\$(hostname): serving $m on 127.0.0.1:$port (screen $sn)\"
"

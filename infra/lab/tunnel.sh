#!/bin/sh
# From your own computer: forward local ports to llama-server (127.0.0.1:REMOTE_PORT) on lab machines.
# Keeps running; Ctrl+C stops all tunnels.
#
# Usage: sh infra/lab/tunnel.sh host[:local_port] ...     (default hosts: $LAB_HOSTS)
#   Without an explicit local port, hosts get BASE_PORT, BASE_PORT+1, ... in order.
#   e.g. sh infra/lab/tunnel.sh host1:8081 host2:8082  ->  BENCH_BASE_URL=http://127.0.0.1:8081/v1
#
# Environment (defaults in brackets):
#   BASE_PORT    first local port      [8081]
#   REMOTE_PORT  llama-server port     [8080]
HOSTS="$*"
[ -z "$HOSTS" ] && HOSTS="$LAB_HOSTS"
[ -z "$HOSTS" ] && { echo "usage: $0 host[:port]... (or set LAB_HOSTS)" >&2; exit 2; }
next="${BASE_PORT:-8081}"
rport="${REMOTE_PORT:-8080}"

trap 'kill 0' INT TERM
for spec in $HOSTS; do
  h="${spec%%:*}"
  port="${spec#*:}"
  [ "$port" = "$spec" ] && { port="$next"; next=$((next + 1)); }
  echo "tunnel 127.0.0.1:$port -> $h:127.0.0.1:$rport"
  ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N -L "$port:127.0.0.1:$rport" "$h" &
done
wait

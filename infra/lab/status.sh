#!/bin/sh
# Read-only status of lab machines, run from your own computer over SSH.
# A machine is BUSY if ANY other user (UID_MIN <= uid < UID_MAX) has a process on it.
# GPU memory is shown for information only; it does not decide FREE/BUSY.
#
# Usage: sh infra/lab/status.sh [host ...]     (default: $LAB_HOSTS)
#   e.g. LAB_HOSTS="host1 host2 host3" sh infra/lab/status.sh
HOSTS="$*"
[ -z "$HOSTS" ] && HOSTS="$LAB_HOSTS"
[ -z "$HOSTS" ] && { echo "usage: $0 host... (or set LAB_HOSTS)" >&2; exit 2; }
UID_MIN="${UID_MIN:-10000}"
UID_MAX="${UID_MAX:-60000}"

REMOTE='
me=$(id -un)
others=$(ps -eo user:32,uid --no-headers | awk -v me="$me" -v lo='"$UID_MIN"' -v hi='"$UID_MAX"' "\$2>=lo && \$2<hi && \$1!=me {print \$1}" | sort -u | tr "\n" " ")
mine=$(ps -u "$me" --no-headers | wc -l)
gpu=$(nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheader,nounits 2>&1 | head -1)
case "$gpu" in *mismatch*|*failed*|*NVML*) gpu="NVML-ERROR";; esac
echo "others=[${others}] mine=${mine} gpu_free_total_MiB=${gpu}"
'

printf "%-12s %-6s %s\n" HOST STATE DETAILS
for h in $HOSTS; do
  out=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$h" "$REMOTE" 2>&1 | tail -1)
  case "$out" in
    others=\[\]*) state=FREE ;;
    others=*)     state=BUSY ;;
    *)            state=DOWN ;;
  esac
  printf "%-12s %-6s %s\n" "$h" "$state" "$out"
done

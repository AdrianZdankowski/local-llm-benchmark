#!/bin/sh
# Run on a lab machine before any compute. Exits non-zero if the machine must not be used:
#   1. another user has a process on it (checked with ps over the regular-user uid range), or
#   2. the current time is outside the compute window.
#
# Environment (defaults in brackets):
#   START_HOUR  window start, 0-23   [19]
#   END_HOUR    window end, 0-23     [7]   (START_HOUR > END_HOUR means the window spans midnight)
#   UID_MIN     lowest uid of regular users      [10000]
#   UID_MAX     uid limit (exclusive)            [60000]
START_HOUR="${START_HOUR:-19}"
END_HOUR="${END_HOUR:-7}"
UID_MIN="${UID_MIN:-10000}"
UID_MAX="${UID_MAX:-60000}"

me=$(id -un)
others=$(ps -eo user:32,uid --no-headers \
  | awk -v me="$me" -v lo="$UID_MIN" -v hi="$UID_MAX" '$2>=lo && $2<hi && $1!=me {print $1}' \
  | sort -u | tr '\n' ' ')
if [ -n "$others" ]; then
  echo "GUARD: $(hostname) busy (other users: $others) - refusing to run" >&2
  exit 1
fi

hour=$(date +%H | sed 's/^0//')
inside=
if [ "$START_HOUR" -gt "$END_HOUR" ]; then
  # window spans midnight, e.g. 19-7
  [ "$hour" -ge "$START_HOUR" ] || [ "$hour" -lt "$END_HOUR" ] && inside=1
else
  [ "$hour" -ge "$START_HOUR" ] && [ "$hour" -lt "$END_HOUR" ] && inside=1
fi
if [ -z "$inside" ]; then
  echo "GUARD: outside compute window ($START_HOUR:00-$END_HOUR:00), now $(date +%H:%M) - refusing to run" >&2
  exit 1
fi
exit 0

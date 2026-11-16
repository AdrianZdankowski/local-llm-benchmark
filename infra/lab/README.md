# Running on shared lab machines

Helper scripts for running the model under test on shared Linux machines with one NVIDIA GPU each and driving the benchmarks from your own computer over SSH.

Nothing here contains host names or user names. Pass hosts as arguments or set `LAB_HOSTS`, for example `export LAB_HOSTS="host1 host2 host3 host4"`. SSH must work non-interactively (key-based login, `BatchMode=yes`).

## Rules

Shared machines need consideration for other users:

1. **A machine is busy if anyone else is on it.** If any other user has *any* process on the machine (a login shell, an idle session, a background job), do not use it. Check with `ps` over the regular-user uid range, not with `nvidia-smi`: an empty GPU says nothing about whether someone is logged in. `guard.sh` and `status.sh` implement this check.
2. **Respect the allowed time window.** `guard.sh` refuses to start outside `START_HOUR`–`END_HOUR` (default 19–7); set them to whatever your site allows.
3. **Use few machines** and follow your site's limits.
4. **Clean up after yourself.** When you finish, stop the server and every other process you started (`stop_all.sh`), then log out. Leave no detached sessions.
5. **No autostart.** Do not install cron jobs or anything else that starts work while you are away unless an administrator allowed it. Start every session by hand.
6. **Sessions.** Use `screen` (or `tmux`) for anything that must survive logout.

## Scripts

| Script | Runs on | Purpose |
|---|---|---|
| `status.sh [host...]` | your computer | Read-only: FREE / BUSY / DOWN per machine, your process count, free GPU memory |
| `guard.sh` | lab machine | Exits non-zero if another user is present or the time is outside the window; every compute script runs it first |
| `start_server.sh <host> <model-key> [port]` | your computer | Stops your previous server on that machine, runs the guard, starts `infra/llama_server/serve.sh` in a detached `screen` session |
| `tunnel.sh host[:port]...` | your computer | SSH port forwards from local ports to `127.0.0.1:8080` on each machine |
| `stop_all.sh [host...]` | your computer | Stops the server sessions and reports anything of yours still running |

Environment variables:

| Variable | Default | Used by |
|---|---|---|
| `LAB_HOSTS` | none | `status.sh`, `stop_all.sh`, `tunnel.sh` when no hosts are given |
| `START_HOUR`, `END_HOUR` | `19`, `7` | `guard.sh`, `start_server.sh` |
| `UID_MIN`, `UID_MAX` | `10000`, `60000` | `guard.sh`, `status.sh`: uid range of regular user accounts; check `/etc/login.defs` on your machines |
| `LAB_REPO` | `local-llm-benchmark` | `start_server.sh`: repository path on the lab machine, relative to the remote home |
| `SCREEN_NAME` | `srv` | `start_server.sh`, `stop_all.sh` |
| `BASE_PORT`, `REMOTE_PORT` | `8081`, `8080` | `tunnel.sh` |

## Workflow

One-time setup, on one free machine:

```bash
ssh <host>
git clone <repo-url> local-llm-benchmark && cd local-llm-benchmark
screen -S setup
export GUARD=infra/lab/guard.sh
sh infra/llama_server/setup_llamacpp.sh          # CUDA_ARCH=89 for RTX 40xx
sh infra/llama_server/download_models.sh all
exit                                             # leave screen, then log out
```

Each session, from your own computer:

```bash
export LAB_HOSTS="host1 host2 host3 host4"       # example list
sh infra/lab/status.sh                           # pick FREE machines only
sh infra/lab/start_server.sh host1 qwen35-9b
sh infra/lab/start_server.sh host2 gemma4-12b
sh infra/lab/tunnel.sh host1:8083 host2:8084 &   # keep running while benchmarking
curl -s http://127.0.0.1:8083/health             # wait for {"status":"ok"}

export BENCH_BASE_URL=http://127.0.0.1:8083/v1 BENCH_MODEL=qwen35-9b
export JUDGE_BASE_URL=<judge endpoint>/v1 JUDGE_MODEL=<judge model>
# ... run a harness from harness/<benchmark>/README.md ...

sh infra/lab/stop_all.sh host1 host2             # always, also after a failure
kill %1                                          # close the tunnels
```

If another user logs in while you are running, stop at once (`stop_all.sh`). The guard only checks at start time; it does not watch the machine afterwards. Long harness runs therefore belong on your own computer (talking to the tunnel), not on the lab machine, so that stopping the server is all it takes to leave.

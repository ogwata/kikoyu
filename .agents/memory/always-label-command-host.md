---
name: always-label-command-host
description: "When giving shell commands in this multi-host setup, always label which machine runs them"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ce5b07da-85f2-4dab-96ed-2349396294c2
---

When presenting any shell command for the kikoyu demo/work, always explicitly state which host it runs on — 🖥 local Mac vs 🟢 the remote DGX Spark (reached via `ssh spark` over Tailscale). Never present a command without naming its side.

**Why:** The user repeatedly pasted Spark-side commands (`docker run --gpus all`, `cp ~/whisperx-work/.env …`, `cd ~/kikoyu-work`) into the local Mac shell, where those paths/daemon don't exist — wasting time and causing confusing errors. The Mac has no NVIDIA GPU and no `~/kikoyu-work` / `~/whisperx-work`; those live only on the Spark.

**How to apply:** Prefix every command block with the host (e.g. "🟢 Spark (SSH先):" or "🖥 Mac ローカル:"). For Spark-side steps, prefer running them via `ssh spark '…'` myself, or show the explicit `ssh spark` shell entry first. Demo runbook lives in [[(docs/demo-live.md)]]; Spark connection details: `Host spark` in ~/.ssh/config.

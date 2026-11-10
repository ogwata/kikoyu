---
name: verify-compatibility-blocker-claims
description: "How to write/vet \"X is incompatible with Y\" claims — distinguish missing package/wheel from actual library/hardware incompatibility, require a repro command or source link"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 476d199f-16d2-4670-a22d-98050cebb678
---

When writing or reviewing a "known limitation" / "X doesn't work with Y" note (especially
CUDA / driver / container-level compatibility claims), require two things before treating it
as fact:

1. A clear distinction between "no prebuilt package/wheel is distributed for this platform"
   and "the underlying library/hardware combination doesn't actually work". These are
   different claims and get conflated constantly.
2. A runnable reproduction command or a link to the primary source, inline with the claim —
   not just a bare conclusion.

**Why:** kikoyu.ipynb stated "ctranslate2 4.4.0 is incompatible with CUDA13/Blackwell" and
disabled the faster-whisper path because of it. The actual source
([speaches-ai/speaches#620](https://github.com/speaches-ai/speaches/issues/620)) only reports
that no PyPI linux/arm64+CUDA wheel exists — the `mekopa/whisperx-blackwell` container's
*bundled* ctranslate2 build worked fine the whole time (verified 2026-07-13 with a one-line
`docker run --rm --gpus all ...` repro). The false claim was copy-pasted verbatim into a forked
notebook (kikoyu-ORG's `shioiri_minutes_dgx.ipynb`) and went unquestioned for ~2 months, because
once a working workaround (`transformers.pipeline`) existed, nobody had a reason to re-test the
"broken" path. The notebook's own troubleshooting table already described the actual failure
mode ("PyPI aarch64 wheel getting mixed in, check `pip show ctranslate2`") right next to the
wrong root-cause conclusion — the symptom was seen but mis-diagnosed.

**How to apply:**
- When reviewing or writing compatibility/blocker notes in any repo, check whether the note
  names a specific artifact (wheel/package) vs. the underlying tech, and whether it can be
  quickly re-verified. Treat bare "doesn't work" claims with no repro/source as suspect,
  especially old ones that predate an established workaround.
- Watch for `pip install` inside vendor-customized containers (e.g. `mekopa/whisperx-blackwell`,
  which ships specially-built/patched dependencies) silently overwriting a working bundled
  package with a broken PyPI version — this is the likely actual mechanism behind the original
  misdiagnosis here.
- When forking a repo/notebook that carries "known limitation" notes, re-verify at least the
  infra/driver/container-level ones once rather than inheriting them as received wisdom.
- Prefer adding a "last verified: DATE" marker to blocker notes so staleness is visible, and
  periodic dependency-check tasks (e.g. `ai-repo-dep-check`) have something concrete to flag.

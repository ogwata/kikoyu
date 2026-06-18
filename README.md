**English** | [日本語](README.ja.md)

---

# kikoyu

A Jupyter notebook for **transcribing audio and separating speakers** locally — for example, meeting recordings. It transcribes with `whisper-large-v3` and runs speaker diarization with `pyannote`, writing out who said what with per-speaker labels.

The name `kikoyu` (聞こゆ, classical Japanese for "to be heard / to reach the ear") reflects what it does: pull words and speakers out of a recording.

> ## ⚠️ Prerequisite: this notebook targets DGX Spark / Blackwell only
>
> It was built and verified on **DGX Spark (GB10 / Blackwell sm_121 / aarch64 / CUDA 13)**.
> To make this unusual sm_121 + CUDA 13 combination work, it relies on a PyTorch monkey-patch and
> the [Mekopa/whisperx-blackwell](https://github.com/Mekopa/whisperx-blackwell) container (capability spoofing).
> **It will not run as-is on a typical x86 + CUDA 12 setup** — on that hardware, plain
> [WhisperX](https://github.com/m-bain/whisperX) works directly and you don't need this.
> What this repo offers is a working, pitfall-patched configuration for running WhisperX + pyannote on a DGX Spark.

## What it does

- Japanese transcription with whisper-large-v3 (`transformers.pipeline` + bf16)
- Speaker diarization with pyannote (labels each segment `SPEAKER_00`, `SPEAKER_01`, …)
- Optional word-level timestamp alignment
- A "resume" path: save the transcript as JSON and redo only the diarization later

Outputs (under `out/`):

| File | Contents |
| --- | --- |
| `{stem}_segments.json` | Raw segments (input to later stages) |
| `{stem}_transcript.txt` | Plain text in `[seconds] text` form |
| `{stem}_segments_speaker.json` | Segments with speaker labels |
| `{stem}_transcript_speaker.txt` | `[HH:MM:SS] SPEAKER_XX: text` form |

## Requirements

- A DGX Spark (GB10 / Blackwell sm_121 / aarch64 / CUDA 13) with Docker
- The `mekopa/whisperx-blackwell:latest` container
- A HuggingFace account and access token
  - `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` are **gated models**.
    You must accept their terms and supply your own token.

## Quick start

```bash
# On the DGX Spark
mkdir -p ~/kikoyu-work && cd ~/kikoyu-work
# Place this repository and your audio file here

cp .env.example .env        # put your HF token in .env, then: chmod 600 .env
docker pull mekopa/whisperx-blackwell:latest
# docker run ... (see docs/setup.md)
```

See **[docs/setup.md](docs/setup.md)** for full setup and run order. (Note: `docs/setup.md` is currently written in Japanese.)

## Repository layout

```
kikoyu/
├── kikoyu.ipynb                      # the notebook
├── prompts/
│   └── initial_prompt.example.txt    # generic sample proper-noun dictionary
├── docs/
│   ├── setup.md                      # setup & run steps (Japanese)
│   └── demo.md                       # live-demo guide (Japanese)
├── .env.example                      # HF token template
├── .gitignore
├── LICENSE
├── README.md                         # this file (English)
└── README.ja.md                      # Japanese
```

## Privacy and data handling

This repository publishes **only the tooling** (the notebook and instructions); nothing containing personal
information is committed. `.gitignore` excludes:

- `.env` (your HuggingFace token)
- `*.local.txt` (the proper-noun dictionary `prompts/initial_prompt.local.txt`, which may contain real names)
- Audio files (`*.m4a`, etc.)
- Transcription and diarization outputs (`out/`, `*_transcript*.txt`, `*_segments*.json`)

The proper-noun dictionary lives in `prompts/initial_prompt.local.txt` (untracked). The notebook reads `local`
if present, otherwise falls back to the generic sample `initial_prompt.example.txt` with a warning.
**Recordings, transcripts, and real names never enter this repository.**

## License and dependencies

- The code in this repository is under the **MIT License** ([LICENSE](LICENSE)).
- This notebook was originally written for Google Colab, then ported to DGX Spark with diarization added.
  There is no third-party license to inherit.
- External components it depends on (follow each one's license / terms):
  - Runtime: [Mekopa/whisperx-blackwell](https://github.com/Mekopa/whisperx-blackwell) (community image)
  - Transcription: OpenAI Whisper (`whisper-large-v3`) / [WhisperX](https://github.com/m-bain/whisperX)
  - Diarization: [pyannote](https://github.com/pyannote/pyannote-audio) (models are gated; terms acceptance required)

## References

- WhisperX issue #1326 (running on DGX Spark): <https://github.com/m-bain/whisperX/issues/1326>
- NVIDIA forum (sm_121 support): <https://forums.developer.nvidia.com/t/dgx-spark-sm121-software-support-is-severely-lacking-official-roadmap-needed/357663>

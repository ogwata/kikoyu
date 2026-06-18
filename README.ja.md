[English](README.md) | **日本語**

---

# kikoyu

会議などの音声ファイルを、ローカルで **文字起こし＋話者分離** するための Jupyter ノートブックです。
文字起こしに `whisper-large-v3`、話者分離に `pyannote` を使い、誰が何を言ったかをラベル付きで書き出します。

名前の `kikoyu`（聞こゆ）は「声が耳に届く／聞こえる」の意。録音から言葉と話者を取り出す、という機能から取りました。

> ## ⚠️ 前提: このノートブックは DGX Spark / Blackwell 専用です
>
> 動作確認した環境は **DGX Spark (GB10 / Blackwell sm_121 / aarch64 / CUDA 13)** です。
> sm_121 + CUDA 13 という特殊な組み合わせを動かすために、PyTorch への monkey-patch と
> [Mekopa/whisperx-blackwell](https://github.com/Mekopa/whisperx-blackwell) コンテナ（capability spoof）を使っています。
> **一般的な x86 + CUDA 12 環境ではそのままでは動きません。** その環境なら素の
> [WhisperX](https://github.com/m-bain/whisperX) がそのまま使えるので、このリポジトリは不要です。
> ここで価値があるのは「DGX Spark で WhisperX + pyannote を実際に動かすための、はまりどころを潰した構成」です。

## できること

- whisper-large-v3 による日本語の文字起こし（`transformers.pipeline` + bf16）
- pyannote による話者分離（`SPEAKER_00`, `SPEAKER_01`, … のラベル付与）
- 単語単位タイムスタンプのアラインメント（任意）
- 文字起こしを JSON 保存しておき、話者分離だけ後からやり直す「再開ルート」

出力（`out/` 配下）:

| ファイル | 内容 |
| --- | --- |
| `{stem}_segments.json` | 生の segments（後段の入力） |
| `{stem}_transcript.txt` | `[秒] テキスト` 形式のプレーンテキスト |
| `{stem}_segments_speaker.json` | 話者ラベル付き segments |
| `{stem}_transcript_speaker.txt` | `[HH:MM:SS] SPEAKER_XX: テキスト` 形式 |

## 必要なもの

- DGX Spark（GB10 / Blackwell sm_121 / aarch64 / CUDA 13）と Docker
- `mekopa/whisperx-blackwell:latest` コンテナ
- HuggingFace アカウントとアクセストークン
  - `pyannote/speaker-diarization-3.1` と `pyannote/segmentation-3.0` は **gated モデル**です。
    利用規約に同意し、自分のトークンを用意する必要があります。

## クイックスタート

```bash
# DGX Spark 上で
mkdir -p ~/kikoyu-work && cd ~/kikoyu-work
# このリポジトリと音声ファイルをここに置く

cp .env.example .env        # .env に自分の HF トークンを書く → chmod 600 .env
docker pull mekopa/whisperx-blackwell:latest
# docker run ... （詳細は docs/setup.md）
```

セットアップと実行順の詳細は **[docs/setup.md](docs/setup.md)** を参照してください。

## ディレクトリ構成

```
kikoyu/
├── kikoyu.ipynb                      # 本体ノートブック
├── prompts/
│   └── initial_prompt.example.txt    # 固有名詞辞書の汎用サンプル
├── docs/
│   ├── setup.md                      # セットアップ・実行手順
│   └── demo.md                       # ライブデモ手順
├── .env.example                      # HF トークンのテンプレ
├── .gitignore
├── LICENSE
├── README.md                         # 英語
└── README.ja.md                      # このファイル（日本語）
```

## プライバシーとデータの扱い

このリポジトリは**ツール（ノートブックと手順）だけ**を公開し、個人情報を含むものは一切コミットしません。
`.gitignore` で次を除外しています:

- `.env`（HuggingFace トークン）
- `*.local.txt`（実名などを含む固有名詞辞書 `prompts/initial_prompt.local.txt`）
- 音声ファイル（`*.m4a` 等）
- 文字起こし・話者分離の出力（`out/`, `*_transcript*.txt`, `*_segments*.json`）

固有名詞辞書は `prompts/initial_prompt.local.txt`（git 管理外）に置く設計です。
ノートブックは local があればそれを、無ければ汎用サンプル `initial_prompt.example.txt` を読み、
警告を出して続行します。**録音・文字起こし・実名は、このリポジトリには決して入りません。**

## ライセンスと依存

- 本リポジトリのコードは **MIT License**（[LICENSE](LICENSE)）です。
- このノートブックは元々 Google Colab 用に書き起こしたものを DGX Spark 向けに移植し、話者分離を加えたものです。
  継承すべき第三者ライセンスはありません。
- 依存する外部成果物（それぞれのライセンス・利用規約に従ってください）:
  - 実行基盤: [Mekopa/whisperx-blackwell](https://github.com/Mekopa/whisperx-blackwell)（コミュニティイメージ）
  - 文字起こし: OpenAI Whisper（`whisper-large-v3`） / [WhisperX](https://github.com/m-bain/whisperX)
  - 話者分離: [pyannote](https://github.com/pyannote/pyannote-audio)（モデルは gated・利用規約への同意が必要）

## 参考

- WhisperX issue #1326（DGX Spark で動かす）: <https://github.com/m-bain/whisperX/issues/1326>
- NVIDIA forum（sm_121 サポート）: <https://forums.developer.nvidia.com/t/dgx-spark-sm121-software-support-is-severely-lacking-official-roadmap-needed/357663>

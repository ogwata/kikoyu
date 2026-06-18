# セットアップ手順 (DGX Spark / Blackwell)

このノートブックは **DGX Spark (GB10 / Blackwell sm_121 / aarch64 / CUDA 13)** 専用です。
sm_121 + CUDA 13 という特殊な組み合わせを動かすための構成で、一般的な x86 + CUDA 12 環境では
そのままでは動きません (その環境なら素の WhisperX がそのまま使えます)。

## 1. 事前準備 (初回のみ)

1. DGX Spark に SSH 接続できる状態にする。
2. 作業ディレクトリを作り、このリポジトリと音声ファイルを置く:
   ```bash
   mkdir -p ~/kikoyu-work && cd ~/kikoyu-work
   # kikoyu.ipynb / prompts/ などを配置し、音声ファイル (*.m4a 等) もここに置く
   ```
3. コンテナイメージを取得:
   ```bash
   docker pull mekopa/whisperx-blackwell:latest
   ```
4. pyannote 話者分離用の HuggingFace トークンを `.env` に置く:
   ```bash
   cp .env.example .env
   # .env を開いて hf_xxx... を自分のトークンに置き換える
   chmod 600 .env
   ```
   - HuggingFace で `pyannote/speaker-diarization-3.1` と `pyannote/segmentation-3.0` の
     利用規約に同意し、アクセストークンを発行しておくこと。
   - **値はクオートで囲まないこと** (`--env-file` はクオートも値の一部として扱う)。
5. 固有名詞辞書を用意する (任意・推奨):
   ```bash
   cp prompts/initial_prompt.example.txt prompts/initial_prompt.local.txt
   # local.txt に参加者名・地名・団体名・専門用語を「、」区切りで列挙
   ```
   `*.local.txt` は `.gitignore` 済みで git には乗りません。

## 2. コンテナ起動

```bash
cd ~/kikoyu-work
docker run -it --rm \
  --gpus all --ipc=host --ulimit memlock=-1 \
  -p 8888:8888 \
  -v "$PWD:/work" -w /work \
  --env-file .env \
  --entrypoint bash \
  mekopa/whisperx-blackwell:latest \
  -lc "pip install -q jupyterlab ipywidgets && \
       jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root \
                   --ServerApp.token='' --ServerApp.password='' \
                   --ServerApp.disable_check_xsrf=True \
                   --ServerApp.root_dir=/work"
```

接続が切れやすい環境では、先に `tmux new -s kikoyu` を実行してから `docker run` すると
セッションを保護できます (`tmux attach -t kikoyu` で復帰)。

## 3. 手元のマシンから Jupyter を開く

別ターミナルで SSH ポートフォワード:

```bash
ssh -L 8888:localhost:8888 <あなたの DGX Spark への SSH 先>
```

ブラウザで `http://localhost:8888/lab` を開く。VS Code から接続する場合は Jupyter 拡張の
"Connect to existing Jupyter server" に `http://localhost:8888` を指定する
(このとき `--ServerApp.disable_check_xsrf=True` が必須)。

## 4. 実行順

1. **音声ファイルの指定**: `kikoyu.ipynb` 冒頭の `AUDIO_FILE` に処理したいファイル名を書く
   (空のままなら `/work` 直下を自動検出。候補が 1 件でなければ停止する)。
2. ノートブックを上から順に実行。**必ず Cell 1 (PyTorch パッチ) から**。
3. 完走すると `out/` に下記が出力される:
   - `{stem}_segments.json` / `{stem}_transcript.txt` (文字起こし)
   - `{stem}_segments_speaker.json` / `{stem}_transcript_speaker.txt` (話者分離後)

文字起こし済みで話者分離だけやり直す場合は、ノートブック内 `## 6. 保存済み segments から再開する場合`
の手順に従う。トラブル時はノートブック末尾の `## 9. トラブルシュート` を参照。

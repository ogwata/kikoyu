# 完全ライブ・デモ手順書 (生録音＋遠隔 Spark)

会議室 (数名) ＋ Google Meet (数名) のハイブリッド会議の場で、**その場で60〜90秒録音した音声を、
遠隔の DGX Spark で即座に文字起こし＋話者分離して見せる**ための手順書です。

既存の [demo.md](demo.md) の「短尺サンプル＋キャッシュ温め」の方針を、
**完全ライブ実行・生録音・遠隔 Spark (SSH)** 向けに具体化したものです。

---

## 0. 設計の核 (長尺問題への工夫)

### 実測値 (2026-06-23, DGX Spark GB10 / 3.13分の実音声で計測)

| 計測 | 時間 | RTF |
| --- | --- | --- |
| モデルロード (HFキャッシュ温) | 2.9 秒 | — |
| 文字起こし **初回 COLD** (CUDAコンパイル込み) | 440 秒 | 2.34x |
| 文字起こし **2回目 WARM (本番相当)** | 126 秒 | **0.67x** |
| 話者分離 (pyannote) | 122 秒 | 約 0.65x |

→ **遅さの正体は「初回1回限りの CUDA コンパイル (約+5分)」**。カーネルを温めれば文字起こしは
RTF 0.67 (実時間より速い)。**90秒の録音なら本番のライブ処理は 文字起こし約60秒＋話者分離約60秒 ≒ 2分**。

> 注: kikoyu は `transformers.pipeline` 版 whisper-large-v3 + `temperature` フォールバックを使う。
> 雑音・かぶりの多い実音声ではチャンク単位で再デコードが走り RTF が膨らむことがある (クリーンな
> 音声ほど速い)。旧記載の「RTF≒1.0」は実運用 (faster-whisper) 経路の数字。

### 本番を成立させる4点

1. **GPUを空ける (必須)** — 同じ Spark で ollama(swallow:70b≈45GB) 等が動いていると GPU を奪い合う。
   デモ前に `ollama stop swallow:70b` (または `sudo systemctl stop ollama`) でアンロードし、デモ中は触らない。
2. **会議そのものから 60〜90 秒だけ生録音** — 短尺が不自然にならず、同意・無害性も自動的に満たす
3. **カーネルをウォームに保つ (必須)** — 本番前のリハで一度完走させ (この時に約5分のコンパイルを消化)、
   **カーネルを生かしたまま**にする。本番は音声を差し替えて再実行 → 待ちが RTF 0.67 + 話者分離だけに縮む
4. **待ち時間 = 解説タイム** — 処理中に sm_121 パッチ / whisper-large-v3 / pyannote の話をして待ちを見せ場に
   (単一ファイル自動検出: clone 直下に音声1件なら `AUDIO_FILE` 空でも自動検出。複数あるなら `AUDIO_FILE` で明示)

---

## 1. 事前準備 (前日〜開始30分前)

- Spark で `mekopa/whisperx-blackwell` コンテナを起動し、Jupyter を起動。`.env` に HF トークン
  (`docs/setup.md` 参照)
- **モデルキャッシュ温め**: ダミー短尺を一度完走させ、whisper-large-v3 ＋ pyannote (合計数 GB) を
  ダウンロード済みにしておく (ライブでダウンロード待ちを見せない)
- 会議室 PC から **SSH ポートフォワード**:
  ```bash
  ssh -L 8888:localhost:8888 <user>@<spark>
  ```
  会議室 PC のブラウザで `http://localhost:8888` を開く → **このブラウザ画面を Google Meet で画面共有**
  (会議室と Meet の双方に見せる)
- **録音テスト**: QuickTime Player で部屋マイクから10秒録り、`scp` 経路まで一度通す (本番経路の確認)
- **エコーキャンセル確認** (重要): 録音 PC が同時に Meet に入っていると、Meet のエコーキャンセルが
  スピーカー越しの遠隔音声を消すことがある。リハ録音で**遠隔の声が入っているか**を必ず確認。
  不安なら Meet 用 PC と録音用 PC (またはマイク) を分ける
- **リハ**: 本番直前にノートブックを Cell 1 から「モデルロードまで」実行 → **カーネルを生かしたまま待機**

---

## 2. 本番の流れ

### 2-1. 録音 (QuickTime Player / 部屋ごと1マイク)

会議室スピーカーから出る Meet 側の声と室内の人の声を、**1本のマイクでまとめて拾う**方式。
仮想オーディオは不要。

1. **QuickTime Player を起動** (Spotlight で「QuickTime」)
2. メニュー **ファイル → 新規オーディオ収録**
3. 赤い●ボタンの**右の「∨」**をクリック → **マイク**: 使う入力を選択 / **品質**: 「高音質」
4. **赤い●で録音開始**。参加者2〜3人に当たり障りない話題で **60〜90 秒、交互に (少しだけ重ねて) 話してもらう**
5. もう一度●で停止 → **ファイル → 保存** (⌘S) → 名前 `meeting_demo` (拡張子は自動で `.m4a`)

### 2-2. 転送・実行・提示

1. `scp meeting_demo.m4a <user>@<spark>:~/kikoyu/`  (古い音声は事前に退避済み)
2. Jupyter (画面共有中) で**推論セルだけ再実行** → 60〜90 秒の処理
3. 処理中に §3 の解説をする
4. 完走 → `out/meeting_demo_transcript_speaker.txt` を開く:
   ```
   [00:00:03] SPEAKER_00: ...
   [00:00:11] SPEAKER_01: ...
   [00:00:18] SPEAKER_02: ...
   ```
   「誰が・いつ・何を」がラベルで割れているのを指さし、「3人で話したらラベルも3つに割れました」と説明

---

## 3. 待ち時間の解説台本 (約60〜90秒尺)

- 「いま走っているのは whisper-large-v3 の文字起こし。RTF ≒ 1.0 なので録った尺とほぼ同じ時間で進みます」
- 「この Spark は Blackwell sm_121 / CUDA 13 という珍しい構成。普通は動かないので PyTorch を
  monkey-patch して能力を詐称させています」
- 「文字起こしが終わると pyannote が**声質で**話者を分け、各区間に `SPEAKER_00 / 01 / ...` を付けます」

---

## 4. リスクと対策

- **録音品質** (Meet がスピーカー越し・残響) → 事前テストで分離されるか確認。交互発話・近接マイク推奨
- **SSH / VPN 断** → 開始前に疎通確認、テザリング等の予備回線を用意
- **話者の過分割 / 併合** → 期待話者数を把握し「だいたい合っていれば OK」と前置きする
- **最低限の保険** → 完全ライブ (保険なし) の方針だが、リハで作った出力 `txt` を1枚手元に残しておくと、
  万一録音失敗でも「結果の読み解き」に切り替えられる

---

## 5. 後片付け・プライバシー

- 録音と `out/` の出力は `.gitignore` 済み。**コミットしない**
- デモ後はサンプルを消すなら clone フォルダごと削除してよい (実運用とは別物)
- 固有名詞辞書 `prompts/initial_prompt.local.txt` はデモでは作らず、同梱の
  `initial_prompt.example.txt` のままにする

---

## 6. 運用メモ / トラブル対処 (2026-06-23 実機セットアップで判明)

コマンドは実行する側を明記する: 🖥 = ローカル Mac / 🟢 = リモート DGX Spark (`ssh spark`)。

### 6-1. 接続 (Tailscale 経由)

- `~/.ssh/config` に `Host spark` 登録済み。**自宅/外出を問わず `ssh spark` で到達**
  (LAN 内 `192.168.1.154` / 外出時 Tailscale `100.113.56.7` を自動で使い分け)。
- NVIDIA Sync は**不要** (要件は SSH 到達性のみ)。別ネットワークからは Tailscale 等のトンネルが前提。

### 6-2. 本番セットアップの実体 (デモ用に構築済み)

実運用 `~/whisperx-work` には触れず、**別フォルダ `~/kikoyu-work`** で回す。

- 🟢 clone: `git clone https://github.com/ogwata/kikoyu.git ~/kikoyu-work`
- 🟢 `.env`: `cp ~/whisperx-work/.env ~/kikoyu-work/.env && chmod 600 ~/kikoyu-work/.env`
  (HF トークンのキーは **`HF_whisperx`**。`HF_TOKEN` ではない)
- 🟢 起動ラッパー `~/kikoyu-work/_demo_start.sh` を `tmux` で起動。要点は **HF キャッシュをマウント**する点
  (setup.md の素の `docker run` はキャッシュ未マウントで毎回再DLになるため):

  ```bash
  docker run --rm --gpus all --ipc=host --ulimit memlock=-1 \
    -p 8888:8888 \
    -v "$PWD":/work -w /work \
    -v "$HOME/.cache/huggingface":/root/.cache/huggingface \   # ← これが肝 (whisper/pyannote 永続)
    --env-file .env --entrypoint bash \
    mekopa/whisperx-blackwell:latest \
    -lc "pip install -q jupyterlab ipywidgets && jupyter lab --ip=0.0.0.0 --port=8888 \
         --no-browser --allow-root --ServerApp.token='' --ServerApp.password='' \
         --ServerApp.disable_check_xsrf=True --ServerApp.root_dir=/work"
  ```
- 🟢 tmux: `tmux new -d -s kikoyu '~/kikoyu-work/_demo_start.sh 2>&1 | tee ~/kikoyu-work/_demo_jupyter.log'`
  (SSH が切れてもコンテナは生存。確認は `tmux attach -t kikoyu`、離脱は `Ctrl-b` → `d`)

### 6-3. GPU を空ける (本番前に必須)

同じ Spark で **ollama (`swallow:70b` ≈ 45GB)** や別プロジェクトが GPU を占有していると遅くなる。

- 🟢 ロード中モデルの確認: `ollama ps`
- 🟢 アンロード (sudo 不要): `ollama stop swallow:70b`
- 🟢 サービスごと止めるなら: `sudo systemctl stop ollama` (要パスワード)
- 🟢 占有確認: `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader`
- ⚠️ **GB10 は `nvidia-smi` のテレメトリが不完全**。GPU使用率が `0 %`、メモリが `[N/A]` と出ても idle とは限らない。
  稼働確認は「kernel が `State: R`」「`docker stats` の CPU%」「SM クロックのブースト」で見る。

### 6-4. SSH トンネルが切れる (Server Connection Error)

ブラウザの "Server Connection Error" / 画面下 "Connecting" は、**Jupyter 本体ではなく 🖥↔🟢 トンネルの一時切断**
(Tailscale の経路貼り替え・会場ネットのゆらぎが誘因)。

- **重要**: カーネルは 🟢 Spark 側 (tmux+コンテナ内) で動くので、**切れても実行中セルは止まらず `out/` に結果は残る**。
  ブラウザは自動再接続。慌てない。
- 🖥 **自動再接続トンネル** (素の `ssh -N -L ...` の代わりにこれを常用):

  ```bash
  while true; do
    ssh -N -L 8888:localhost:8888 \
      -o ServerAliveInterval=10 -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes -o ConnectTimeout=10 spark
    echo "$(date +%H:%M:%S) トンネル切断 → 再接続..."; sleep 2
  done
  ```
- エラーダイアログは **Close**。本番前に "Do not show again" にチェックしておくと邪魔にならない。
- 予備にスマホのテザリングを用意 (§4 と同じ)。

### 6-5. その他

- コンテナの `(unhealthy)` 表示は Docker ヘルスチェックの判定ズレで、**サーバは正常** (8888 応答中)。無視可。
- ウォームアップ用のダミー音声は **🖥 macOS の `say` で合成**できる (マイク不要):
  `say -v Kyoko -o a.aiff "…"` / `say -v Grandpa -o b.aiff "…"` を 🟢 側 `ffmpeg -f concat` で1ファイルに連結。
  2話者でも話者分離はきれいに割れる (本番は生録音、これは温め・疎通用)。
- 速度の実測根拠は §0 の表を参照。**初回 COLD は CUDA コンパイルで約+5分**、温めた **2回目 WARM が RTF 0.67**。

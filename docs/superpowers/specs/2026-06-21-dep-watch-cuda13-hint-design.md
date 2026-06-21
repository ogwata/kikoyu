# dep-watch: CUDA 13 互換ヒント機能 設計

- 日付: 2026-06-21
- 対象: `.github/scripts/check_deps.py`, `.github/dep-watch.config.json`, `.github/workflows/dep-watch.yml`(変更なし見込み)
- 関連: Issue #1 (dep-watch 通知), ctranslate2 4.4.0→4.8.0 検知

## 背景と動機

dep-watch は watch-list 各パッケージの PyPI 最新安定版とバージョン番号を比較し、
更新があれば追跡 Issue で通知する。しかしバージョン番号の比較だけでは
「その新版が DGX Spark (aarch64 + CUDA 13 + sm_121) で動くか」は分からない。
特に ctranslate2 は CUDA 13 非互換が faster-whisper パス休止の原因であり、
番号が上がった = 復活可、ではない。

そこで、更新検知に加えて **CUDA 13 互換の "ヒント"（推定シグナル）** を表示したい。

## 根本制約（重要）

CUDA 13 で実際に動くかの**確定判定は、実機（DGX Spark aarch64+CUDA13+sm_121
コンテナ）で import → GPU 実行**しないと不可能。dep-watch が走る GitHub Actions
ランナーは x86_64 / GPU なしのため、ここで出せるのは **best-effort のヒントのみ**。
断定はしない。全表示に「要実機検証」の免責を付す。

## 決定事項（brainstorming の結論）

1. 判定の根拠: **自動ヒント（best-effort）**。手動注記フィールドは設けない。
2. 対象範囲: **config でオプトインしたパッケージのみ**。
3. 検出シグナル: **CHANGELOG grep と wheel 依存メタデータの両方**を組み合わせ。

## 設計

### 1. config スキーマ拡張（`.github/dep-watch.config.json`）

各パッケージに任意フィールドを追加（無ければ従来動作・後方互換）:

- `cuda13_watch` (bool, 既定 false): true のときだけ CUDA13 ヒントを計算・表示。
- `changelog_url` (string, 任意): CHANGELOG grep の取得先。無ければ CHANGELOG
  シグナルはスキップ（wheel 依存シグナルのみ）。

初期投入は **ctranslate2 のみ**:

```json
{ "name": "ctranslate2", "current": "4.4.0",
  "cuda13_watch": true,
  "changelog_url": "https://raw.githubusercontent.com/OpenNMT/CTranslate2/master/CHANGELOG.md",
  "note": "..." }
```

faster-whisper / torch などは将来必要になれば同フィールドを足す（YAGNI、今回は入れない）。

### 2. 検出ロジック（`check_deps.py` に追加）

すべて best-effort。ネットワーク取得は try/except で失敗を握り、ジョブを落とさない。

#### シグナルA: wheel 依存メタデータ

- PyPI JSON API `https://pypi.org/pypi/<pkg>/<version>/json`（最新安定版）を取得。
- `info.requires_dist` を走査し、`nvidia-*-cu13` / `nvidia-*-cu12` の有無を検出 →
  CUDA メジャー推定（"13" / "12" / None）。
- `urls`（配布ファイル一覧）のファイル名から **linux aarch64 wheel の有無**を検出
  （`*_aarch64.whl` / `*manylinux*aarch64*`）。CPU/GPU 別までは判定できない点に注意。
- 取得失敗時は wheel 依存=「取得失敗」。

純粋関数として切り出す:
- `cuda_major_from_requires(requires_dist: list[str]) -> str|None`
- `has_aarch64_wheel(urls: list[dict]) -> bool`

#### シグナルB: CHANGELOG grep

- `changelog_url` があれば取得。`re.compile(r"cuda[ \-]?13", re.I)` で検索。
- ヒットしたら件数と該当行（trim、最大数行）をスニペットとして保持。
- 取得失敗 / URL 無し時は CHANGELOG=「—」。

純粋関数として切り出す:
- `grep_cuda13(text: str) -> list[str]`（マッチ行のリストを返す。無ければ空）

#### 合成 → 推定ラベル

- シグナルA で cu13 検出 → 🟢 `cu13依存検出`
- それ以外で CHANGELOG ヒットあり → 🟡 `CHANGELOGに言及あり`
- どちらも無し → 🔴 `シグナルなし（CUDA13対応の根拠なし）`
- （A=cu12 検出時は推定列の補足に「cu12依存」と出す）

### 3. Issue 表示

既存の「更新あり」「参考/情報」表は変更しない。`cuda13_watch:true` の
パッケージが 1 件以上あるときのみ、**専用セクションを追加**:

```
## 🧪 CUDA 13 互換ヒント（自動推定・要実機検証）
> CHANGELOG / wheel 依存メタデータからの推定で、断定ではありません。
> 確定には DGX Spark (aarch64 + CUDA13 + sm_121) コンテナでの実行が必要です。

| ライブラリ | 最新 | wheel依存 | aarch64 wheel | CHANGELOG | 推定 |
|---|---|---|---|---|---|
| ctranslate2 | `4.8.0` | cu13なし | あり | 言及なし | 🔴 根拠なし |
```

スニペットがあれば表の下に引用ブロックで添える。

### 4. エラーハンドリング

- 新規 PyPI JSON 取得・CHANGELOG 取得はそれぞれ独立の try/except。
- 失敗は当該セルを「取得失敗」/「—」にし、他パッケージ・他シグナルの処理は継続。
- 既存 `latest_stable_from_pypi` の WARN print 方針を踏襲。

### 5. テスト

`.github/scripts/test_check_deps.py`（stdlib `unittest`、ネットワーク不要）を新設し、
壊れやすい純粋関数をフィクスチャ文字列で検証:

- `cuda_major_from_requires`: cu13 / cu12 / 無しの 3 ケース。
- `has_aarch64_wheel`: aarch64 wheel あり / なし。
- `grep_cuda13`: "CUDA 13" / "cuda-13" ヒット、非ヒット。

実行: `python -m unittest discover -s .github/scripts`。CI への組み込みは任意
（今回のワークフロー変更はしない方針 = 既存 dep-watch.yml は据え置き）。

## 非対象（YAGNI）

- 実機での実行検証（CI 不可）。
- 手動注記フィールド。
- ctranslate2 以外への初期オプトイン。
- dep-watch.yml の変更（テスト実行ステップ追加等）。

## 受け入れ基準

1. config に `cuda13_watch`/`changelog_url` が無い既存パッケージは従来通り動作。
2. ctranslate2 についてヒントセクションが生成され、現実の PyPI/CHANGELOG から
   推定ラベルが付く（現状は 🔴 根拠なし になる想定）。
3. ネットワーク失敗時もジョブが落ちず、当該セルが「取得失敗」になる。
4. オフライン単体テストが `python -m unittest` で通る。

#!/usr/bin/env python3
"""
dep-watch: ピン留めマニフェストの無いリポジトリ（ノートブック/コンテナ依存）向けに、
watch-list のライブラリの PyPI 最新安定版をチェックし、更新があれば追跡 Issue を
作成/更新して通知する。標準ライブラリのみで動作する（GitHub Actions の python で実行）。

- 設定: .github/dep-watch.config.json
- 通知: ラベル "dep-watch" の Issue を 1 件だけ維持し、毎回本文を更新する。
"""
import json
import os
import re
import glob
import urllib.request
import urllib.error

ROOT = os.getcwd()
CONFIG_PATH = os.path.join(ROOT, ".github", "dep-watch.config.json")
LABEL = "dep-watch"
ISSUE_TITLE = "📦 依存ライブラリの更新チェック (dep-watch)"
UA = {"User-Agent": "dep-watch-action"}


# ----------------------------- バージョン処理 -----------------------------
STABLE_RE = re.compile(r"^\d+(?:\.\d+)*$")  # 純粋な数値ドット区切りのみ＝安定版


def parse_ver(v):
    return tuple(int(x) for x in v.split("."))


def is_stable(v):
    return bool(STABLE_RE.match(v.strip()))


def cmp_ver(a, b):
    """a>b:1, a==b:0, a<b:-1 （長さ違いは0埋め）"""
    ta, tb = parse_ver(a), parse_ver(b)
    n = max(len(ta), len(tb))
    ta += (0,) * (n - len(ta))
    tb += (0,) * (n - len(tb))
    return (ta > tb) - (ta < tb)


def bump_level(cur, new):
    tc, tn = parse_ver(cur), parse_ver(new)
    tc += (0,) * (3 - len(tc))
    tn += (0,) * (3 - len(tn))
    if tn[0] != tc[0]:
        return "メジャー"
    if tn[1] != tc[1]:
        return "マイナー"
    return "パッチ"


def latest_stable_from_pypi(pkg):
    """PyPI の RSS から最新安定版を返す。失敗時は None。"""
    url = "https://pypi.org/rss/project/%s/releases.xml" % pkg.lower().replace("_", "-")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            xml = r.read().decode("utf-8", "replace")
    except Exception as e:
        print("WARN: %s fetch failed: %s" % (pkg, e))
        return None
    titles = re.findall(r"<title>([^<]+)</title>", xml)
    # 先頭は channel タイトルなので除外し、安定版のみ
    versions = [t.strip() for t in titles[1:] if is_stable(t)]
    if not versions:
        return None
    best = versions[0]
    for v in versions[1:]:
        if cmp_ver(v, best) > 0:
            best = v
    return best


# ----------------------------- ノートブック解析 -----------------------------
PIP_RE = re.compile(r"([A-Za-z0-9_.\-]+)==([0-9][0-9A-Za-z.\-]*)")


def scan_notebook_pins():
    """*.ipynb 内の 'pip install pkg==x.y.z' のピンを {pkg: ver} で返す。"""
    pins = {}
    for nb in glob.glob(os.path.join(ROOT, "**", "*.ipynb"), recursive=True):
        try:
            data = json.load(open(nb, encoding="utf-8"))
        except Exception:
            continue
        for cell in data.get("cells", []):
            src = "".join(cell.get("source", []))
            if "pip install" not in src:
                continue
            for line in src.splitlines():
                if "pip install" not in line:
                    continue
                for name, ver in PIP_RE.findall(line):
                    if is_stable(ver):
                        pins[name.lower().replace("_", "-")] = ver
    return pins


# ----------------------------- CUDA 13 互換ヒント -----------------------------
# 注意: ここで出すのは best-effort の「推定シグナル」であって断定ではない。
# 確定には実機 (DGX Spark aarch64 + CUDA 13 + sm_121 コンテナ) での実行が必要。
NVIDIA_CU_RE = re.compile(r"nvidia-[a-z0-9.\-]*-cu(\d+)", re.I)
CUDA13_RE = re.compile(r"cuda[ \-]?13", re.I)


def cuda_major_from_requires(requires_dist):
    """requires_dist (list[str]) から nvidia-*-cuNN 依存の CUDA メジャーを返す。
    cu13 を優先、無ければ cu12 等。該当なし/Noneは None。"""
    if not requires_dist:
        return None
    majors = set()
    for req in requires_dist:
        for m in NVIDIA_CU_RE.findall(req or ""):
            majors.add(m)
    if not majors:
        return None
    if "13" in majors:
        return "13"
    # それ以外は数値的に最大のものを返す (通常は単一)
    return max(majors, key=lambda x: int(x))


def has_aarch64_wheel(urls):
    """PyPI の配布ファイル一覧 (list[dict]) に linux aarch64 wheel があるか。
    CPU/GPU 別までは判定できない点に注意。"""
    if not urls:
        return False
    for u in urls:
        fn = (u or {}).get("filename", "")
        if fn.endswith(".whl") and "aarch64" in fn:
            return True
    return False


def grep_cuda13(text):
    """テキストから 'CUDA 13' 系の言及行を抽出して返す (無ければ空リスト)。"""
    if not text:
        return []
    return [ln.strip() for ln in text.splitlines() if CUDA13_RE.search(ln)]


def pypi_release_json(pkg, version):
    """PyPI JSON API から特定バージョンのリリース情報を返す。失敗時 None。"""
    url = "https://pypi.org/pypi/%s/%s/json" % (pkg.lower().replace("_", "-"), version)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("WARN: %s pypi-json failed: %s" % (pkg, e))
        return None


def fetch_text(url):
    """任意 URL のテキストを取得。失敗時 None。"""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print("WARN: changelog fetch failed (%s): %s" % (url, e))
        return None


def cuda13_hint(p, latest):
    """1 パッケージの CUDA13 互換ヒントを dict で返す。"""
    name = p["name"]
    wheel_label, aarch64_label = "取得失敗", "—"
    cuda_major = None
    if latest:
        data = pypi_release_json(name, latest)
        if data is not None:
            info = data.get("info", {}) or {}
            cuda_major = cuda_major_from_requires(info.get("requires_dist"))
            if cuda_major == "13":
                wheel_label = "cu13依存検出"
            elif cuda_major:
                wheel_label = "cu%s依存" % cuda_major
            else:
                wheel_label = "cu依存なし"
            aarch64_label = "あり" if has_aarch64_wheel(data.get("urls")) else "なし"

    snippets, cl_label = [], "—"
    changelog_url = p.get("changelog_url")
    if changelog_url:
        text = fetch_text(changelog_url)
        if text is None:
            cl_label = "取得失敗"
        else:
            snippets = grep_cuda13(text)
            cl_label = ("言及あり(%d)" % len(snippets)) if snippets else "言及なし"

    if cuda_major == "13":
        verdict = "🟢 cu13依存検出"
    elif snippets:
        verdict = "🟡 CHANGELOGに言及あり"
    else:
        verdict = "🔴 シグナルなし（CUDA13対応の根拠なし）"

    return {
        "name": name,
        "latest": latest or "—",
        "wheel": wheel_label,
        "aarch64": aarch64_label,
        "changelog": cl_label,
        "verdict": verdict,
        "snippets": snippets[:5],  # 表示は最大5行に制限
    }


# ----------------------------- 集計 -----------------------------
def build_report():
    cfg = json.load(open(CONFIG_PATH, encoding="utf-8"))
    pkgs = cfg.get("packages", [])
    pins = scan_notebook_pins() if cfg.get("scan_notebooks") else {}

    updates, info, cuda13 = [], [], []
    for p in pkgs:
        name = p["name"]
        key = name.lower().replace("_", "-")
        current = p.get("current")
        if pins.get(key):  # ノートブックのピンを優先
            current = pins[key]
        latest = latest_stable_from_pypi(name)
        note = p.get("note", "")
        if p.get("cuda13_watch"):  # オプトインしたものだけ CUDA13 ヒントを計算
            cuda13.append(cuda13_hint(p, latest))
        if latest is None:
            info.append((name, current or "—", "取得失敗", "", note))
            continue
        if current and is_stable(current):
            if cmp_ver(latest, current) > 0:
                updates.append((name, current, latest, bump_level(current, latest), note))
            else:
                info.append((name, current, latest, "最新", note))
        else:
            info.append((name, current or "—", latest, "参考", note))
    return updates, info, cuda13


def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_cuda13_section(cuda13):
    """CUDA13 互換ヒントの専用セクションを返す (対象が無ければ空文字)。"""
    if not cuda13:
        return ""
    parts = [
        "\n## 🧪 CUDA 13 互換ヒント（自動推定・要実機検証）\n",
        "> CHANGELOG / wheel 依存メタデータからの推定で、断定ではありません。\n"
        "> 確定には DGX Spark (aarch64 + CUDA 13 + sm_121) コンテナでの実行が必要です。\n",
        md_table(
            [(h["name"], "`%s`" % h["latest"], h["wheel"], h["aarch64"],
              h["changelog"], h["verdict"]) for h in cuda13],
            ["ライブラリ", "最新", "wheel依存", "aarch64 wheel", "CHANGELOG", "推定"]),
    ]
    for h in cuda13:
        if h["snippets"]:
            parts.append("\n**%s** CHANGELOG 該当行:" % h["name"])
            parts.append("\n".join("> %s" % s for s in h["snippets"]))
    return "\n".join(parts)


def build_issue_body(updates, info, cuda13=None):
    import datetime
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    parts = ["_最終チェック: %s（毎日自動更新）_\n" % now]
    if updates:
        parts.append("## 🔔 更新あり\n")
        parts.append(md_table(
            [(n, "`%s`" % c, "`%s`" % l, lv, note) for (n, c, l, lv, note) in updates],
            ["ライブラリ", "現在", "最新", "更新", "備考"]))
    else:
        parts.append("## ✅ watch-list に新しい更新はありません\n")
    section = build_cuda13_section(cuda13 or [])
    if section:
        parts.append(section)
    if info:
        parts.append("\n## 参考 / 情報\n")
        parts.append(md_table(
            [(n, "`%s`" % c, "`%s`" % l, s, note) for (n, c, l, s, note) in info],
            ["ライブラリ", "現在", "最新", "状態", "備考"]))
    parts.append(
        "\n---\n"
        "- 現在版は `.github/dep-watch.config.json` の `current` 値です。"
        "コンテナ/環境を更新したら値を更新してください（ノートブックに `pkg==x.y.z` のピンがあれば自動反映）。\n"
        "- この Issue は dep-watch が毎日 本文を更新します（クローズしても新たな更新があれば再オープンされます）。")
    return "\n".join(parts)


# ----------------------------- GitHub API -----------------------------
API = "https://api.github.com"


def gh(method, path, token, payload=None):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "dep-watch-action")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
        return json.loads(body) if body else {}


def ensure_label(repo, token):
    try:
        gh("POST", "/repos/%s/labels" % repo, token,
           {"name": LABEL, "color": "0e8a16",
            "description": "dependency update watcher"})
    except urllib.error.HTTPError as e:
        if e.code != 422:  # 422 = 既に存在
            print("WARN: label create:", e)


def find_issue(repo, token):
    issues = gh("GET", "/repos/%s/issues?state=all&labels=%s&per_page=20" % (repo, LABEL), token)
    for it in issues:
        if it.get("title") == ISSUE_TITLE and "pull_request" not in it:
            return it
    return None


def main():
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GH_REPO"]

    updates, info, cuda13 = build_report()
    body = build_issue_body(updates, info, cuda13)
    print("updates:", len(updates), "info:", len(info), "cuda13:", len(cuda13))

    ensure_label(repo, token)
    existing = find_issue(repo, token)

    if existing:
        num = existing["number"]
        # 更新があり、かつクローズ済みなら再オープン
        state = "open" if updates else existing.get("state", "open")
        gh("PATCH", "/repos/%s/issues/%d" % (repo, num), token,
           {"body": body, "state": state})
        print("updated issue #%d (state=%s)" % (num, state))
    else:
        # 初回は、更新が無くても追跡用に1件作成しておく
        created = gh("POST", "/repos/%s/issues" % repo, token,
                     {"title": ISSUE_TITLE, "body": body, "labels": [LABEL]})
        print("created issue #%s" % created.get("number"))


if __name__ == "__main__":
    main()

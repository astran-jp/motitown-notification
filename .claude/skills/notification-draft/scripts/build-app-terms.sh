#!/usr/bin/env bash
# アプリ(Unity)のソースから「画面に出る日本語」を抜き出し、app-terms.generated.txt を作る。
# これが「アプリ上でどう見えているか」の機械的な正本。用語 lint は glossary.txt + このファイルを allowlist に使う。
#
# 抽出元:
#   1. Assets/Motitan/Scripts/**/*.cs の日本語文字列リテラル
#   2. Assets/Localization/motitan-localization-table_ja.asset(Unity Localization の日本語表)
#   3. Assets/Motitan/**/*.prefab, *.unity の TextMeshPro テキスト(m_text)
#
# usage: build-app-terms.sh [motitan_app のパス]   (既定: ../motitan_app)
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$SKILL_DIR/../../../../motitan_app}"
APP="$(cd "$APP" && pwd)"
[ -d "$APP/Assets/Motitan/Scripts" ] || { echo "motitan_app が見つかりません: $APP" >&2; exit 2; }
OUT="$SKILL_DIR/app-terms.generated.txt"

{
  echo "# 自動生成: $(date +%F) motitan_app@$(cd "$APP" && git rev-parse --short HEAD 2>/dev/null || echo '?') から抽出。手で編集しない(scripts/build-app-terms.sh で再生成)"
  APP="$APP" python3 - <<'PY'
import os, re, json, glob
app = os.environ["APP"]
out = set()

def add(v):
    v = v.replace("\\n", "\n")
    v = re.sub(r"<[^>]*>", " ", v)          # TMP のリッチテキストタグ
    v = re.sub(r"\{[^}]*\}", " ", v)        # {0} や $"{name}" の補間
    for line in v.split("\n"):
        line = line.strip()
        if re.search(r"[ぁ-んァ-ヶ一-龥]", line):
            out.add(line)

# 1. C# 文字列リテラル(ログ・例外らしき "[Tag] ..." は除く)
for f in glob.glob(os.path.join(app, "Assets/Motitan/Scripts/**/*.cs"), recursive=True):
    try:
        s = open(f, encoding="utf-8").read()
    except Exception:
        continue
    for m in re.finditer(r'\$?"([^"\\]*(?:\\.[^"\\]*)*)"', s):
        v = m.group(1)
        if v.startswith("[") or not re.search(r"[ぁ-んァ-ヶ一-龥]", v):
            continue
        add(v)

# 2. Unity Localization 日本語表(\uXXXX でエスケープされている)
ja = os.path.join(app, "Assets/Localization/motitan-localization-table_ja.asset")
if os.path.exists(ja):
    for m in re.finditer(r"m_Localized:\s*(.+)", open(ja, encoding="utf-8").read()):
        v = m.group(1).strip()
        if v.startswith('"') and v.endswith('"'):
            try:
                v = json.loads(v)
            except Exception:
                v = v[1:-1]
        add(v)

# 3. prefab / scene の TextMeshPro テキスト
for pat in ("Assets/Motitan/**/*.prefab", "Assets/Motitan/**/*.unity"):
    for f in glob.glob(os.path.join(app, pat), recursive=True):
        try:
            s = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for m in re.finditer(r"m_text:\s*(.+)", s):
            v = m.group(1).strip()
            if v.startswith('"') and v.endswith('"'):
                try:
                    v = json.loads(v)
                except Exception:
                    v = v[1:-1]
            add(v)

for t in sorted(out):
    print(t)
PY
} > "$OUT"
echo "wrote $OUT ($(grep -vc '^#' "$OUT") lines)" >&2

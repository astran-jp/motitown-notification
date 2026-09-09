#!/usr/bin/env bash
# お知らせ原稿を Gemini に書かせる。
#
# usage: dispatch.sh <N> <brief.md> <out.md>
#   N        お知らせ番号
#   brief.md 伝えたい内容(箇条書きのメモで可)
#   out.md   原稿の出力先(通常 {N}/draft.md)
#
# env:
#   GEMINI_MODEL  使うモデル(既定: gemini-3.8-flash)
#   GEMINI_API_KEY or ~/.gemini/settings.json の認証設定が必要
set -euo pipefail

N="${1:?usage: dispatch.sh <N> <brief.md> <out.md>}"
BRIEF="${2:?brief.md}"
OUT="${3:?out.md}"
MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 認証: 環境に無ければ ~/.zsh_secret の GEMINI_API_KEY を読む
if [ -z "${GEMINI_API_KEY:-}" ] && [ -f "$HOME/.zsh_secret" ]; then
  # shellcheck disable=SC1090
  set +u; source "$HOME/.zsh_secret"; set -u
fi
command -v gemini >/dev/null || { echo "gemini CLI が見つかりません: npm i -g @google/gemini-cli" >&2; exit 2; }
[ -f "$BRIEF" ] || { echo "brief が見つかりません: $BRIEF" >&2; exit 2; }

# 過去の原稿(draft.md)を新しい順に最大2件。無ければ空
EXAMPLES=""
for d in $(ls "$REPO_DIR" | grep -E '^[0-9]+$' | sort -rn); do
  [ "$d" = "$N" ] && continue   # 今回の番号の原稿(再実行時の前回出力)は例に含めない
  f="$REPO_DIR/$d/draft.md"
  [ -f "$f" ] || continue
  EXAMPLES+=$'\n''--- '"$d/draft.md"$' ---\n'"$(cat "$f")"$'\n'
  [ "$(printf '%s' "$EXAMPLES" | grep -c '^--- ')" -ge 2 ] && break
done
[ -n "$EXAMPLES" ] || EXAMPLES="(過去の原稿はまだありません)"

# テンプレートの {{...}} をファイル内容で置換(node で安全に文字列置換)
# ブリーフ自体の用語検査(Notion の内部名などが混ざっていたらここで止める)
if ! python3 "$SKILL_DIR/scripts/lint.py" --terms-only "$BRIEF"; then
  echo "brief に未定義用語があります。glossary.txt の表記に直すか、正しい UI 用語なら glossary.txt に追加してから再実行してください。" >&2
  exit 6
fi

# 公式UI用語集(コメントと出典メモを除く)
GLOSSARY="$(grep -v '^\s*#' "$SKILL_DIR/glossary.txt" 2>/dev/null | grep -v '^\s*$' | sed 's/\s*#.*$//' | sed 's/^/- /')"

# 禁句・禁止表現(コメント行と空行を除く)
BANNED_WORDS="$(grep -v '^\s*#' "$SKILL_DIR/banned-words.txt" 2>/dev/null | grep -v '^\s*$' | sed 's/^/- /')"
BANNED_PATTERNS="$(grep -v '^\s*#' "$SKILL_DIR/banned-patterns.txt" 2>/dev/null | grep -v '^\s*$' | sed 's/^/- /')"

build_prompt() { # $1 = 再試行時の注記(空なら無し)
  PERSONA="$SKILL_DIR/persona.md" GUIDE="$SKILL_DIR/writing-guide.md" TEMPLATE="$SKILL_DIR/prompt-template.md" \
  BRIEF_FILE="$BRIEF" EXAMPLES="$EXAMPLES" NUMBER="$N" BANNED_WORDS="$BANNED_WORDS" BANNED_PATTERNS="$BANNED_PATTERNS" GLOSSARY="$GLOSSARY" RETRY_NOTE="${1:-}" \
  node -e '
    const fs = require("fs"), e = process.env;
    const r = p => fs.readFileSync(p, "utf8");
    let t = r(e.TEMPLATE);
    const m = { PERSONA: r(e.PERSONA), GUIDE: r(e.GUIDE), EXAMPLES: e.EXAMPLES, NUMBER: e.NUMBER, BRIEF: r(e.BRIEF_FILE),
                BANNED_WORDS: e.BANNED_WORDS, BANNED_PATTERNS: e.BANNED_PATTERNS, GLOSSARY: e.GLOSSARY, RETRY_NOTE: e.RETRY_NOTE };
    for (const [k, v] of Object.entries(m)) t = t.split("{{" + k + "}}").join(v);
    process.stdout.write(t);
  ' > "$WORK/prompt.md"
}
build_prompt ""

run_gemini() {
  echo "model=$MODEL prompt=$(wc -c < "$WORK/prompt.md")bytes" >&2
  [ -n "${DISPATCH_KEEP_PROMPT:-}" ] && cp "$WORK/prompt.md" "$DISPATCH_KEEP_PROMPT"

  # 空の作業ディレクトリで実行(リポジトリをワークスペースとして読ませない)。
  # プロンプト本体は stdin、-p は短い指示のみ。
  (
    cd "$WORK"
    gemini -m "$MODEL" --skip-trust --approval-mode plan --output-format json \
      -p "上の指示に従って原稿を書いてください。原稿の Markdown だけを出力してください。" \
      < "$WORK/prompt.md"
  ) > "$WORK/raw.json" 2> "$WORK/stderr.log" || true
  [ -n "${DISPATCH_KEEP_RAW:-}" ] && cp "$WORK/raw.json" "$DISPATCH_KEEP_RAW"

  # JSON の response を取り出す。認証エラー等の JSON は stderr に出るので、stdout が空なら stderr を見る。
  # 先頭に CLI の注意書きが混ざることがあるので "{" で始まる行から読む。JSON でなければそのまま。
  # 先頭/末尾のコードフェンスは剥がす
  node -e '
    const fs = require("fs");
    const raw = fs.readFileSync(process.argv[1], "utf8");
    const err = fs.readFileSync(process.argv[2], "utf8");
    const s = raw.trim() ? raw : err;
    let out = s;
    const i = s.search(/^\{/m);
    if (i >= 0) {
      try {
        const j = JSON.parse(s.slice(i));
        if (j.error) { console.error("gemini error:", j.error.message ?? JSON.stringify(j.error)); process.exit(3); }
        out = j.response ?? "";
      } catch (_) {}
    }
    out = out.trim().replace(/^```[a-zA-Z]*\n/, "").replace(/\n```$/, "").trim() + "\n";
    if (!out.startsWith("---")) {
      console.error("frontmatter で始まっていません。出力を確認してください:\n" + s.slice(0, 500));
      process.exit(4);
    }
    fs.writeFileSync(process.argv[3], out);
  ' "$WORK/raw.json" "$WORK/stderr.log" "$OUT"
}

# 生成 → lint(機械検査) → term-judge(LLM による用語判定)。違反があれば違反一覧を添えて書き直させる
MAX_ATTEMPTS="${DISPATCH_MAX_ATTEMPTS:-3}"
attempt=1
while :; do
  run_gemini
  ok=1
  python3 "$SKILL_DIR/scripts/lint.py" "$OUT" > "$WORK/lint.log" 2>&1 || ok=0
  if [ "$ok" = 1 ] && [ -z "${DISPATCH_SKIP_JUDGE:-}" ]; then
    "$SKILL_DIR/scripts/term-judge.sh" "$OUT" >> "$WORK/lint.log" 2>&1 || ok=0
  fi
  cat "$WORK/lint.log" >&2
  [ "$ok" = 1 ] && break
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "lint 違反が残っています(${attempt}回試行)。$OUT を手で直すか、ブリーフを補強して再実行してください。" >&2
    exit 5
  fi
  attempt=$((attempt + 1))
  echo "--- lint 違反があるため書き直し(${attempt}/${MAX_ATTEMPTS}) ---" >&2
  NOTE="## 前回の出力に対する機械検査の違反(必ず全て解消すること)"$'\n'"$(grep '^NG' "$WORK/lint.log" | sed 's/^NG *//; s/^/- /')"$'\n'"前回の出力:"$'\n''```'$'\n'"$(cat "$OUT")"$'\n''```'
  build_prompt "$NOTE"
done

echo "wrote $OUT" >&2

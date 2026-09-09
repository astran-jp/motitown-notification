#!/usr/bin/env bash
# 用語の LLM 判定。機械的な lint(カタカナ語・英字語・「」・操作手順)では拾えない
# 「日本語の複合語として作られた機能名」(例: フレーズ対戦機能、単語スキップ機能)を Gemini に探させる。
#
# usage: term-judge.sh <draft.md>
# exit 0: 問題なし / 1: 未定義用語あり(NG 行を stdout に出す) / 3: gemini エラー
#
# env: GEMINI_MODEL(既定 gemini-3.8-flash), GEMINI_API_KEY(~/.zsh_secret から自動読込)
set -euo pipefail
DRAFT="${1:?usage: term-judge.sh <draft.md>}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

if [ -z "${GEMINI_API_KEY:-}" ] && [ -f "$HOME/.zsh_secret" ]; then set +u; source "$HOME/.zsh_secret"; set -u; fi

{
  cat <<'HDR'
あなたはモチタン・モチスピ(語学学習アプリ)のお知らせ原稿の校閲者です。
原稿の中で「アプリの機能・画面・ボタン・モード・プランなどを指す固有の呼び名」をすべて列挙し、
それぞれが下の「公式UI用語集」に **表記まで完全一致** で存在するかを判定してください。

判定のルール:
- 用語集に無い呼び名は、AI が作った未定義用語とみなす(例: 「フレーズ対戦機能」「単語スキップ機能」「Book画面」)
- 一般的な日本語(例: 再生、再生速度、対戦、単語、改善、追加、更新)や、動作の説明文は対象外。下の「一般語(対象外)」にある語も対象外
- 用語集の語の一部だけを一般語として使うのは問題なし(例: 用語集に「再生速度（倍）」があり、本文で「再生速度を変更できる」と書く)
- 用語集の語を助詞でつないだ説明(例: 「フレーズ帳から対戦をプレイ」)は問題なし。名詞をくっつけて新しい名前にしたもの(例: 「フレーズ帳対戦」)は未定義用語
- 迷ったら「未定義」側に倒してよい(人が最終確認する)

出力は JSON のみ。形式:
{"undefined_terms":[{"term":"...","line":"その語を含む原稿の行をそのまま","suggestion":"用語集の語を使った言い換え案"}]}
問題が無ければ {"undefined_terms":[]} を出力。

# 公式UI用語集
HDR
  grep -v '^\s*#' "$SKILL_DIR/glossary.txt" | grep -v '^\s*$' | sed 's/\s*#.*$//'
  echo
  echo "# 一般語(対象外)"
  grep -v '^\s*#' "$SKILL_DIR/common-words.txt" | grep -v '^\s*$'
  echo
  echo "# 原稿"
  cat "$DRAFT"
} > "$WORK/prompt.md"

(
  cd "$WORK"
  gemini -m "$MODEL" --skip-trust --approval-mode plan --output-format json \
    -p "上の指示に従って判定し、JSON だけを出力してください。" < "$WORK/prompt.md"
) > "$WORK/raw.json" 2> "$WORK/stderr.log" || true

node -e '
  const fs = require("fs");
  const raw = fs.readFileSync(process.argv[1], "utf8"), err = fs.readFileSync(process.argv[2], "utf8");
  const s = raw.trim() ? raw : err;
  const i = s.search(/^\{/m);
  let j; try { j = JSON.parse(s.slice(i)); } catch (e) { console.error("judge: 応答を解釈できません\n" + s.slice(0, 400)); process.exit(3); }
  if (j.error) { console.error("gemini error:", j.error.message ?? JSON.stringify(j.error)); process.exit(3); }
  let body = (j.response ?? "").trim().replace(/^```[a-zA-Z]*\n/, "").replace(/\n```$/, "").trim();
  const k = body.indexOf("{"); if (k > 0) body = body.slice(k);
  let r; try { r = JSON.parse(body); } catch (e) { console.error("judge: JSON を解釈できません\n" + body.slice(0, 400)); process.exit(3); }
  const terms = r.undefined_terms ?? [];
  for (const t of terms) console.log(`NG   judge: 未定義用語「${t.term}」→ ${t.suggestion ?? ""}: ${t.line ?? ""}`);
  console.log(terms.length ? `judge: ${terms.length} 件の未定義用語` : "judge: OK");
  process.exit(terms.length ? 1 : 0);
' "$WORK/raw.json" "$WORK/stderr.log"

#!/usr/bin/env python3
"""お知らせ原稿(draft.md)の機械検査。

usage: lint.py <draft.md>
exit 0: 合格 / 1: 違反あり / 2: 引数・ファイルエラー

検査項目:
  - 禁句 (banned-words.txt, 部分一致)
  - 禁止表現 (banned-patterns.txt, 正規表現)
  - frontmatter の必須項目 (number / title / date / apps / author / banner)
  - 冒頭「モチタン・モチスピを開発している神谷です。」/ 末尾の署名「開発者 神谷創」
  - 「！」は本文全体で1つまで
  - TBD の残存は警告(exit には影響しない)
  - 未定義用語: カタカナ語・英字語・「」内の語・操作手順(A > B > C)の各段・「〜機能/画面/モード/タブ/設定」の複合語が、
    glossary.txt(公式UI用語) / app-terms.generated.txt(アプリの文字列リテラル) / common-words.txt(一般語) のどれにも
    無ければ違反。AI が作った用語(例: "Book画面")をここで弾く

  --terms-only : 用語検査だけを行う(brief.md 用。冒頭・署名・frontmatter は見ない)
"""
import os, re, sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENING = "モチタン・モチスピを開発している神谷です。"
SIGNATURE = "開発者 神谷創"
REQUIRED_FM = ["number", "title", "date", "apps", "author", "banner"]


def load_list(name):
    path = os.path.join(SKILL_DIR, name)
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        out.append(line)
    return out


# ── 用語検査 ─────────────────────────────────────────────
KATAKANA = r"[ァ-ヶー]{2,}"
LATIN = r"[A-Za-z][A-Za-z0-9+/&.\-]*[A-Za-z0-9]|[A-Za-z]{2,}"
QUOTED = r"「([^」]{1,30})」"
COMPOUND = r"[一-龥ァ-ヶーA-Za-z]{1,12}(?:機能|画面|モード|タブ|設定|ボタン|帳|プラン|ページ)"
SUFFIX_ONLY = {"機能", "画面", "モード", "タブ", "設定", "ボタン", "帳", "プラン", "ページ"}


def load_terms():
    glossary = set(load_list("glossary.txt"))
    app = [l for l in load_list("app-terms.generated.txt")]
    common = set(load_list("common-words.txt"))
    # glossary は「表記 # 出典」の形を許す
    glossary = {t.split("#")[0].strip() for t in glossary}
    return glossary, app, common


def term_ok(term, glossary, app, common):
    t = term.strip()
    if not t or t in glossary or t in common:
        return True
    if t in SUFFIX_ONLY:
        return True
    if re.fullmatch(r"v?\d+(\.\d+)*", t):
        return True
    # glossary の語を並べただけの複合(例: フレーズ帳詳細 = フレーズ帳 + 詳細)は、
    # 先頭が glossary 語なら残りも再帰的に確かめる
    for g in sorted(glossary, key=len, reverse=True):
        if len(g) >= 2 and t.startswith(g) and t != g:
            rest = t[len(g):]
            if term_ok(rest, glossary, app, common):
                return True
    # アプリの文字列リテラルに完全一致で含まれるか(部分一致は緩すぎるので不可)
    return t in app


def extract_terms(line):
    found = []
    for m in re.finditer(QUOTED, line):
        q = m.group(1)
        # 長い引用(文)や記号だけの引用(「→」)は用語ではない
        if len(q) <= 14 and re.search(r"[A-Za-z0-9ぁ-んァ-ヶ一-龥]", q):
            found.append(q)
    for m in re.finditer(COMPOUND, line):
        found.append(m.group(0))
    for m in re.finditer(KATAKANA, line):
        found.append(m.group(0))
    for m in re.finditer(LATIN, line):
        found.append(m.group(0))
    return found


def check_terms(lines, skip_prefixes=()):
    glossary, app, common = load_terms()
    appset = set(app)
    errors = []
    seen = set()
    for i, line in enumerate(lines, 1):
        raw = line.strip()
        if not raw or raw == "---" or raw.startswith(skip_prefixes):
            continue
        # frontmatter: 機械的な項目は見ない。title/banner は値だけ見る
        if re.match(r"^(number|date|apps|author):", raw):
            continue
        m = re.match(r"^(title|banner|list_title):\s*(.*)$", raw)
        if m:
            raw = m.group(2)
        # 操作手順の行は各段が UI 用語に完全一致しなければならない
        if " > " in raw and not raw.startswith("#"):
            path = raw
            # 先頭のリスト記号とラベル(「- 導線: 」「再生速度の設定場所: 」)を外す
            path = re.sub(r"^[-*・]\s*", "", path)
            head = path.split(">", 1)[0]
            if re.search(r"[:：]", head):
                path = path[path.rfind(":", 0, len(head)) + 1:] if ":" in head else path
                path = path[path.rfind("：", 0, len(head)) + 1:] if "：" in head else path
            for seg in [s.strip() for s in path.split(">")]:
                seg = re.sub(r"\s*\([^)]*\)\s*$", "", seg).strip()  # 末尾の半角括弧の補足は外す(全角括弧は用語の一部)
                seg = re.sub(r"\s*\([^)]*\)\s*$", "", seg).strip()
                if seg and seg != "TBD" and seg not in glossary and seg not in appset:
                    key = ("path", seg)
                    if key not in seen:
                        seen.add(key)
                        errors.append(f"L{i}: 操作手順の段「{seg}」がアプリの表記にありません: {raw}")
            continue
        for t in extract_terms(raw):
            if term_ok(t, glossary, appset, common):
                continue
            key = ("term", t)
            if key in seen:
                continue
            seen.add(key)
            errors.append(f"L{i}: 未定義用語「{t}」(glossary/app-terms/common-words のどれにも無い): {raw}")
    return errors


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    terms_only = "--terms-only" in sys.argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"読めません: {e}", file=sys.stderr)
        return 2

    errors, warnings = [], []
    lines = text.split("\n")

    if terms_only:
        errors = check_terms(lines, skip_prefixes=("#",))
        for e in errors:
            print("NG  ", e)
        print(f"lint(terms): {len(errors)} 件の違反" if errors else "lint(terms): OK")
        return 1 if errors else 0

    # frontmatter
    fm = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body_start = i + 1
                break
            m = re.match(r"^([A-Za-z_]+):\s*(.*)$", lines[i])
            if m:
                fm[m.group(1)] = m.group(2).strip()
    else:
        errors.append("L1: frontmatter(---)で始まっていません")
    for k in REQUIRED_FM:
        if not fm.get(k):
            errors.append(f"frontmatter: {k} がありません")

    body_lines = lines[body_start:]
    body = "\n".join(body_lines)

    # 禁句 / 禁止表現 は frontmatter を含む全体に掛ける
    words = load_list("banned-words.txt")
    patterns = [(p, re.compile(p, re.MULTILINE)) for p in load_list("banned-patterns.txt")]
    for i, line in enumerate(lines, 1):
        low = line.lower()
        for w in words:
            if w.lower() in low:
                errors.append(f"L{i}: 禁句「{w}」: {line.strip()}")
        for src, rx in patterns:
            if rx.search(line):
                errors.append(f"L{i}: 禁止表現 /{src}/: {line.strip()}")

    # 未定義用語
    errors += check_terms(lines)

    # 冒頭・署名
    nonblank = [l.strip() for l in body_lines if l.strip()]
    # 冒頭は h1 の次の非空行
    after_h1 = [l for l in nonblank if not l.startswith("# ")]
    if not after_h1 or after_h1[0] != OPENING:
        errors.append(f"冒頭が「{OPENING}」ではありません: {after_h1[0] if after_h1 else '(空)'}")
    if not nonblank or nonblank[-1] != SIGNATURE:
        errors.append(f"末尾が署名「{SIGNATURE}」ではありません: {nonblank[-1] if nonblank else '(空)'}")

    # 「！」の数
    n_excl = body.count("！") + body.count("!")
    if n_excl > 1:
        errors.append(f"「！」が {n_excl} 個あります(1つまで)")

    # TBD
    for i, line in enumerate(lines, 1):
        if "TBD" in line:
            warnings.append(f"L{i}: TBD が残っています: {line.strip()}")

    for w in warnings:
        print("WARN", w)
    for e in errors:
        print("NG  ", e)
    if errors:
        print(f"lint: {len(errors)} 件の違反")
        return 1
    print("lint: OK" + (f" (警告 {len(warnings)} 件)" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

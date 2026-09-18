#!/usr/bin/env python3
"""アプリ(motitan_app)の Localization String Table から日本語 → 英語の対訳を引く。

usage: glossary.py <日本語の語句> [<語句> ...]

画面名・ボタン名・機能名(市民リーグ、記憶度、プレミアムチケット …)の英語表記を、英語版アプリの文言に合わせるために使う。
アプリのリポジトリは環境変数 MOTITAN_APP で指す(既定は ../motitan_app)。
"""
import os, re, sys

APP = os.environ.get("MOTITAN_APP", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "motitan_app"))
TABLE = os.path.join(APP, "Assets", "Localization", "motitan-localization-table_{}.asset")
ENTRY = re.compile(r"- m_Id: (\d+)\n\s+m_Localized: (.*)")


def decode(raw):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
        raw = re.sub(r"\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), raw)
        raw = raw.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    return raw


def load(code):
    path = TABLE.format(code)
    if not os.path.isfile(path):
        raise SystemExit(f"テーブルが無い: {path}(MOTITAN_APP でアプリのリポジトリを指定する)")
    text = open(path, encoding="utf-8").read()
    # 値が複数行に折り返されている場合は最初の行だけ(検索用途なので十分)
    return {m.group(1): decode(m.group(2)) for m in ENTRY.finditer(text)}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ja, en = load("ja"), load("en")
    for q in sys.argv[1:]:
        hits = [(k, v) for k, v in ja.items() if q in v]
        print(f"== {q}: {len(hits)} 件")
        for k, v in hits[:15]:
            print(f"  ja: {v[:60]!r}\n  en: {en.get(k, '')[:80]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

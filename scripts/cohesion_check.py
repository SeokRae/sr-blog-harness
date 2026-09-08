#!/usr/bin/env python3
"""초안의 문단 응집 점검 재료를 출력한다.

판정하지 않는다. 주제열(각 문장의 첫 어절)과 문단 크기, 나열 위치, 예고 사슬을
사람이 볼 수 있게 펼쳐 놓을 뿐이다. 한국어 문장 분리와 어절 추출은 근사치이므로
플래그가 붙었다고 문제인 것도, 안 붙었다고 통과인 것도 아니다.

사용법: python3 cohesion_check.py _drafts/{slug}.md [--all]

기본은 editor의 점검 우선순위만 출력한다. 예고 사슬, 세 항목 이상 나열,
플래그가 붙은 문단(긴 문단과 정박 한도 초과), 개수와 번호 라벨.
--all을 주면 모든 문단의 주제열을 펼친다.
"""

import re
import sys

JOSA = ("으로서", "으로써", "이라는", "라는", "에서는", "에서", "으로", "로써", "로서",
        "에게", "한테", "까지", "부터", "처럼", "보다", "마저", "조차", "라도",
        "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "와", "과", "로")

LABEL_PATTERN = re.compile(r"첫째|둘째|셋째|넷째|[0-9]가지|세 가지|네 가지|두 가지|다음 세")
SENT_END = re.compile(r"(?<![0-9])[.!?](?=\s|$)")
INLINE_CODE = re.compile(r"`[^`]*`")
EMPHASIS = re.compile(r"[*_~]+")
NAME_COMMENT = re.compile(r"<!--\s*작성자 노트:\s*소주제 이름\s*=\s*(.+?)\s*-->")


def strip_frontmatter(lines):
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1:], i + 1
    return lines, 0


def blocks_of(lines, offset):
    """빈 줄로 나눈 블록을 (시작줄번호, 종류, 줄목록)으로 돌려준다. 코드펜스는 통째로 버린다."""
    out, buf, start, in_fence = [], [], 0, False
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\n")
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if buf:
                out.append((start, kind_of(buf), buf))
                buf = []
            continue
        if in_fence:
            continue
        if not line.strip():
            if buf:
                out.append((start, kind_of(buf), buf))
                buf = []
            continue
        if not buf:
            start = idx + offset + 1
        buf.append(line)
    if buf:
        out.append((start, kind_of(buf), buf))
    return out


def kind_of(buf):
    head = buf[0].lstrip()
    if head.startswith("#"):
        return "heading"
    if re.match(r"^([-*+]|\d+\.)\s", head):
        return "list"
    if head.startswith(">"):
        return "quote"
    if head.startswith("|"):
        return "table"
    if head.startswith("<!--"):
        return "comment"
    if re.match(r"^\[\^[^\]]+\]:", head):
        return "footnote"
    return "para"


def sentences(text):
    text = INLINE_CODE.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    text = EMPHASIS.sub("", text)
    parts, last = [], 0
    for m in SENT_END.finditer(text):
        chunk = text[last:m.end()].strip()
        if chunk:
            parts.append(chunk.replace("\x00", "."))
        last = m.end()
    tail = text[last:].strip()
    if tail:
        parts.append(tail.replace("\x00", "."))
    return parts


def topic_of(sentence):
    words = sentence.split()
    if not words:
        return ""
    topic = " ".join(words[:2])
    return topic[:16] + ("…" if len(topic) > 16 else "")


def stem(word):
    core = word.split()[0] if word.split() else word
    for j in sorted(JOSA, key=len, reverse=True):
        if len(core) > len(j) + 1 and core.endswith(j):
            return core[: -len(j)]
    return core


def longest_same_run(topics):
    best = run = 1
    for a, b in zip(topics, topics[1:]):
        run = run + 1 if a and stem(a) == stem(b) else 1
        best = max(best, run)
    return best if topics else 0


def main():
    args = [a for a in sys.argv[1:] if a != "--all"]
    show_all = "--all" in sys.argv
    if len(args) != 1:
        print(__doc__.strip())
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        raw = f.readlines()

    body, offset = strip_frontmatter(raw)
    text = "".join(body)
    blocks = blocks_of(body, offset)

    print(f"초안: {path}")

    m = NAME_COMMENT.search(text)
    names = [n.strip() for n in re.split(r"[|,]", m.group(1)) if n.strip()] if m else []
    headings = [(s, b[0].lstrip("# ").strip()) for s, k, b in blocks if k == "heading"]

    print("\n[예고 사슬]")
    if names:
        print(f"  작성자 노트 이름: {' | '.join(names)}")
        missing = [n for n in names if not any(n in h for _, h in headings)]
        extra = [h for _, h in headings if not any(n in h for n in names)]
        print(f"  소제목에 없는 이름: {' | '.join(missing) if missing else '없음'}")
        if extra:
            print(f"  이름에 없는 소제목: {' | '.join(extra)}")
    else:
        print("  작성자 노트 주석 없음. 도입부에서 예고된 이름을 직접 추려 기준으로 삼는다")
        for _, h in headings[:10]:
            print(f"    소제목: {h}")
        if len(headings) > 10:
            print(f"    (소제목 {len(headings)}개 중 10개만 표시)")

    header = "  각 문장의 첫 어절. 패턴이 설명되는지는 사람이 본다"
    print("\n[문단 주제열]" + ("  전체" if show_all else "  플래그가 붙은 문단만 (--all로 전체)"))
    print(header)
    prev_kind, shown, skipped = None, 0, 0
    for start, kind, buf in blocks:
        if kind in ("heading", "comment", "table", "quote", "footnote"):
            prev_kind = kind
            continue
        if kind == "list":
            items = sum(1 for line in buf if re.match(r"^\s*([-*+]|\d+\.)\s", line))
            if items >= 3:
                umbrella = "직전에 문단 있음" if prev_kind == "para" else f"직전이 {prev_kind or '없음'}"
                print(f"  L{start} 나열 {items}항목  [우산 확인: {umbrella}]")
            prev_kind = kind
            continue
        topics = [topic_of(s) for s in sentences(" ".join(buf))]
        flags = []
        if len(topics) > 5:
            flags.append("긴 문단")
        run = longest_same_run(topics)
        if run >= 4:
            flags.append(f"같은 주제 {run}문장 연속(정박 한도 4)")
        if not flags and not show_all:
            skipped += 1
            prev_kind = kind
            continue
        mark = "  [" + ", ".join(flags) + "]" if flags else ""
        print(f"  L{start} ({len(topics)}문장){mark}")
        for i, t in enumerate(topics, 1):
            print(f"      {i}. {t}")
        shown += 1
        prev_kind = kind

    if not show_all:
        print(f"  플래그 {shown}개 문단, 조용한 문단 {skipped}개")

    print("\n[개수와 번호 라벨]  걸린 줄이 전부 문제는 아니다. 판단은 사람이 한다")
    hits = [(i + 1, line.rstrip()) for i, line in enumerate(raw) if LABEL_PATTERN.search(line)]
    for num, line in hits:
        print(f"  L{num}: {line.strip()[:70]}")
    if not hits:
        print("  없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())

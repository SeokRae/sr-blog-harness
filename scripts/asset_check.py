#!/usr/bin/env python3
"""포스트가 참조하는 사이트 내부 경로가 발행본에 실리는지 점검한다. (#7)

로컬 jekyll build는 작업 트리를 읽으므로, 커밋하지 않은 assets 파일도 빌드에 들어가 통과한다.
그 상태로 포스트만 커밋하면 Pages 빌드에는 파일이 없어 임베드가 404가 된다.

링크 대상만 본다. 마크다운 링크와 이미지의 ](...), HTML의 src=, href=.
그중 {{ site.baseurl }}/x, /blog/x, {{ '/x' | relative_url }} 형태만 사이트 내부 경로로 친다.
외부 URL 속 /blog/(다른 사이트의 블로그 주소)와 코드펜스, 인라인 코드 안의 예시는 버린다.

사용법: 블로그 저장소 루트에서 jekyll build 후
    python3 asset_check.py _posts/{date}-{slug}.md [site_dir]

출력
    미추적: L{n} {path}  저장소에 파일은 있으나 git이 모른다. 포스트와 같은 커밋에 넣는다
    없음: L{n} {path}    빌드 결과에도 없다. 깨진 참조다
문제가 있으면 exit 1, 없으면 0. 빌드 결과 폴더가 없으면 2.
"""

import os
import re
import subprocess
import sys
from urllib.parse import unquote

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
TARGET = re.compile(r"\]\(([^)]+)\)|\b(?:src|href)=\"([^\"]+)\"|\b(?:src|href)='([^']+)'")
SITE_PATH = (
    re.compile(r"^\{\{\s*site\.baseurl\s*\}\}/(.*)$"),
    re.compile(r"^/blog/(.*)$"),
    re.compile(r"^\{\{\s*['\"]/([^'\"]*)['\"]\s*\|\s*relative_url\s*\}\}$"),
)


def targets(lines):
    """(줄번호, 링크 대상)을 돌려준다. 코드펜스와 인라인 코드는 건너뛴다."""
    in_fence = False
    for num, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in TARGET.finditer(INLINE_CODE.sub("", line)):
            raw = next(group for group in match.groups() if group is not None).strip()
            # 마크다운 링크 제목("...")을 떼되, Liquid 태그 안의 공백은 살린다.
            if raw.startswith("{{") and "}}" in raw:
                end = raw.index("}}") + 2
                rest = raw[end:]
                yield num, raw[:end] + (rest.split()[0] if rest and not rest[0].isspace() else "")
            else:
                yield num, raw.split()[0]


def site_path(target):
    for pattern in SITE_PATH:
        found = pattern.match(target)
        if found:
            return unquote(re.split(r"[#?]", found.group(1))[0])
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    post = sys.argv[1]
    site = sys.argv[2] if len(sys.argv) > 2 else "_site"
    if not os.path.isdir(site):
        print(f"빌드 결과가 없다: {site} (jekyll build 먼저)", file=sys.stderr)
        return 2

    with open(post, encoding="utf-8") as f:
        lines = f.read().splitlines()

    seen, problems = set(), []
    for num, target in targets(lines):
        path = site_path(target)
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path):
            # 원본이 저장소에 있는 파일이다. git이 알아야 Pages에 실린다.
            tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                                     capture_output=True).returncode == 0
            if not tracked:
                problems.append(f"미추적: L{num} {path}")
        elif not os.path.exists(os.path.join(site, path)):
            # 퍼머링크처럼 빌드가 만드는 경로는 원본 파일이 없다. 빌드 결과에서 찾는다.
            problems.append(f"없음: L{num} {path}")

    for line in problems:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

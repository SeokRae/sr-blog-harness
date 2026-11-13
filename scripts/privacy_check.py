#!/usr/bin/env python3
"""공개 저장소에 커밋할 포스트와 리서치 노트에서 개인 정보 후보를 찾는다. (#13)

리서치 노트는 포스트와 함께 공개 저장소에 커밋된다. 근거 출처를 적다 보면
홈 디렉터리 절대 경로, 비공개 저장소 이름, 세션 기록 경로가 그대로 들어간다.
한번 push하면 파일을 고쳐도 이력에 남으므로, 커밋 전에 찾아야 한다.

찾는 것
    경로      절대 홈 경로 (/Users/{이름}/, /home/{이름}/, C:\\Users\\{이름}\\)
    세션      Claude Code 세션 기록 경로 (~/.claude/projects/...)
    이메일    이메일 주소 (noreply 주소와 example, test 같은 예약 도메인은 뺀다)
    저장소    작성자 계정의 비공개 저장소 이름 (gh CLI로 목록을 받는다)
              한 단어 이름은 계정/이름, "이름 저장소"처럼 저장소로 읽히는 자리에서만 찾는다

판정은 하지 않는다. 공개해도 되는 값인지는 사람이 정한다.
~/ 로 시작하는 경로는 사용자 이름이 드러나지 않으므로 경로로 치지 않는다.

사용법: 블로그 저장소 루트에서
    python3 privacy_check.py _posts/{date}-{slug}.md _drafts/{slug}.research.md [--owner 계정]

--owner를 주지 않으면 gh로 로그인한 계정을 쓴다.

출력
    {종류}: {파일}:L{n} {찾은 문자열}
    알림: ...  비공개 저장소 목록을 받지 못했을 때. 나머지 점검은 계속한다
찾은 것이 있으면 exit 1, 없으면 0. 파일을 못 읽으면 2.
"""

import json
import re
import subprocess
import sys

HOME_PATH = re.compile(r"(/Users/[^/\s`'\")]+/|/home/[^/\s`'\")]+/|[A-Za-z]:\\Users\\[^\\\s`'\")]+\\)")
SESSION_PATH = re.compile(r"~?/?\.claude/projects/[^\s`'\")]*")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EXAMPLE_DOMAIN = re.compile(r"(^|[@.])example(\.[a-z]+)?$|\.(example|test|invalid|localhost)$")


def gh_json(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def private_repos(owner):
    """owner 계정의 비공개 저장소 이름 목록. 받지 못하면 None."""
    try:
        if not owner:
            owner = gh_json(["api", "user"])["login"]
        repos = gh_json(["repo", "list", owner, "--visibility", "private",
                         "--limit", "1000", "--json", "name"])
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError):
        return None
    return sorted({r["name"] for r in repos}, key=len, reverse=True)


def scan(path, repo_names):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print(f"알림: {path}를 읽지 못했다 ({e})")
        return None
    repo_patterns = repo_name_patterns(repo_names or [])
    hits = []
    for num, line in enumerate(lines, 1):
        for m in HOME_PATH.finditer(line):
            hits.append(("경로", num, m.group(0)))
        for m in SESSION_PATH.finditer(line):
            hits.append(("세션", num, m.group(0)))
        for m in EMAIL.finditer(line):
            addr = m.group(0).lower()
            if "noreply" not in addr and not EXAMPLE_DOMAIN.search(addr):
                hits.append(("이메일", num, m.group(0)))
        seen = set()
        for pattern in repo_patterns:
            for m in pattern.finditer(line):
                if m.start(1) not in seen:
                    seen.add(m.start(1))
                    hits.append(("저장소", num, m.group(1)))
    return hits


def repo_name_patterns(names):
    """저장소 이름을 찾는 정규식 목록.

    하이픈, 밑줄, 점이 든 이름(예: my-notes)은 일반 단어와 겹칠 일이 적어 어디서든 찾는다.
    한 단어 이름(예: spring, admin)은 본문의 일반 단어와 겹치므로,
    저장소로 읽히는 자리에서만 찾는다: 계정/이름, github.com/계정/이름, "이름 저장소".
    """
    distinctive = [n for n in names if re.search(r"[-_.]", n)]
    plain = [n for n in names if n not in distinctive]
    patterns = []
    if distinctive:
        alt = "|".join(re.escape(n) for n in distinctive)
        patterns.append(re.compile(r"(?<![\w.-])(" + alt + r")(?![\w-])"))
    if plain:
        alt = "|".join(re.escape(n) for n in plain)
        patterns.append(re.compile(r"(?<=[\w-]/)(" + alt + r")(?![\w-])"))
        patterns.append(re.compile(r"(?<![\w.-])(" + alt + r")`?\s*(?:저장소|레포|repo)"))
    return patterns


def main(argv):
    owner = None
    files = []
    it = iter(argv)
    for arg in it:
        if arg == "--owner":
            owner = next(it, None)
        else:
            files.append(arg)
    if not files:
        print(__doc__)
        return 2

    repo_names = private_repos(owner)
    if repo_names is None:
        print("알림: 비공개 저장소 목록을 받지 못했다. 저장소 이름 점검은 건너뛴다")

    found = False
    for path in files:
        hits = scan(path, repo_names)
        if hits is None:
            return 2
        for kind, num, text in hits:
            found = True
            print(f"{kind}: {path}:L{num} {text}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

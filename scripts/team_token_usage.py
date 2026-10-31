#!/usr/bin/env python3
"""세션 하나의 토큰 사용량을 에이전트별, 깨어난 회차(wake)별로 합산한다. (#11)

팀 협업 전환 뒤 되돌림이 새 스폰 없이 처리됐는지, 그 비용이 얼마였는지 보는 측정 도구다.
이름 붙인 팀원은 .meta.json의 name으로 나오고, 단발 호출은 (unnamed)로 나온다.
같은 이름이 두 번 나오거나 blog-writer-2 같은 이름이 있으면 대체 스폰이 있었다는 뜻이다.

사용법: python3 team_token_usage.py ~/.claude/projects/{cwd 슬러그}/{세션 ID}

출력
    main: 리드 세션의 합계
    {이름} [{agentType}, model={모델}] wakes={N}: 팀원 하나. wake 2부터가 SendMessage로 깨어난 회차다
      wake {n}: input, cache_creation, cache_read, output 토큰
캐시가 만료된 뒤(기본 5분) 깨어나면 transcript 전체가 cache_creation으로 다시 잡힌다.
사용자를 기다린 뒤의 회차는 따로 본다.
"""

import json
import pathlib
import sys

KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def wakes(path):
    per_prompt, order, seen, current = {}, [], set(), "-"
    for line in open(path):
        d = json.loads(line)
        # promptId는 회차를 여는 user 줄에만 있다. 뒤따르는 assistant 줄은 그 회차에 넣는다.
        current = d.get("promptId") or current
        m = d.get("message")
        if not isinstance(m, dict) or not m.get("usage"):
            continue
        # API 응답 하나가 여러 줄로 나뉘어 기록되므로 id당 한 번만 센다.
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        if current not in per_prompt:
            per_prompt[current] = dict.fromkeys(KEYS, 0)
            order.append(current)
        for k in KEYS:
            per_prompt[current][k] += m["usage"].get(k) or 0
    return [per_prompt[p] for p in order]


def fmt(u):
    return " ".join(f"{k.replace('_input_tokens', '').replace('_tokens', '')}={u[k]}" for k in KEYS)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    session = pathlib.Path(sys.argv[1]).expanduser()
    main_file = session.with_suffix(".jsonl")
    if main_file.exists():
        total = dict.fromkeys(KEYS, 0)
        for u in wakes(main_file):
            for k in KEYS:
                total[k] += u[k]
        print(f"main: {fmt(total)}")
    for f in sorted((session / "subagents").glob("agent-*.jsonl")):
        meta_file = f.with_suffix(".meta.json")
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        rows = wakes(f)
        print(f"{meta.get('name') or '(unnamed)'} [{meta.get('agentType', '?')}, model={meta.get('model', '?')}] "
              f"wakes={len(rows)} file={f.name}")
        for i, u in enumerate(rows, 1):
            print(f"  wake {i}: {fmt(u)}")


if __name__ == "__main__":
    main()

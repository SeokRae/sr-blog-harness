# sr-blog-harness

> `~/IdeaProjects/blog`(SeokRae/blog, Jekyll + Type Theme) 전용 블로그 글쓰기 **파이프라인 하네스** — 근거 수집부터 발행까지 조율하는 Claude Code 플러그인.

주제 하나를 던지면 근거 수집(researcher) → 초안 작성(writer) → 사실 검증(verifier) → 윤문(editor) → 발행(publisher)까지 순차로 이어받아 처리한다. 각 단계는 전용 서브 에이전트가 맡고, 산출물은 `_drafts/{slug}.md`(+`.research.md`)를 거쳐 `_posts/`로 옮겨진다.

이 하네스는 범용이 아니라 `~/IdeaProjects/blog` 한 저장소를 대상으로 만들어졌다 — 경로·레포·발행 정책이 하드코딩돼 있다.

## 파이프라인

| 단계 | 서브 에이전트 | 역할 | 산출물 |
|------|--------------|------|--------|
| 0.5 근거 수집 | `blog-researcher` | 내부(코드·git log) 1차 + 외부 2차 근거 수집 | `_drafts/{slug}.research.md` |
| 1 초안 작성 | `blog-writer` | 리서치 노트를 근거로 초안 작성 | `_drafts/{slug}.md` |
| 1.5 사실 검증 | `blog-verifier` | `(확인 필요)` 플래그 확정/교정/확인불가 처리 | 초안 in-place + 노트 `## 검증 기록` |
| 2 윤문 | `blog-editor` | 가독성·문장 구조 다듬기 (사실/코드는 불변) | 초안 in-place |
| 3 발행 | `blog-publisher` | frontmatter 보완 → `_posts/` 이동 → Issue→feature 브랜치→PR | `_posts/{date}-{slug}.md` + PR |

발행은 Issue → feature 브랜치 → PR(`Closes #N`)까지만 자동화한다. **main 직접 push·자동 merge는 하지 않는다 — merge는 사용자가 한다.**

writer와 editor는 문단 배열 규칙(연쇄, 정박, 우산, 예고)을 공유 계약으로 씁니다. writer가 설계하고 editor가 [`scripts/cohesion_check.py`](scripts/cohesion_check.py)로 점검 재료를 뽑아 판단하며, 결과는 리서치 노트의 `## 응집 점검 기록`에 남습니다. 스크립트는 판정자가 아니라 어디를 볼지 좁혀 주는 보조 도구예요. 근거와 체크리스트는 [`skills/blog-pipeline/references/paragraph-cohesion.md`](skills/blog-pipeline/references/paragraph-cohesion.md)에 있습니다.

## 설치

```
/plugin marketplace add SeokRae/sr-blog-harness
/plugin install sr-blog-harness@sr-blog-harness
```

## 사용

`~/IdeaProjects/blog`에서(또는 플러그인이 전역 활성화된 세션에서):

- "블로그에 'OO' 주제로 글 써줘" → 전체 파이프라인 실행
- "리서치만 다시" / "윤문만 다시" / "검증만 다시" / "발행만 다시" → 해당 단계만 재실행
- 이미 초안이 있으면 근거 수집·작성 단계를 건너뛰고 검증부터 시작

세부 흐름·에러 핸들링은 [`skills/blog-pipeline/SKILL.md`](skills/blog-pipeline/SKILL.md) 참고.

## 출처

원래 `~/IdeaProjects/blog` 저장소의 `.claude/agents`, `.claude/skills/blog-pipeline`으로 프로젝트 로컬에 있던 것을 이 플러그인으로 이관했다 (2026-07-29).

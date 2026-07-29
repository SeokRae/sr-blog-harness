---
name: blog-pipeline
description: "블로그(~/IdeaProjects/blog, SeokRae/blog) 포스트 작성부터 발행까지 파이프라인을 조율하는 오케스트레이터. '블로그 글 써줘', '포스트 작성해줘', '블로그에 올려줘', '블로그 발행해줘', '이 글 블로그에 올려줘' 요청 시 사용. 후속 작업 — '초안 다시 써줘', '리서치만 다시', '윤문만 다시', '검증만 다시', '발행만 다시', '이전 초안 이어서 발행' 요청 시에도 반드시 이 스킬을 사용한다."
---

# Blog Pipeline Orchestrator

`~/IdeaProjects/blog` (Jekyll + Type Theme, https://seokrae.github.io/blog/) 포스트를 아이디어부터 발행까지 조율하는 오케스트레이터.

## 실행 모드: 서브 에이전트

파이프라인 각 단계가 파일(초안 md)을 순차적으로 넘겨받는 구조라 실시간 팀 통신이 필요 없다. `Agent` 도구로 각 단계를 순서대로 호출한다.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 출력 |
|---------|---------------|------|------|
| blog-researcher | blog-researcher (커스텀) | 주제 → 근거 수집 (내부 1차·외부 2차) | `_drafts/{slug}.research.md` |
| blog-writer | blog-writer (커스텀) | 근거 노트 → 초안 작성 | `_drafts/{slug}.md` |
| blog-verifier | blog-verifier (커스텀) | `(확인 필요)` 플래그·사실 검증 | `_drafts/{slug}.md` (in-place) + `_drafts/{slug}.research.md`의 `## 검증 기록` |
| blog-editor | blog-editor (커스텀) | 초안 윤문 | `_drafts/{slug}.md` (in-place) |
| blog-publisher | blog-publisher (커스텀) | 발행 검증 + git push + 배포 확인 | `_posts/{date}-{slug}.md` + 배포 URL |

모든 Agent 호출에 `model: "opus"`를 명시한다.

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `~/IdeaProjects/blog/_drafts/`에 기존 미완성 초안이 있는지, 또는 사용자 요청에 초안 파일 경로가 포함되어 있는지 확인한다
2. 분기:
   - **초안 없음 + 주제만 제공** → Phase 0.5(근거 수집)부터 전체 실행
   - **초안 있음** (사용자가 직접 쓴 글 또는 이전 세션 산출물) → researcher·writer를 건너뛰고 Phase 1.5(검증)부터 시작 (플래그가 없으면 verifier가 빠르게 통과 후 editor로)
   - **부분 재실행 요청** ("리서치만 다시"/"윤문만 다시"/"검증만 다시"/"발행만 다시") → 해당 단계만 호출

### Phase 0.5: 근거 수집

`Agent(prompt: "{주제/키워드/참고자료}", subagent_type: "blog-researcher", model: "opus")`
→ 결과: `_drafts/{slug}.research.md` + 잠정 slug. 이 slug를 Phase 1 writer 호출에 그대로 넘겨 초안 파일과 짝을 맞춘다.
→ 내부 근거가 저장소·제공 경로에 전혀 없다고 보고되면, 외부 근거만으로 진행할지 사용자에게 확인한다.

### Phase 1: 초안 작성 (필요 시)

`Agent(prompt: "{주제/키워드/참고자료} · 리서치 노트: _drafts/{slug}.research.md", subagent_type: "blog-writer", model: "opus")`
→ 결과: `_drafts/{slug}.md` (리서치 노트가 있으면 그것을 1차 근거로 삼아 작성)

### Phase 1.5: 사실 검증

`Agent(prompt: "_drafts/{slug}.md 검증 (리서치 노트: _drafts/{slug}.research.md)", subagent_type: "blog-verifier", model: "opus")`
→ `(확인 필요)` 플래그를 확정/오류교정/확인불가로 처리한 초안(in-place) + **리서치 노트의 `## 검증 기록` 절**(확정 포함 전 항목) + 검증 요약(확정 N·교정 N·확인불가 N).
→ **"확인 불가" 항목이 남으면 사용자에게 반드시 보고하고, 그대로 진행할지 확인한다.** 검증 없이 자동으로 윤문으로 넘어가지 않는다.
→ **근거 사슬 게이트**: 본문의 외부 인용(논문·DOI·통계·표준·외부 도구 동작)이 전부 리서치 노트의 검증 기록에 있는지 확인한다. 빠진 게 있으면 verifier를 다시 돌린다 — 인용이 맞더라도 되짚을 수 없으면 발행 불가다. 초안의 `<!-- 검증: -->` 주석은 발행 시 제거되므로 근거 사슬로 치지 않는다 (#16).

### Phase 2: 윤문

`Agent(prompt: "_drafts/{slug}.md 윤문", subagent_type: "blog-editor", model: "opus")`
→ 윤문된 초안을 사용자에게 보여주고 확인받는다. **발행 전 필수 체크포인트다 — 승인 없이 자동으로 다음 단계로 넘어가지 않는다.**

### Phase 3: 발행

사용자가 승인하면:
`Agent(prompt: "_drafts/{slug}.md 발행", subagent_type: "blog-publisher", model: "opus")`
→ 결과: 내부 주석 정리(작성자·편집자·검증 노트 제거) → `_posts/`로 이동 → **Issue 생성 → main에서 feature 브랜치 분기 → 커밋 → PR(`Closes #N`) 생성**. main 직접 push·자동 merge는 하지 않는다 — **merge는 사용자가 한다.**
→ merge가 완료되면 Pages 빌드·배포 URL을 확인해 보고한다(merge 전이면 PR URL 보고 후 대기).
→ 본문에 `(확인 필요)` 미해소 마커가 남아 있으면 publisher가 발행을 멈추고 보고한다.

### Phase 4: 결과 보고

- PR URL·Issue 번호를 보고하고, 사용자에게 merge를 안내한다 (자동 merge하지 않음)
- merge 후에는 최종 배포 URL·Pages 빌드 확인 결과·걸린 시간을 요약 보고한다
- 문제가 발생했으면 어느 단계에서 멈췄는지와 남은 산출물 경로를 명시한다

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| researcher 내부 근거 없음 | 실패가 아니다 — 외부 근거만으로 진행할지 사용자에게 확인 후 계속 |
| verifier "확인 불가" 잔존 | 발행 전 사용자에게 목록으로 보고. 그대로 낼지·수정할지 확인받기 전엔 진행하지 않음 |
| researcher/writer/verifier/editor 실패 | 1회 재시도. 재실패 시 부분 산출물(있다면)과 함께 사용자에게 보고, 수동 개입 요청 |
| publisher 로컬 빌드 실패 | 절대 자동으로 push/PR하지 않는다 — 에러 로그 보고 후 사용자 확인 대기 |
| publisher Pages 빌드 실패 | merge가 이미 된 상태이므로 에러 로그를 보고하고 재발행(새 PR) 여부를 사용자에게 확인 |

## 테스트 시나리오

### 정상 흐름
1. 사용자가 "블로그에 'Jekyll Chirpy 세팅기' 주제로 글 써줘" 요청
2. Phase 0: `_drafts/`에 기존 초안 없음 → 전체 실행
3. Phase 0.5: blog-researcher가 `_drafts/jekyll-chirpy-setup.research.md` 생성 (slug 확정)
4. Phase 1: blog-writer가 리서치 노트를 근거로 `_drafts/jekyll-chirpy-setup.md` 생성
5. Phase 1.5: blog-verifier가 `(확인 필요)` 플래그 검증, "확인 불가" 없으면 통과
6. Phase 2: blog-editor가 윤문, 사용자에게 확인 요청
7. 사용자 승인 → Phase 3: blog-publisher가 `_posts/2026-07-07-jekyll-chirpy-setup.md`로 이동, Issue→feature 브랜치→PR 생성 (merge는 사용자)
8. 사용자 merge → Phase 4: Pages 빌드 확인, 배포 URL과 함께 완료 보고

### 에러 흐름
1. Phase 3에서 로컬 `jekyll build` 실패 (frontmatter 오류)
2. blog-publisher가 에러 로그와 함께 중단, push하지 않음
3. 오케스트레이터가 사용자에게 에러 내용과 `_drafts/{slug}.md` 경로를 보고
4. 사용자가 수정 후 "발행만 다시" 요청 → Phase 3부터 재실행

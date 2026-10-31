---
name: blog-pipeline
description: "블로그(~/IdeaProjects/blog, SeokRae/blog) 포스트 작성부터 발행까지 파이프라인을 조율하는 오케스트레이터. '블로그 글 써줘', '포스트 작성해줘', '블로그에 올려줘', '블로그 발행해줘', '이 글 블로그에 올려줘' 요청 시 사용. 후속 작업 — '초안 다시 써줘', '리서치만 다시', '윤문만 다시', '검증만 다시', '발행만 다시', '이전 초안 이어서 발행' 요청 시에도 반드시 이 스킬을 사용한다."
---

# Blog Pipeline Orchestrator

`~/IdeaProjects/blog` (Jekyll + Type Theme, https://seokrae.github.io/blog/) 포스트를 아이디어부터 발행까지 조율하는 오케스트레이터.

## 실행 모드: 팀 협업

리드는 이 스킬을 실행하는 메인 세션입니다. writer, verifier, editor는 `Agent(name: ...)`으로 이름을 붙여 띄운 팀원이고, 앞 단계로 되돌아가는 구간은 `SendMessage`로 주고받아요. 이름 붙인 에이전트는 끝난 뒤에도 이름으로 깨울 수 있고, 깨우면 자기 transcript에서 이어 갑니다. 그래서 되돌림마다 초안과 리서치 노트를 처음부터 다시 읽지 않아요. 단계 순서는 아래 워크플로우의 스폰 시점으로 정하고, 공유 작업 목록은 쓰지 않습니다.

## 에이전트 구성

| 단계 | subagent_type | 호출 | 역할 | 출력 |
|------|---------------|------|------|------|
| 0.5 근거 수집 | `sr-blog-harness:blog-researcher` | 단발 | 주제 → 근거 수집 (내부 1차·외부 2차) | `_drafts/{slug}.research.md` |
| 1 초안 | `sr-blog-harness:blog-writer` | 팀원 `blog-writer` | 근거 노트 → 초안 작성, 되돌림 요청 수정 | `_drafts/{slug}.md` |
| 1.5 검증 | `sr-blog-harness:blog-verifier` | 팀원 `blog-verifier` | `(확인 필요)` 플래그·사실 검증 | `_drafts/{slug}.md` (in-place) + `_drafts/{slug}.research.md`의 `## 검증 기록` |
| 2 윤문 | `sr-blog-harness:blog-editor` | 팀원 `blog-editor` | 초안 윤문 + 문단 응집 점검 | `_drafts/{slug}.md` (in-place) + `_drafts/{slug}.research.md`의 `## 응집 점검 기록` (노트가 없으면 만든다) |
| 3 발행 | `sr-blog-harness:blog-publisher` | 단발 | 발행 검증 + git push + 배포 확인 | `_posts/{date}-{slug}.md` + 배포 URL |

researcher와 publisher는 이름 없는 단발 호출로 남깁니다.

- **researcher**: 되돌림을 받는 구간이 없습니다. 노트는 뒤에서 verifier와 editor가 절을 덧붙이는 파일이라, 깨울 수 있는 researcher가 남아 있으면 같은 파일을 고칠 수 있는 주체만 늘어나요. "리서치만 다시"는 새 단발 호출로 충분합니다.
- **publisher**: 사용자 승인 뒤 한 번 돕니다. push와 PR 생성은 밖으로 나가는 동작이라, 늦게 도착한 메시지로 다시 깨어날 수 있는 이름을 주지 않아요. 발행을 멈추는 사유(미해소 마커, 근거 사슬 누락, 빌드 실패)는 publisher 안에서 고칠 일이 아니라 리드가 사용자나 verifier로 돌릴 일입니다.

Agent 호출에 `model`을 넣지 않는다. 팀원과 단발 호출 모두 세션 모델을 상속한다. 에이전트별 모델은 팀 전환 전후의 토큰 비교를 마친 뒤 정한다 (#11).

## 공유 규칙: 문단 응집

문단 배열 규칙(연쇄, 정박, 우산, 예고)은 한 에이전트의 취향이 아니라 **네 단계를 관통하는 계약**입니다. 소주제 이름이 그 계약을 나르는 물건이에요.

| 단계 | 소주제 이름을 어떻게 다루나 |
|------|---------------------------|
| researcher | 인사이트 후보를 2~4개로 묶어 이름을 짓고 노트의 `## 소주제 이름 후보`에 표기를 확정한다 |
| writer | 그 이름으로 도입부에서 예고하고 소제목에 쓴다. 초안 하단에 `<!-- 작성자 노트: 소주제 이름 = A \| B \| C -->`를 남기고, `cohesion_check.py`로 자기 점검한다 |
| verifier | 이름 표기를 바꾸지 않는다. 표기가 사실로 틀렸을 때만 본문과 주석을 함께 고치고 보고한다 |
| editor | `scripts/cohesion_check.py`로 대조하고, 결과를 노트의 `## 응집 점검 기록`에 남긴다 |
| publisher | 발행 시 `<!-- 작성자 노트 -->`를 제거하므로 독자에게는 노출되지 않는다 |

이 사슬이 끊기면 증상은 하나로 나타납니다. 도입부가 예고한 것과 본문 소제목이 다른 글이 나가요. 근거와 점검 체크리스트, 그리고 기존 규칙(AI 문투 배제, 내용 불변, 인사이트 컨셉)과 충돌하는 지점의 해소안은 [`references/paragraph-cohesion.md`](references/paragraph-cohesion.md)에 있습니다. 각 에이전트 정의에 필요한 요약이 들어 있으므로 평소에는 따로 읽히지 않아도 되고, 규칙을 고칠 때 이 파일이 기준입니다.

## 팀 통신

### 스폰 프롬프트

팀원 프롬프트에는 파일 경로와 아래 두 줄만 넣는다. 앞 팀원의 완료 보고나 작성 의도는 넘기지 않는다. verifier는 fork가 아닌 새 에이전트로 띄운다.

- `되돌림 대상: blog-writer` (Phase 1에서 writer를 띄웠을 때) 또는 `되돌림 대상: main` (초안 있음 경로)
- `보고: main`

### 되돌림 경로

| 구간 | 보내는 쪽 → 받는 쪽 | 보내는 것 | 회차를 닫고 기록하는 쪽 |
|------|-------------------|----------|----------------------|
| 사실 교정 | blog-verifier → blog-writer | 문장 하나로 못 고치는 주장 | blog-verifier |
| 근거 사슬 | main → blog-verifier | 검증 기록에 없는 외부 인용, writer가 되돌림 중 새로 넣은 사실 문장 | blog-verifier |
| 배열 | blog-editor → blog-writer | 문단 안 정보로 못 쓰는 우산 문장 | blog-editor |
| 사용자 결정 | main → blog-writer | 확인 불가 항목과 편집자 노트 중 사용자가 정한 처리 | blog-editor (재점검) |

- 보내는 쪽은 자기 수정을 다 끝낸 뒤 보내고, 회신이 올 때까지 초안을 고치지 않는다. 한 번에 초안을 고치는 팀원은 하나다
- 받는 쪽은 고친 뒤 보낸 쪽에 재확인을 요청한다. 사용자 결정만 main으로 회신하고, 리드가 `새 사실: 있음` 줄을 근거 사슬로 verifier에 보낸 다음 editor에 `[사용자 결정 {n}회차 재점검]`을 보낸다
- 구간마다 최대 2회. 그래도 남은 항목과 writer가 `못 고침`으로 답한 항목은 기록하는 쪽이 main에 `[중단]`으로 올리고, 리드가 사용자에게 보인다
- writer가 없는 초안 있음 경로에서는 writer 쪽 항목이 main으로 온다. 초안에 `<!-- 작성자 노트`가 있으면 이전 파이프라인이 쓴 초안이니, 리드가 그때 `blog-writer`를 처음 띄워 받은 항목과 회신할 팀원을 넘긴다. 없으면 사용자가 쓴 초안이니 항목을 사용자에게 보이고, 정한 대로 리드가 고친 뒤 보낸 팀원에게 재확인을 요청한다

### 메시지 형식

```
[{구간} {n}회차] {보내는 쪽} → {받는 쪽}
- {파일}:{줄} | 현재: {본문 진술} | 근거: {출처와 그 출처가 말하는 것} | 기대: {바뀌어야 할 모습}

[재확인 요청 {구간} {n}회차] {받는 쪽} → {보내는 쪽}
- {파일}:{줄} | 처리: 고침 또는 못 고침({이유}) | 새 사실: 있음 또는 없음
```

main에 보내는 보고는 첫 줄에 `[완료]`(단계 끝) 또는 `[중단]`(사용자 판단 필요)을 단다. 리드는 이 두 태그만 단계 전환 신호로 쓴다. 회신을 기다리며 턴을 끝내는 팀원은 main에 보내지 않고, 마지막 응답 첫 줄에 `[대기] {상대}`만 쓴다.

### 되돌림 기록

회차를 닫는 팀원이 `_drafts/{slug}.research.md`의 `## 되돌림 기록` 절에 한 줄씩 남긴다(절이 없으면 만든다). publisher가 노트를 포스트와 함께 커밋하므로 기록이 저장소에 남는다.

```
- {구간} {n}회차 | {보내는 쪽} → {받는 쪽} | 항목 {N}건 | 해소 {N}, 남음 {N} | {줄 목록}
```

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `~/IdeaProjects/blog/_drafts/`에 기존 미완성 초안이 있는지, 또는 사용자 요청에 초안 파일 경로가 포함되어 있는지 확인한다
2. 분기:
   - **초안 없음 + 주제만 제공** → Phase 0.5(근거 수집)부터 전체 실행
   - **초안 있음** (사용자가 직접 쓴 글 또는 이전 세션 산출물) → researcher·writer를 건너뛰고 Phase 1.5(검증)부터 시작 (플래그가 없으면 verifier가 빠르게 통과 후 editor로). 팀원 프롬프트의 되돌림 대상은 main이다
   - **부분 재실행 요청** ("리서치만 다시"/"윤문만 다시"/"검증만 다시"/"발행만 다시") → 해당 단계만 호출. 같은 세션에 그 팀원이 남아 있으면 `SendMessage`로 다시 시키고, 없으면 새로 띄운다

### Phase 0.5: 근거 수집

`Agent(prompt: "{주제/키워드/참고자료}", subagent_type: "sr-blog-harness:blog-researcher")` (단발, `name` 없음)
→ 결과: `_drafts/{slug}.research.md` + 잠정 slug. 이 slug를 Phase 1 writer 호출에 그대로 넘겨 초안 파일과 짝을 맞춘다.
→ 노트의 `## 소주제 이름 후보`(2~4개)를 사용자에게 함께 보여준다. 글의 뼈대가 여기서 정해지므로, 이름이 어색하면 이 단계에서 잡는 편이 윤문 단계에서 되돌리는 것보다 싸다.
→ 내부 근거가 저장소·제공 경로에 전혀 없다고 보고되면, 외부 근거만으로 진행할지 사용자에게 확인한다.

### Phase 1: 초안 작성 (필요 시)

`Agent(name: "blog-writer", subagent_type: "sr-blog-harness:blog-writer", prompt: "{주제/키워드/참고자료}\n리서치 노트: _drafts/{slug}.research.md\n보고: main")`
→ 결과: `_drafts/{slug}.md` (리서치 노트가 있으면 그것을 1차 근거로 삼아 작성). `[완료]`를 받으면 Phase 1.5로 간다.
→ writer가 저장 직후 `scripts/cohesion_check.py`로 배열을 자기 점검한다. 예고 사슬과 정박 한도, 우산 문장만 본다. 문장 다듬기는 editor의 몫이다.

### Phase 1.5: 사실 검증

`Agent(name: "blog-verifier", subagent_type: "sr-blog-harness:blog-verifier", prompt: "_drafts/{slug}.md 검증\n리서치 노트: _drafts/{slug}.research.md\n되돌림 대상: {blog-writer 또는 main}\n보고: main")`
→ `(확인 필요)` 플래그를 확정/오류교정/확인불가로 처리한 초안(in-place) + **리서치 노트의 `## 검증 기록` 절**(확정 포함 전 항목) + 검증 요약(확정 N·교정 N·확인불가 N).
→ 문장 하나로 못 고치는 주장은 verifier가 writer에게 사실 교정으로 보내고, 재확인까지 마친 뒤 `[완료]`를 보낸다.
→ **"확인 불가" 항목이 남으면 사용자에게 반드시 보고하고, 그대로 진행할지 확인한다.** 검증 없이 자동으로 윤문으로 넘어가지 않는다. 사용자가 고치라고 정한 항목은 사용자 결정 회차로 writer에게 보낸다.
→ **근거 사슬 게이트**: 본문의 외부 인용(논문·DOI·통계·표준·외부 도구 동작)이 전부 리서치 노트의 검증 기록에 있는지 확인한다. 빠진 게 있으면 `SendMessage(to: "blog-verifier")`로 빠진 인용 목록을 근거 사슬 회차로 보낸다. 인용이 맞더라도 되짚을 수 없으면 발행 불가다. 초안의 `<!-- 검증: -->` 주석은 발행 시 제거되므로 근거 사슬로 치지 않는다 (#16).

### Phase 2: 윤문

`Agent(name: "blog-editor", subagent_type: "sr-blog-harness:blog-editor", prompt: "_drafts/{slug}.md 윤문\n리서치 노트: _drafts/{slug}.research.md\n되돌림 대상: {blog-writer 또는 main}\n보고: main")`
→ 윤문된 초안을 사용자에게 보여주고 확인받는다. **발행 전 필수 체크포인트다 — 승인 없이 자동으로 다음 단계로 넘어가지 않는다.**
→ editor의 **문단 응집 점검 결과**(예고 사슬 일치 여부, 배열을 손본 문단 수, 유지 판단 수, 편집자 노트 수)를 함께 보고한다. 점검 근거는 `_drafts/{slug}.research.md`의 `## 응집 점검 기록`에 남는다. "우산 문장 필요"나 예고 이름 불일치가 노트로 남아 있으면 목록으로 보여준다. editor는 새 사실을 만들어 넣지 않으므로 이 항목들은 사용자가 결정한다.
→ editor 보고에 writer가 배열 회차에서 넣은 `새 사실: 있음` 줄이 있으면, 승인을 요청하기 전에 근거 사슬 회차로 verifier에게 보낸다.
→ 사용자가 편집자 노트 처리를 정하면 사용자 결정 회차로 `SendMessage(to: "blog-writer")`에 보내고, 재점검까지 끝난 초안으로 다시 승인을 받는다.
→ 승인되면 `shasum _drafts/{slug}.md _drafts/{slug}.research.md` 값을 남긴다. 팀원은 승인 뒤에도 깨어날 수 있으므로, Phase 3 직전에 다시 계산해 승인한 내용 그대로인지 확인한다.

### Phase 3: 발행

사용자가 승인하고 해시가 그대로면:
`Agent(prompt: "_drafts/{slug}.md 발행", subagent_type: "sr-blog-harness:blog-publisher")` (단발, `name` 없음)
→ 결과: 내부 주석 정리(작성자·편집자·검증 노트 제거) → `_posts/`로 이동 → **Issue 생성 → main에서 feature 브랜치 분기 → 커밋 → PR(`Closes #N`) 생성**. main 직접 push·자동 merge는 하지 않는다 — **merge는 사용자가 한다.**
→ merge가 완료되면 `Agent(prompt: "배포 확인: {PR URL}", subagent_type: "sr-blog-harness:blog-publisher")`를 한 번 더 불러 Pages 빌드와 배포 URL을 확인해 보고한다(merge 전이면 PR URL 보고 후 대기).
→ 본문에 `(확인 필요)` 미해소 마커가 남아 있으면 publisher가 발행을 멈추고 보고한다.
→ 빌드 뒤 `scripts/asset_check.py`로 포스트가 참조하는 저장소 파일을 점검한다. `미추적` 파일은 포스트와 같은 커밋에 넣고, `없음`(깨진 참조)이 나오면 발행을 멈추고 보고한다. 그림 형태와 계약은 [`references/figure-embed.md`](references/figure-embed.md)에 있다 (#7).

### Phase 4: 결과 보고

- PR URL·Issue 번호를 보고하고, 사용자에게 merge를 안내한다 (자동 merge하지 않음)
- merge 후에는 최종 배포 URL·Pages 빌드 확인 결과·걸린 시간을 요약 보고한다
- 문제가 발생했으면 어느 단계에서 멈췄는지와 남은 산출물 경로를 명시한다

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| researcher 내부 근거 없음 | 실패가 아니다 — 외부 근거만으로 진행할지 사용자에게 확인 후 계속 |
| verifier "확인 불가" 잔존 | 발행 전 사용자에게 목록으로 보고. 그대로 낼지·수정할지 확인받기 전엔 진행하지 않음. 수정은 사용자 결정 회차로 writer에게 |
| editor 예고 사슬 불일치 보고 | 도입부 예고와 소제목이 어긋난 상태다. 어느 쪽 이름이 맞는지 사용자에게 확인한다. editor가 임의로 통일했다면 그 사실도 함께 보고된다. 사용자가 정한 이름은 사용자 결정 회차로 writer에게 |
| 되돌림 2회 뒤에도 남음, writer `못 고침` | 기록하는 팀원이 `[중단]`으로 보고한다. 리드는 남은 항목을 사용자에게 목록으로 보이고, 사용자가 정한 처리를 사용자 결정 회차로 보낸다 |
| `[대기]` 뒤 상대 회신 없이 멈춤 | 상대 팀원에게 `SendMessage`로 받은 요청을 이어서 처리하라고 한 번 보낸다. 그래도 멈추면 아래 팀원 실패로 처리 |
| researcher 실패 | 단발 호출을 1회 다시 한다. 재실패 시 부분 산출물(있다면)과 함께 사용자에게 보고, 수동 개입 요청 |
| writer/verifier/editor 실패 | 같은 이름에 `SendMessage`로 이어서 하라고 1회 보낸다. 그래도 안 되면 `blog-writer-2`처럼 새 이름으로 띄우고 초안과 노트 경로를 넘긴다(새 팀원은 `## 되돌림 기록`부터 읽는다). 재실패 시 부분 산출물과 함께 사용자에게 보고 |
| 사용량 한도, 인증 만료, 권한 거부로 멈춤 | 다시 보내도 결과가 같으니 재시도하지 않는다. 초안과 노트를 열어 어디까지 됐는지 확인하고 사용자에게 보고한다. 한도라면 풀리는 시각도 함께 |
| Phase 3 직전 해시 불일치 | 승인 뒤 초안이나 노트가 바뀌었다. 바뀐 부분을 사용자에게 보이고 다시 승인받는다 |
| publisher 미해소 마커, 근거 사슬 누락으로 중단 | 사용자에게 보고한다. 진행하기로 하면 `blog-verifier`가 세션에 있으면 `SendMessage`로, 없으면 새로 띄워 Phase 1.5로 되돌리고, 고친 뒤 승인 체크포인트를 다시 거친다 |
| publisher 로컬 빌드 실패 | 절대 자동으로 push/PR하지 않는다 — 에러 로그 보고 후 사용자 확인 대기 |
| publisher Pages 빌드 실패 | merge가 이미 된 상태이므로 에러 로그를 보고하고 재발행(새 PR) 여부를 사용자에게 확인 |

## 테스트 시나리오

### 정상 흐름
1. 사용자가 "블로그에 'Jekyll Chirpy 세팅기' 주제로 글 써줘" 요청
2. Phase 0: `_drafts/`에 기존 초안 없음 → 전체 실행
3. Phase 0.5: blog-researcher 단발 호출이 `_drafts/jekyll-chirpy-setup.research.md` 생성 (slug 확정)
4. Phase 1: 팀원 `blog-writer`가 리서치 노트를 근거로 `_drafts/jekyll-chirpy-setup.md` 생성, `[완료]`
5. Phase 1.5: 팀원 `blog-verifier`가 플래그를 검증한다. 문장 하나로 못 고치는 주장 1건을 `blog-writer`에게 사실 교정 1회차로 보내고, writer의 재확인 요청을 받아 확인한 뒤 `## 되돌림 기록`에 남기고 `[완료]`
6. 리드의 근거 사슬 게이트에서 인용 1건이 검증 기록에 없음 → `SendMessage(to: "blog-verifier")` → 기록 추가 후 `[완료]`
7. Phase 2: 팀원 `blog-editor`가 윤문하고, 재료가 없는 우산 문장 1곳을 `blog-writer`에게 배열 1회차로 보낸다. 재점검 뒤 `[완료]`, 리드가 사용자에게 확인 요청
8. 사용자 승인 → 해시 기록 → Phase 3: blog-publisher 단발 호출이 `_posts/2026-07-07-jekyll-chirpy-setup.md`로 이동, Issue→feature 브랜치→PR 생성 (merge는 사용자)
9. 사용자 merge → 배포 확인 단발 호출 → Phase 4: 배포 URL과 함께 완료 보고
10. 확인: 세션의 subagents transcript에 `blog-writer`, `blog-verifier`, `blog-editor`가 하나씩만 있고, 노트의 `## 되돌림 기록`에 세 회차가 있다

### 에러 흐름
1. Phase 3에서 로컬 `jekyll build` 실패 (frontmatter 오류)
2. blog-publisher가 에러 로그와 함께 중단, push하지 않음
3. 오케스트레이터가 사용자에게 에러 내용과 `_drafts/{slug}.md` 경로를 보고
4. 사용자가 수정 후 "발행만 다시" 요청 → Phase 3부터 재실행 (새 단발 호출, 기존 Issue가 있으면 이어서 쓴다)

### 되돌림 중 팀원 멈춤
1. Phase 1.5 사실 교정 1회차를 받은 `blog-writer`가 오류로 멈추고, `blog-verifier`는 `[대기] blog-writer` 상태다
2. 리드가 `SendMessage(to: "blog-writer")`로 받은 요청을 이어서 처리하라고 보낸다
3. writer가 자기 transcript에서 이어 고치고 `blog-verifier`에게 재확인을 요청한다. 새 스폰은 없다

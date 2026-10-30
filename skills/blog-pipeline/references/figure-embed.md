# 그림 임베드 레퍼런스

블로그 포스트에 그림을 넣을 때의 형태와 계약입니다. 그림을 넣을지는 사용자가 정해요. 이 문서는 넣기로 정한 뒤에 씁니다. `blog-writer`가 그림 자리를 잡을 때, `blog-publisher`가 발행 직전에 확인할 때 읽습니다.

이슈 번호는 따로 적지 않으면 블로그 저장소(SeokRae/blog)의 것입니다.

## 공통 계약

블로그 저장소의 계약 테스트와 테마 구조에서 오는 조건입니다. 형태와 무관하게 지킵니다.

- **외부 요청 0.** `test/site_output_test.rb`의 `assert_no_external_requests`가 `_site/**/*.html` 전체에서 외부 스타일시트와 스크립트를 찾습니다(블로그 #24, #125). `assets/` 아래의 정적 HTML도 `_site`로 그대로 복사되므로 같은 검사를 받아요. mermaid CDN이나 웹폰트 `<link>`는 쓸 수 없습니다.
- **테마는 `<html data-theme>`가 정합니다.** `_includes/head.html`이 로드할 때 `light`나 `dark`를 넣고, 헤더의 토글 버튼이 런타임에 값을 바꿉니다. 그림의 다크 모드는 이 속성을 기준으로 맞춰요.
- **참조한 파일은 포스트와 같은 커밋에 넣습니다.** 로컬 `jekyll build`는 작업 트리를 읽으므로 커밋하지 않은 파일도 빌드에 들어가 통과합니다. 포스트만 커밋하면 Pages 빌드에서는 그 파일이 없어 404가 나요. 아래 [publisher 점검](#publisher-점검)이 이걸 잡습니다.

## 형태 1: 인라인 SVG

정적 그림(flowcast sequence, component, topology가 만든 SVG)이나 CSS 애니메이션 SVG에 씁니다. `<figure>`를 포스트 본문에 통째로 넣는 형태예요. 발행 사례는 flowcast 1편(`.flowcast-embed`, 블로그 #36, #40)과 레이트리미터 편(`.rl-algo-embed`, 블로그 #82)입니다.

```html
<figure class="{이름}-embed">
<style>
.{이름}-embed{margin:2em 0;padding:1.25em;border:1px solid rgba(31,111,208,0.18);border-radius:10px;background:#fbfcfe;--muted:#54667e;--accent:#1f6fd0;}
[data-theme="dark"] .{이름}-embed{background:#0c1524;border-color:rgba(153,186,255,0.14);--muted:#98abc9;--accent:#68b6ff;}
.{이름}-embed svg{max-width:100%;height:auto;}
.{이름}-embed figcaption{margin-top:0.75em;color:var(--muted);font-size:0.85em;text-align:center;}
</style>
<svg viewBox="..." role="img" aria-label="{그림이 보여주는 것}">...</svg>
<figcaption>...</figcaption>
</figure>
```

색 값은 두 발행본이 함께 쓰는 기본 팔레트입니다. 그림에 필요한 변수는 이 두 규칙에 더해요.

- **모든 선택자를 스코프 클래스 아래에 둡니다.** 본문 안의 `<style>`도 페이지 전체에 적용돼요. 레이트리미터 편의 `figcaption{...}`(`_posts/2026-08-09-rate-limiter-payment-platform.md:233`)은 스코프 없이 들어가 있습니다. 그 페이지에 figure가 하나뿐이라 드러나지 않았을 뿐이에요.
- **색은 CSS 변수로만 둡니다.** 블로그 #40 전에는 변수에 라이트 값만 있어 다크 페이지 위에 라이트 패널이 떠 있었습니다. 다크 규칙에서 변수 세트를 덮어쓰자 SVG 전체가 따라왔고, hex를 직접 박아 둔 figcaption만 따로 고쳐야 했어요.
- **다크 팔레트를 새로 고르면 대비를 계산해 남깁니다.** 블로그 #40은 accent 8.47:1, muted 7.84:1처럼 값마다 대비를 기록했습니다. 기본 팔레트를 그대로 쓰면 다시 계산할 필요가 없어요.
- **계약 테스트에 단언을 더하지 않아도 됩니다.** 외부 요청 검사가 생성된 HTML 전체를 훑기 때문입니다(블로그 #125).

## 형태 2: self-contained HTML + iframe

스크립트가 도는 HTML 한 장(flowcast:state-loop, flowcast:mechanism의 출력)에 씁니다. 파일을 `assets/flowcast/`에 두고 iframe으로 띄워요. 아직 발행 사례는 없고, JVM 구동 편(`assets/flowcast/jvm-startup-loop.html`)이 첫 사례가 됩니다.

```html
<figure class="{이름}-embed">
<iframe src="{{ '/assets/flowcast/{이름}.html' | relative_url }}" title="{그림이 보여주는 것}" loading="lazy" style="display:block;width:100%;height:{N}px;border:0;"></iframe>
<figcaption>...</figcaption>
</figure>
```

figcaption 스타일은 형태 1처럼 스코프해서 넣습니다. 이 형태는 파일이 포스트 밖에 따로 있어서 깨지는 곳도 거기서 나와요.

- **파일을 커밋합니다.** `_posts/` 밖에 있어 포스트만 커밋하면 빠집니다. 형태 2에서 가장 먼저 깨지는 곳이에요.
- **생성된 파일은 손으로 고치지 않습니다.** flowcast 산출물은 원본(JSON이나 생성기)을 고쳐 다시 만들고 통째로 바꿉니다. `jvm-startup-loop.html`의 첫 주석도 같은 말을 해요.
- **`title` 속성을 붙입니다.** 스크린리더가 iframe을 부르는 이름입니다.
- **높이를 정해 줍니다.** iframe은 안쪽 내용 높이를 따라가지 않아요. 고정 높이를 주고 모바일 폭에서 잘리지 않는지 봅니다.
- **`scrollIntoView`를 쓰는 HTML은 블로그 페이지를 스크롤시킵니다.** iframe 바깥 문서까지 움직여 읽던 자리가 튀어요. flowcast state-loop 규칙(flowcast #147)이 이걸 막고 있으니, 다른 곳에서 만든 HTML을 넣을 때만 따로 확인합니다.
- **알려진 한계: 테마를 로드할 때 한 번만 읽습니다.** `jvm-startup-loop.html`은 부모 문서의 `data-theme`를 처음 한 번 읽어요(파일 8행). 페이지를 연 뒤 토글로 테마를 바꾸면 iframe은 따라가지 않고, 새로고침해야 맞춰집니다. 블로그 토글 스크립트(`_includes/head.html`)도 iframe에 변경을 알리지 않습니다. 고치려면 flowcast 출력이나 블로그 쪽 이슈로 다뤄요.

## publisher 점검

로컬 빌드가 끝난 뒤 블로그 저장소 루트에서 돌립니다.

```bash
python3 "$(find ~/.claude/plugins -path '*sr-blog-harness*/scripts/asset_check.py' | head -1)" _posts/{date}-{slug}.md
```

스크립트는 링크 대상(`](...)`, `src=`, `href=`)만 봅니다. 그중 `{{ site.baseurl }}/x`, `/blog/x`, `{{ '/x' | relative_url }}` 형태를 사이트 내부 경로로 치고, 외부 URL과 코드 예시는 건너뛰어요.

| 출력 | 뜻 | 처리 |
|------|----|------|
| `미추적: L{n} {path}` | 파일은 저장소에 있으나 git이 모른다 | 포스트와 같은 커밋에 넣는다 |
| `없음: L{n} {path}` | 빌드 결과에도 없다. 깨진 참조다 | 발행을 멈추고 사용자에게 보고한다 |

출력이 없고 exit 0이면 통과입니다.

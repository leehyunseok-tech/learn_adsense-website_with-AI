"""TOC.md 를 보고 한 쪽의 뼈대를 만듭니다.

상자 여섯 종이 미리 들어간 틀이 나옵니다.
내용만 채우면 check_book.py 의 최소 기준을 만족합니다.

    python tools/new_page.py ch01
    python tools/new_page.py ch01 --force     # 이미 있어도 덮어씁니다

TOC.md 에 그 id 가 있어야 합니다. 제목과 절 목록을 거기서 읽습니다.
"""

import html as htmlmod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"

쪽패턴 = re.compile(r"^### \[([^\]]+)\]\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\w+)\s*$")
절패턴 = re.compile(r"^- ((?:\d+|[A-H])\.\d+)\s+(.+)$")
부패턴 = re.compile(r"^## (.+)$")



def ch숫자(쪽id: str) -> bool:
    """ch01 처럼 ch 뒤에 숫자가 오는 것만 본문 장입니다.

    changelog 도 ch 로 시작하기 때문에 접두사만 보면 안 됩니다.
    """
    return re.match(r"^ch\d", 쪽id) is not None

def esc(s: str) -> str:
    return htmlmod.escape(s, quote=False)


def 폴더(쪽id: str) -> str:
    if ch숫자(쪽id):
        return "chapters"
    if 쪽id.startswith("apx-"):
        return "appendix"
    if 쪽id in ("prologue", "howto"):
        return "front"
    return "back"


def 절id(번호: str) -> str:
    return "s" + 번호.replace(".", "-")


def 제목읽기() -> str:
    p = ROOT / "book.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("title", "책")
        except Exception:
            pass
    return "책"


def TOC읽기(찾을id: str):
    현재부 = ""
    for 줄 in TOC.read_text(encoding="utf-8").splitlines():
        b = 부패턴.match(줄)
        if b and not 줄.startswith("## 파싱"):
            현재부 = b.group(1).strip()
            continue
        m = 쪽패턴.match(줄)
        if m:
            찾음 = m.group(1) == 찾을id
            if 찾음:
                return {"제목": m.group(2), "부": 현재부, "절": [], "번호": None}
    return None


def 절들읽기(찾을id: str) -> list[tuple[str, str]]:
    안에 = False
    모음 = []
    for 줄 in TOC.read_text(encoding="utf-8").splitlines():
        m = 쪽패턴.match(줄)
        if m:
            안에 = m.group(1) == 찾을id
            continue
        if 안에:
            s = 절패턴.match(줄)
            if s:
                모음.append((s.group(1), s.group(2)))
    return 모음


머리 = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{쪽제목} — {책제목}</title>
<meta name="description" content="TODO: 이 쪽을 한 문장으로.">
<script>
  try {{
    var t = localStorage.getItem('book:theme');
    if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
  }} catch (e) {{}}
</script>
<link rel="stylesheet" href="../assets/book.css">
</head>
<body class="chapter" data-chapter="{쪽id}" data-part="{부번호}" data-root="../">

<a class="skip-link" href="#main">본문 바로가기</a>

<header class="book-header">
  <button class="icon-btn sidebar-toggle" type="button" data-action="toggle-sidebar"
          aria-expanded="false" aria-label="목차 열기">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
  </button>
  <a class="book-header__brand" href="../index.html">{책제목}</a>
  <span class="book-header__crumb">{부} › {쪽제목}</span>
  <span class="book-header__spacer"></span>
  <div class="book-header__actions">
    <button class="icon-btn" type="button" data-action="toggle-done" aria-pressed="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12l5 5L20 6"/></svg>
      <span class="done-label">읽음 표시</span>
    </button>
    <button class="icon-btn" type="button" data-action="open-search" aria-label="검색 (Ctrl+K)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    </button>
    <button class="icon-btn" type="button" data-action="toggle-theme" aria-label="테마 전환">
      <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>
    </button>
    <button class="icon-btn" type="button" onclick="window.print()" aria-label="인쇄">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V3h12v6M6 18H4v-6h16v6h-2M8 14h8v7H8z"/></svg>
    </button>
  </div>
</header>

<div class="reading-progress"><i></i></div>

<div class="book-layout">

  <!-- BUILD:SIDEBAR:START -->
  <!-- BUILD:SIDEBAR:END -->

  <main class="chapter-body" id="main">

    <div class="chapter-hero">
      <p class="chapter-hero__part">{부}</p>
      <span class="chapter-hero__num">{번호}</span>
      <h1 class="chapter-hero__title">{쪽제목}</h1>
      <p class="chapter-hero__lead">
        TODO: 이 쪽을 왜 읽어야 하는지 두세 문장으로.
        <strong>중요한 부분은 이렇게 강조</strong>합니다.
      </p>
    </div>

    <div class="chapter-meta">
      <span>약 00분</span>
      <span>예제 0개</span>
      <span>연습문제 0문항</span>
    </div>

    <div class="chapter-goals">
      <p class="chapter-goals__title">이 장을 끝내면 할 수 있는 것</p>
      <ul>
        <li>TODO</li>
        <li>TODO</li>
      </ul>
    </div>
"""

절틀 = """
    <!-- ============================================================ -->
    <section class="section" id="{절id}">
      <h2>{번호} {제목}</h2>

      <p>TODO</p>
{상자}
    </section>
"""

상자모음 = """
      <div class="concept">
        <p class="concept__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/></svg>
          <span class="print-label">[개념] </span>TODO 개념 이름
        </p>
        <p>TODO: 정의를 한 문장으로.</p>
      </div>

      <div class="analogy">
        <p class="analogy__title">
          <span class="print-label">[비유] </span>💡 이렇게 생각해 보세요
        </p>
        <div class="analogy__body">
          <p>TODO: 일상적인 것에 빗대세요. <strong>여기서만 구어체</strong>를 씁니다.</p>
        </div>
      </div>

      <div class="pitfall">
        <p class="pitfall__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/></svg>
          <span class="print-label">[주의] </span>TODO 함정 이름
        </p>
        <p>TODO: <strong>에러가 안 나면서 틀리는</strong> 것을 고르세요.</p>
      </div>
"""

두번째상자 = """
      <div class="analogy">
        <p class="analogy__title">
          <span class="print-label">[비유] </span>🔧 이렇게 생각해 보세요
        </p>
        <div class="analogy__body">
          <p>TODO: 두 번째 비유입니다. 새 개념마다 하나씩 넣으십시오.</p>
        </div>
      </div>

      <figure class="figure" id="fig-{쪽번호}-1">
        <svg viewBox="0 0 660 260" role="img" aria-labelledby="f1t f1d">
          <title id="f1t">TODO 그림 제목</title>
          <desc id="f1d">TODO 그림이 무엇을 보여주는지 글로 설명합니다.</desc>
          <rect x="24" y="40" width="180" height="70" rx="10"
                fill="var(--fig-surface)" stroke="var(--fig-line)" stroke-width="1.8"/>
          <text x="114" y="80" text-anchor="middle" font-size="13"
                fill="var(--fig-text)" font-weight="700">TODO</text>
          <text x="24" y="180" font-size="12" fill="var(--fig-text-soft)">
            색은 var(--fig-*) 만 쓰십시오. 그래야 다크 모드와 인쇄가 자동입니다.
          </text>
        </svg>
        <figcaption class="figure__caption">
          <strong>그림 {쪽번호}-1</strong> · TODO 캡션
        </figcaption>
      </figure>

      <div class="ai-prompt">
        <p class="ai-prompt__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z"/></svg>
          <span class="print-label">[AI에게] </span>AI에게 이렇게 시켜보세요
        </p>
        <div class="ai-prompt__text">TODO: 그대로 붙여 넣을 수 있는 프롬프트.

[내 환경]
[하고 싶은 것]
[꼭 지켜줘]
- TODO

마지막에 위험한 곳을 짚어줘.</div>
        <p class="ai-prompt__expect">
          <strong>이런 답이 오면 정상</strong> — TODO
        </p>
      </div>

      <div class="ai-trap">
        <p class="ai-trap__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/></svg>
          <span class="print-label">[AI 함정] </span>AI가 여기서 틀립니다
        </p>
        <p class="ai-trap__why">
          TODO: <strong>왜 AI 가 여기서 틀리는지</strong>, 왜 발견하기 어려운지.
        </p>
        <div class="ai-trap__grid">
          <div class="ai-trap__wrong">
            <span class="ai-trap__label"><span class="print-label">[X] </span>AI가 준 코드</span>
            <div class="example__code" data-lang="text">
<pre>TODO</pre>
            </div>
            <div class="example__output">
              <span class="example__output-label">문제</span>
<pre>· TODO</pre>
            </div>
          </div>
          <div class="ai-trap__right">
            <span class="ai-trap__label"><span class="print-label">[O] </span>고친 코드</span>
            <div class="example__code" data-lang="text">
<pre>TODO</pre>
            </div>
          </div>
        </div>
        <p class="ai-trap__caught">
          <strong>이걸 잡아낸 개념</strong> — TODO: 이 장의 어느 절이 이걸 잡아냈는지.
        </p>
      </div>
"""

꼬리 = """
    <!-- ============================================================ -->
    <section class="section chapter-outro">

      <div class="summary">
        <p class="summary__title">이 장에서 배운 것</p>
        <ul>
          <li>TODO</li>
          <li>TODO</li>
        </ul>
        <p class="summary__oneline">TODO: 한 문장으로 말하면.</p>
      </div>

      <div class="quiz">
        <h3 class="quiz__title">연습문제</h3>
{문제}
      </div>

      <div class="next-preview">
        <p class="next-preview__label">다음 장</p>
        <p class="next-preview__title">TODO</p>
        <p>TODO: 다음 장을 읽고 싶게 만드는 한 문단.</p>
      </div>
    </section>

  </main>

  <aside class="rail" aria-label="이 장의 주요 상자">
    <p class="rail__title">이 장의 상자</p>
    <ul class="rail__list">
      <li><a href="#{첫절}"><span class="rail__tag">핵심</span>TODO</a></li>
    </ul>
  </aside>

</div>

<!-- BUILD:PAGER:START -->
<!-- BUILD:PAGER:END -->

<footer class="book-footer">
  <p>{책제목}</p>
</footer>

<div class="search-overlay" id="search-overlay" role="dialog" aria-modal="true" aria-label="검색">
  <div class="search-panel">
    <input type="search" placeholder="검색…" aria-label="검색어">
    <div class="search-results"></div>
  </div>
</div>

<script src="../assets/book.js"></script>
</body>
</html>
"""

문제틀 = """
        <div class="quiz__item">
          <p class="quiz__q">
            <span>{n}.</span>
            <span>TODO 문제</span>
            <span class="quiz__level quiz__level--{난이도}">{난이도글}</span>
          </p>
          <details class="quiz__answer">
            <summary>정답 보기</summary>
            <div class="quiz__answer-body">
              <p>TODO 정답과 <strong>왜 그런지</strong>.</p>
            </div>
          </details>
        </div>
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    쪽id = sys.argv[1]
    덮어쓰기 = "--force" in sys.argv

    if not TOC.exists():
        print("TOC.md 가 없습니다. 책 폴더에서 실행하십시오.")
        return 1

    정보 = TOC읽기(쪽id)
    if not 정보:
        print(f"TOC.md 에 [{쪽id}] 가 없습니다.")
        print("TOC.md 에 먼저 추가하십시오:")
        print(f"  ### [{쪽id}] 제목 | 8 | todo")
        return 1

    절들 = 절들읽기(쪽id)
    경로 = ROOT / 폴더(쪽id) / f"{쪽id}.html"
    if 경로.exists() and not 덮어쓰기:
        print(f"{경로.relative_to(ROOT)} 가 이미 있습니다. --force 를 붙이십시오.")
        return 1

    m = re.match(r"^ch(\d+)$", 쪽id)
    번호 = m.group(1).lstrip("0") if m else "✳"
    쪽번호 = m.group(1).lstrip("0") if m else "0"
    부번호 = 정보["부"][:1] if 정보["부"][:1].isdigit() else "0"

    조각 = [머리.format(
        쪽제목=esc(정보["제목"]), 책제목=esc(제목읽기()), 쪽id=쪽id,
        부=esc(정보["부"]), 부번호=부번호, 번호=번호,
    )]

    for i, (절번호, 절제목) in enumerate(절들 or [("0.1", "TODO 첫 절")]):
        상자 = 상자모음 if i == 0 else ""
        if i == 1:
            상자 = 두번째상자.format(쪽번호=쪽번호)
        조각.append(절틀.format(
            절id=절id(절번호), 번호=절번호, 제목=esc(절제목), 상자=상자,
        ))

    # 절이 하나뿐이면 나머지 필수 상자를 첫 절에 몰아 넣습니다
    if len(절들) < 2:
        조각.insert(2, 두번째상자.format(쪽번호=쪽번호))

    문제 = "".join(
        문제틀.format(n=n, 난이도=d, 난이도글=g)
        for n, (d, g) in enumerate(
            [("easy", "쉬움"), ("normal", "보통"), ("hard", "어려움")], start=1)
    )
    첫절 = 절id(절들[0][0]) if 절들 else "s0-1"
    조각.append(꼬리.format(문제=문제, 첫절=첫절, 책제목=esc(제목읽기())))

    경로.parent.mkdir(parents=True, exist_ok=True)
    경로.write_text("".join(조각), encoding="utf-8")

    print("=" * 62)
    print(f"{경로.relative_to(ROOT)} — 절 {len(절들)}개")
    print("=" * 62)
    print("TODO 를 전부 채운 뒤 아래를 돌리십시오.")
    print("  python tools/build.py")
    print("  python tools/check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CHANGELOG.md 를 읽어 책 안의 '바뀐 것들' 쪽을 만듭니다.

계속 고쳐지는 책이라면 독자가 "저번에 읽은 뒤로 뭐가 바뀌었나"를
알 수 있어야 합니다. 그 쪽을 사람이 손으로 관리하면 금방 낡습니다.

    python tools/build_changelog.py

CHANGELOG.md 형식 (Keep a Changelog 를 따릅니다)

    ## [1.1.0] - 2026-03-15
    ### 더함
    - 12장에 데코레이터 절을 넣었습니다
    ### 고침
    - 8장 예제의 출력이 실제와 달랐습니다
    ### 뺌
    - 부록 D 의 옛 API 설명

'더함 / 고침 / 뺌 / 바꿈' 네 가지를 씁니다.
"""

import html as htmlmod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
원본 = ROOT / "CHANGELOG.md"
결과 = ROOT / "back" / "changelog.html"

종류색 = {
    "더함": "good",
    "고침": "warn",
    "뺌": "bad",
    "바꿈": "accent",
}



def 절id() -> str:
    """TOC.md 가 changelog 에 붙인 절 번호를 씁니다.

    여기서 s99-1 로 박아 두면 TOC.md 가 다른 번호를 쓸 때
    check_sections.py 가 어긋남을 잡아냅니다.
    """
    toc = ROOT / "TOC.md"
    if not toc.exists():
        return "s99-1"
    안에 = False
    for 줄 in toc.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### \[([^\]]+)\]", 줄)
        if m:
            안에 = m.group(1) == "changelog"
            continue
        if 안에:
            s = re.match(r"^- ((?:\d+|[A-H])\.\d+)\s", 줄)
            if s:
                return "s" + s.group(1).replace(".", "-")
    return "s99-1"

def esc(s: str) -> str:
    return htmlmod.escape(s, quote=False)


def 굵게(s: str) -> str:
    """**굵게** 와 `코드` 만 처리합니다. 나머지는 그대로 둡니다."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def 읽기() -> list[dict]:
    if not 원본.exists():
        return []

    판들 = []
    지금판 = None
    지금종류 = None

    for 줄 in 원본.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+\[?([^\]\s]+)\]?\s*-\s*(.+)$", 줄)
        if m:
            지금판 = {"판": m.group(1), "날짜": m.group(2).strip(), "묶음": []}
            판들.append(지금판)
            지금종류 = None
            continue

        m = re.match(r"^###\s+(.+)$", 줄)
        if m and 지금판 is not None:
            지금종류 = {"이름": m.group(1).strip(), "항목": []}
            지금판["묶음"].append(지금종류)
            continue

        m = re.match(r"^[-*]\s+(.+)$", 줄)
        if m and 지금종류 is not None:
            지금종류["항목"].append(m.group(1).strip())

    return 판들


def 만들기(판들: list[dict]) -> str:
    조각 = []
    for 판 in 판들:
        조각.append('      <div class="chlog">')
        조각.append(
            f'        <p class="chlog__ver">{esc(판["판"])}'
            f'<span class="chlog__date">{esc(판["날짜"])}</span></p>'
        )
        for 묶음 in 판["묶음"]:
            색 = 종류색.get(묶음["이름"], "accent")
            조각.append(
                f'        <p class="chlog__kind chlog__kind--{색}">'
                f'{esc(묶음["이름"])}</p>'
            )
            조각.append("        <ul>")
            for 항목 in 묶음["항목"]:
                조각.append(f"          <li>{굵게(항목)}</li>")
            조각.append("        </ul>")
        조각.append("      </div>")
    return "\n".join(조각)


쪽틀 = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>바뀐 것들 — {제목}</title>
<meta name="description" content="이 책이 언제 무엇이 바뀌었는지.">
<script>
  try {{
    var t = localStorage.getItem('book:theme');
    if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
  }} catch (e) {{}}
</script>
<link rel="stylesheet" href="../assets/book.css">
</head>
<body class="chapter" data-chapter="changelog" data-part="6" data-root="../">

<a class="skip-link" href="#main">본문 바로가기</a>

<header class="book-header">
  <button class="icon-btn sidebar-toggle" type="button" data-action="toggle-sidebar"
          aria-expanded="false" aria-label="목차 열기">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
  </button>
  <a class="book-header__brand" href="../index.html">{제목}</a>
  <span class="book-header__crumb">닫는 글 › 바뀐 것들</span>
  <span class="book-header__spacer"></span>
  <div class="book-header__actions">
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
      <p class="chapter-hero__part">닫는 글</p>
      <span class="chapter-hero__num">↻</span>
      <h1 class="chapter-hero__title">바뀐 것들</h1>
      <p class="chapter-hero__lead">
        이 책은 <strong>계속 고쳐집니다.</strong>
        <strong>저번에 읽은 뒤로 무엇이 달라졌는지</strong> 여기서 보십시오.
      </p>
    </div>

    <div class="chapter-meta">
      <span>참조용</span>
      <span>판 {판수}개</span>
    </div>

    <section class="section" id="{절id}">
      <h2>판별 변경 내역</h2>

{내역}
    </section>

    <section class="section chapter-outro">
      <div class="next-preview">
        <p class="next-preview__label">처음으로</p>
        <p class="next-preview__title">표지와 전체 목차</p>
        <p><a class="xref" href="../index.html">첫 쪽으로 돌아가기</a></p>
      </div>
    </section>

  </main>
</div>

<!-- BUILD:PAGER:START -->
<!-- BUILD:PAGER:END -->

<footer class="book-footer">
  <p>{제목}</p>
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


def 제목읽기() -> str:
    import json
    p = ROOT / "book.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("title", "책")
        except Exception:
            pass
    return "책"


def main() -> int:
    판들 = 읽기()
    if not 판들:
        print("CHANGELOG.md 가 없거나 비어 있습니다.")
        print("아래 형식으로 만드십시오:")
        print()
        print("  ## [1.0.0] - 2026-01-01")
        print("  ### 더함")
        print("  - 첫 판을 냈습니다")
        return 1

    결과.parent.mkdir(exist_ok=True)
    결과.write_text(
        쪽틀.format(제목=esc(제목읽기()), 판수=len(판들),
                   내역=만들기(판들), 절id=절id()),
        encoding="utf-8",
    )

    항목수 = sum(len(g["항목"]) for v in 판들 for g in v["묶음"])
    print("=" * 62)
    print(f"back/changelog.html — 판 {len(판들)}개 · 항목 {항목수}개")
    print(f"  최신: {판들[0]['판']} ({판들[0]['날짜']})")
    print("=" * 62)
    print("TOC.md 의 닫는 글 부분에 아래 줄이 있는지 확인하십시오:")
    print("  ### [changelog] 바뀐 것들 | 1 | done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""TOC.md 와 book.json 으로 표지(index.html)를 만듭니다.

목차를 손으로 두 곳에 쓰면 반드시 어긋납니다.
표지도 TOC.md 에서 나오게 해서 그 일을 없앱니다.

    python tools/build_index.py

TOC.md 에서 쪽 제목 바로 아래 줄에 `> ` 로 시작하는 한 줄을 두면
표지에 부제로 나옵니다.

    ### [ch01] 컨테이너가 뭔가요 | 8 | done
    > 가상머신과 무엇이 다른지부터
"""

import html as htmlmod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"
결과 = ROOT / "index.html"

쪽패턴 = re.compile(r"^### \[([^\]]+)\]\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\w+)\s*$")
부패턴 = re.compile(r"^## (.+)$")
설명패턴 = re.compile(r"^>\s+(.+)$")


def esc(s: str) -> str:
    return htmlmod.escape(s, quote=False)


def ch숫자(쪽id: str) -> bool:
    return re.match(r"^ch\d", 쪽id) is not None


def 경로(쪽id: str) -> str:
    if ch숫자(쪽id):
        return f"chapters/{쪽id}.html"
    if 쪽id.startswith("apx-"):
        return f"appendix/{쪽id}.html"
    if 쪽id in ("prologue", "howto"):
        return f"front/{쪽id}.html"
    return f"back/{쪽id}.html"


def 번호(쪽id: str) -> str:
    m = re.match(r"^ch0*(\d+)$", 쪽id)
    if m:
        return m.group(1)
    m = re.match(r"^apx-([a-h])-", 쪽id)
    if m:
        return m.group(1).upper()
    return "—"


def 설정() -> dict:
    p = ROOT / "book.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def 읽기() -> list[dict]:
    부들 = []
    지금부 = None
    지난쪽 = None

    for 줄 in TOC.read_text(encoding="utf-8").splitlines():
        b = 부패턴.match(줄)
        if b and not 줄.startswith("## 파싱"):
            지금부 = {"이름": b.group(1).strip(), "쪽": []}
            부들.append(지금부)
            지난쪽 = None
            continue

        m = 쪽패턴.match(줄)
        if m and 지금부 is not None:
            지난쪽 = {
                "id": m.group(1), "제목": m.group(2),
                "쪽수": int(m.group(3)), "상태": m.group(4), "설명": "",
            }
            지금부["쪽"].append(지난쪽)
            continue

        d = 설명패턴.match(줄)
        if d and 지난쪽 is not None:
            지난쪽["설명"] = d.group(1).strip()

    return [b for b in 부들 if b["쪽"]]


def 부만들기(부: dict) -> str:
    이름 = 부["이름"]
    m = re.match(r"^PART\s+(\S+)\s*·\s*(.+)$", 이름)
    번호글, 제목 = (m.group(1), m.group(2)) if m else ("", 이름)
    꼬리 = f"{len(부['쪽'])}쪽" if 번호글.isdigit() else ""

    줄 = [
        '  <section class="part">',
        '    <div class="part__head">',
        f'      <span class="part__num">{esc(번호글 + "부" if 번호글.isdigit() else 제목[:6])}</span>',
        f'      <span class="part__name">{esc(제목)}</span>',
    ]
    if 꼬리:
        줄.append(f'      <span class="part__pages">{꼬리}</span>')
    줄 += ['    </div>', '    <ul class="toc-list">']

    for 쪽 in 부["쪽"]:
        있음 = (ROOT / 경로(쪽["id"])).exists()
        줄.append(f'      <li data-id="{쪽["id"]}">')
        if 있음:
            줄.append(f'        <a class="toc-row" href="{경로(쪽["id"])}">')
        else:
            줄.append('        <span class="toc-row">')
        줄 += [
            f'        <span class="toc-row__num">{esc(번호(쪽["id"]))}</span>',
            '        <span class="toc-row__body">',
            f'          <span class="toc-row__title">{esc(쪽["제목"])}</span>',
        ]
        if 쪽["설명"]:
            줄.append(f'          <span class="toc-row__desc">{esc(쪽["설명"])}</span>')
        줄.append('        </span>')
        줄.append('        </a>' if 있음 else '        </span>')
        줄.append('      </li>')

    줄 += ['    </ul>', '  </section>', '']
    return "\n".join(줄)


틀 = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{제목}</title>
<meta name="description" content="{부제}">
<script>
  try {{
    var t = localStorage.getItem('book:theme');
    if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
  }} catch (e) {{}}
</script>
<link rel="stylesheet" href="assets/book.css">
<style>
  .cover {{
    max-width: 820px; margin-inline: auto;
    padding: var(--space-7) var(--space-4) var(--space-6);
    text-align: center;
  }}
  .cover__title {{
    font-size: clamp(1.9rem, 5vw, 3rem); line-height: 1.25;
    margin-block: var(--space-4) var(--space-5);
  }}
  .cover__thesis {{
    max-width: 44ch; margin-inline: auto;
    font-size: 1.125rem; line-height: 1.8; color: var(--fg-muted);
    padding: var(--space-5); border-radius: var(--radius-lg);
    background: var(--bg-subtle); border: 1px solid var(--border-soft);
  }}
  .cover__thesis strong {{ color: var(--fg); }}
  .cover__actions {{
    display: flex; flex-wrap: wrap; gap: var(--space-3);
    justify-content: center; margin-top: var(--space-6);
  }}
  .btn {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 11px 22px; border-radius: var(--radius);
    font-weight: 700; font-size: 0.9375rem; text-decoration: none;
    border: 1px solid var(--border);
    background: var(--bg-elevated); color: var(--fg);
  }}
  .btn:hover {{ border-color: var(--accent); background: var(--bg-subtle); }}
  .btn--primary {{
    background: var(--accent); color: var(--fg-on-accent); border-color: var(--accent);
  }}
  .home-wrap {{ min-width: 0; }}
  .home {{ min-width: 0; padding: 0 0 var(--space-8); max-width: 860px; margin-inline: auto; }}
  .stats {{
    display: grid; gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    margin-block: var(--space-6);
  }}
  .stat {{
    padding: var(--space-4); border-radius: var(--radius);
    background: var(--bg-subtle); border: 1px solid var(--border-soft);
    text-align: center;
  }}
  .stat__num {{ font-size: 1.75rem; font-weight: 800; line-height: 1.2; }}
  .stat__label {{ font-size: 0.75rem; color: var(--fg-faint); margin-top: 2px; }}
  .part {{ margin-block: var(--space-7); }}
  .part__head {{
    display: flex; align-items: baseline; gap: var(--space-3);
    padding-bottom: var(--space-2); margin-bottom: var(--space-4);
    border-bottom: 2px solid var(--border);
  }}
  .part__num {{
    font-size: 0.75rem; font-weight: 800; letter-spacing: .1em; color: var(--accent);
  }}
  .part__name {{ font-size: 1.1875rem; font-weight: 700; }}
  .part__pages {{ margin-inline-start: auto; font-size: 0.8125rem; color: var(--fg-faint); }}
  .toc-list {{ list-style: none; padding: 0; margin: 0; }}
  .toc-row {{
    display: flex; align-items: baseline; gap: var(--space-3);
    padding: var(--space-3); border-radius: var(--radius);
    text-decoration: none; color: var(--fg); border: 1px solid transparent;
  }}
  a.toc-row:hover {{ background: var(--bg-subtle); border-color: var(--border-soft); }}
  span.toc-row {{ opacity: .55; }}
  .toc-row__num {{
    flex: none; width: 2.4em; font-weight: 800; font-size: 0.9375rem; color: var(--fg-faint);
  }}
  .toc-row__body {{ flex: 1; min-width: 0; }}
  .toc-row__title {{ font-weight: 700; font-size: 0.9375rem; display: block; }}
  .toc-row__desc {{ font-size: 0.8125rem; color: var(--fg-muted); margin-top: 2px; display: block; }}
  .toc-row__state {{
    flex: none; font-size: 0.6875rem; font-weight: 700;
    padding: 2px 9px; border-radius: 999px;
    background: var(--bg-sunken); color: var(--fg-faint);
  }}
  .toc-row__state--done {{ background: var(--fig-good-bg); color: var(--box-tip-head); }}
  .toc-row__state--wip  {{ background: var(--fig-warn-bg); color: var(--box-pitfall-head); }}
  li.is-read .toc-row__num::after {{ content: " ✓"; color: var(--box-tip-head); }}

  @media print {{
    .cover__actions, .stats, .toc-row__state {{ display: none !important; }}
    .cover {{ padding-block: 0; }}
    .part {{ break-inside: avoid; }}
  }}
</style>
</head>
<body data-chapter="index" data-root="./">

<a class="skip-link" href="#main">목차 바로가기</a>

<header class="book-header">
  <button class="icon-btn sidebar-toggle" type="button" data-action="toggle-sidebar"
          aria-expanded="false" aria-label="목차 열기">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
  </button>
  <a class="book-header__brand" href="index.html">{짧은제목}</a>
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

  <div class="home-wrap">

<div class="cover">
  <h1 class="cover__title">{표지제목}</h1>
  <p class="cover__thesis">{부제}</p>
  <div class="cover__actions">
    <a class="btn btn--primary" href="{첫쪽}">처음부터 읽기</a>
    <a class="btn" href="back/changelog.html">바뀐 것들</a>
  </div>
</div>

<main class="home" id="main">

  <div class="stats">
    <div class="stat"><p class="stat__num">{장수}</p><p class="stat__label">장</p></div>
    <div class="stat"><p class="stat__num">{부록수}</p><p class="stat__label">부록</p></div>
    <div class="stat"><p class="stat__num" id="stat-read">0</p><p class="stat__label">읽은 장</p></div>
    <div class="stat"><p class="stat__num">{그림수}</p><p class="stat__label">삽화</p></div>
  </div>

{목차}
</main>

  </div>
</div>

<footer class="book-footer">
  <p>{제목}</p>
</footer>

<div class="search-overlay" id="search-overlay" role="dialog" aria-modal="true" aria-label="검색">
  <div class="search-panel">
    <input type="search" placeholder="검색…" aria-label="검색어">
    <div class="search-results"></div>
  </div>
</div>

<script src="assets/book.js"></script>
<script>
  (function () {{
    var done = {{}};
    try {{ done = JSON.parse(localStorage.getItem('book:done') || '{{}}') || {{}}; }} catch (e) {{}}
    var n = 0;
    Array.prototype.forEach.call(document.querySelectorAll('li[data-id]'), function (li) {{
      if (done[li.getAttribute('data-id')]) {{ li.classList.add('is-read'); n++; }}
    }});
    var el = document.getElementById('stat-read');
    if (el) el.textContent = String(n);
  }})();
</script>
</body>
</html>
"""


def 그림세기() -> int:
    n = 0
    for 폴더 in ("front", "chapters", "appendix", "back"):
        for p in (ROOT / 폴더).glob("*.html"):
            n += len(re.findall(r'<figure class="figure"', p.read_text(encoding="utf-8")))
    return n


def main() -> int:
    if not TOC.exists():
        print("TOC.md 가 없습니다.")
        return 1

    conf = 설정()
    부들 = 읽기()
    쪽전부 = [쪽 for b in 부들 for 쪽 in b["쪽"]]
    장수 = sum(1 for 쪽 in 쪽전부 if ch숫자(쪽["id"]))
    부록수 = sum(1 for 쪽 in 쪽전부 if 쪽["id"].startswith("apx-"))

    첫쪽 = next(
        (경로(쪽["id"]) for 쪽 in 쪽전부 if (ROOT / 경로(쪽["id"])).exists()),
        "index.html",
    )
    제목 = conf.get("title") or "책"
    # 표지 큰 제목만 특정 지점(줄바꿈 지정)에서 강제로 줄을 바꿉니다.
    # book.json 의 "cover_break_after" 로 그 지점을 지정합니다(예: "만들고").
    # 지정이 없으면 화면 너비에 따라 자동으로 줄바꿈됩니다.
    끊을위치 = conf.get("cover_break_after")
    표지제목 = esc(제목)
    if 끊을위치 and f"{끊을위치} " in 제목:
        표지제목 = esc(제목).replace(f"{esc(끊을위치)} ", f"{esc(끊을위치)}<br>")

    결과.write_text(틀.format(
        lang=conf.get("lang", "ko"),
        제목=esc(제목),
        표지제목=표지제목,
        짧은제목=esc(제목),
        부제=esc(conf.get("subtitle") or "TODO: book.json 의 subtitle 을 채우십시오."),
        첫쪽=첫쪽,
        장수=장수, 부록수=부록수, 그림수=그림세기(),
        목차="\n".join(부만들기(b) for b in 부들),
    ), encoding="utf-8")

    완성 = sum(1 for 쪽 in 쪽전부 if 쪽["상태"] == "done")
    print("=" * 62)
    print(f"index.html — 쪽 {len(쪽전부)}개 (완성 {완성} · 남음 {len(쪽전부) - 완성})")
    print(f"  장 {장수} · 부록 {부록수} · 삽화 {그림세기()}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())

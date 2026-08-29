"""TOC.md를 읽어 모든 페이지의 사이드바와 이전/다음 네비게이션을 만듭니다.

TOC.md가 목차의 유일한 원본입니다. 챕터 HTML의 사이드바를 손으로 고치지 말고
이 스크립트를 실행하십시오.

    python tools/build_toc.py           # 전체 다시 생성
    python tools/build_toc.py --check   # 바뀔 파일만 확인 (쓰지 않음)

각 페이지에는 아래 표시가 있어야 합니다.

    <!-- BUILD:SIDEBAR:START -->  ...  <!-- BUILD:SIDEBAR:END -->
    <!-- BUILD:PAGER:START -->    ...  <!-- BUILD:PAGER:END -->
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from posixpath import relpath

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"

# data-id 로 폴더를 정합니다. 다른 도구와 같은 규칙이어야 합니다.
#   ch + 숫자  -> chapters   (changelog 는 ch 로 시작하지만 장이 아닙니다)
#   apx-       -> appendix
#   prologue / howto -> front
#   그 밖      -> back
FRONT = {"prologue", "howto"}


@dataclass
class Page:
    pid: str
    title: str
    part_index: int
    sections: list[tuple[str, str]] = field(default_factory=list)

    @property
    def path(self) -> str:
        """저장소 루트 기준 경로 (posix)."""
        if re.match(r"^ch\d", self.pid):
            return f"chapters/{self.pid}.html"
        if self.pid.startswith("apx-"):
            return f"appendix/{self.pid}.html"
        if self.pid in FRONT:
            return f"front/{self.pid}.html"
        return f"back/{self.pid}.html"

    @property
    def exists(self) -> bool:
        return (ROOT / self.path).exists()

    @property
    def label(self) -> str:
        """사이드바 왼쪽에 붙는 번호나 기호."""
        m = re.fullmatch(r"ch(\d+)", self.pid)
        if m:
            return str(int(m.group(1)))
        m = re.match(r"apx-([a-z])-", self.pid)
        if m:
            return m.group(1).upper()
        return "·"

    @property
    def short_title(self) -> str:
        """'부록 A · NumPy, …' 처럼 앞에 붙은 라벨을 떼어냅니다."""
        return re.sub(r"^부록 [A-H] · ", "", self.title)


@dataclass
class Part:
    num: int
    name: str
    pages: list[Page] = field(default_factory=list)

    @property
    def heading(self) -> str:
        if 1 <= self.num <= 4:
            return f"{self.num}부 · {self.name}"
        return self.name


def parse_toc() -> list[Part]:
    parts: list[Part] = []
    page: Page | None = None

    for raw in TOC.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()

        m = re.match(r"^## PART (\d+) · (.+)$", line)
        if m:
            parts.append(Part(num=int(m.group(1)), name=m.group(2).strip()))
            page = None
            continue

        m = re.match(r"^### \[([^\]]+)\] (.+?) \|", line)
        if m and parts:
            page = Page(pid=m.group(1), title=m.group(2).strip(),
                        part_index=len(parts) - 1)
            parts[-1].pages.append(page)
            continue

        m = re.match(r"^- ((?:\d+|[A-H])\.\d+) (.+)$", line)
        if m and page is not None:
            number, title = m.group(1), m.group(2).strip()
            anchor = "s" + number.replace(".", "-")
            page.sections.append((anchor, f"{number} {title}"))
            continue

    return parts


def href(from_path: str, to_path: str) -> str:
    """from_path 문서에서 to_path 문서를 가리키는 상대 경로."""
    from_dir = from_path.rsplit("/", 1)[0] if "/" in from_path else "."
    return relpath(to_path, from_dir)


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def build_sidebar(parts: list[Part], current: Page | None,
                  from_path: str = "index.html") -> str:
    """책 전체 목차를 만듭니다.

    current가 None이면 표지(index.html)용입니다. 현재 장 표시 없이
    전체 목록만 나오고, 스크롤에 따라 강조가 따라갑니다.
    """
    here = current.path if current else from_path
    out: list[str] = ['<nav class="sidebar" id="sidebar" aria-label="목차">']

    if current is not None:
        out.append(
            f'    <a class="sidebar__home" href="{href(here, "index.html")}">'
            "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" "
            'stroke-width="2"><path d="M3 10l9-7 9 7v10a1 1 0 01-1 1h-5v-7H9v7H4a1 1 '
            '0 01-1-1z"/></svg>표지와 전체 목차</a>'
        )
    else:
        out.append('    <p class="sidebar__here">전체 목차</p>')

    for part in parts:
        if not part.pages:
            continue
        out.append(f'    <p class="sidebar__title">{esc(part.heading)}</p>')
        out.append('    <ul class="sidebar__list">')

        for page in part.pages:
            is_current = current is not None and page.pid == current.pid
            classes = ["sidebar__item"]
            if is_current:
                classes.append("is-current")
            if not page.exists:
                classes.append("is-todo")
            cls = " ".join(classes)

            inner = (
                f'<span class="sidebar__num">{esc(page.label)}</span>'
                f"{esc(page.short_title)}"
            )
            if page.exists:
                link = f'<a href="{href(here, page.path)}">{inner}</a>'
            else:
                link = f'<span class="sidebar__pending">{inner}</span>'

            out.append(f'      <li class="{cls}" data-id="{page.pid}">')
            out.append(f"        {link}")

            # 현재 페이지만 절 목록을 펼칩니다.
            if is_current and page.sections:
                out.append('        <ul class="sidebar__sub">')
                for anchor, text in page.sections:
                    out.append(
                        f'          <li><a href="#{anchor}">{esc(text)}</a></li>'
                    )
                out.append("        </ul>")

            out.append("      </li>")

        out.append("    </ul>")

    out.append("  </nav>")
    return "\n  ".join(out)


def build_pager(flat: list[Page], index: int, current: Page) -> str:
    prev_page = flat[index - 1] if index > 0 else None
    next_page = flat[index + 1] if index + 1 < len(flat) else None

    def side(page: Page | None, kind: str) -> str:
        arrow = "← 이전" if kind == "prev" else "다음 →"
        if page is None:
            return f'  <span class="pager__{kind} pager__empty"></span>'

        label = page.label
        name = page.title if label == "·" else f"{label}장 · {page.title}"
        if page.pid.startswith("apx-"):
            name = page.title

        body = (
            f'    <p class="pager__dir">{arrow}</p>\n'
            f'    <p class="pager__name">{esc(name)}</p>'
        )
        if page.exists:
            return (
                f'  <a class="pager__{kind}" '
                f'href="{href(current.path, page.path)}">\n{body}\n  </a>'
            )
        return (
            f'  <span class="pager__{kind} pager__pending">\n{body}\n  </span>'
        )

    return (
        '<nav class="pager" aria-label="페이지 이동">\n'
        f"{side(prev_page, 'prev')}\n"
        f"{side(next_page, 'next')}\n"
        "</nav>"
    )


def replace_block(text: str, name: str, body: str) -> tuple[str, bool]:
    start = f"<!-- BUILD:{name}:START -->"
    end = f"<!-- BUILD:{name}:END -->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    if not pattern.search(text):
        return text, False
    return pattern.sub(f"{start}\n  {body}\n  {end}", text, count=1), True


def main() -> int:
    check_only = "--check" in sys.argv

    parts = parse_toc()
    flat = [p for part in parts for p in part.pages]

    print(f"TOC.md: {len(parts)}개 부, {len(flat)}개 페이지")
    print(f"이 중 {sum(1 for p in flat if p.exists)}개가 작성되어 있습니다\n")

    changed = 0
    skipped: list[str] = []

    # 표지 — 현재 장 없이 전체 목차만 넣습니다.
    index_path = ROOT / "index.html"
    if index_path.exists():
        original = index_path.read_text(encoding="utf-8")
        text, ok = replace_block(
            original, "SIDEBAR", build_sidebar(parts, None)
        )
        if not ok:
            skipped.append("index.html — SIDEBAR 표시 없음")
        elif text != original:
            changed += 1
            print("  갱신  index.html")
            if not check_only:
                index_path.write_text(text, encoding="utf-8")

    for i, page in enumerate(flat):
        if not page.exists:
            continue

        path = ROOT / page.path
        original = path.read_text(encoding="utf-8")
        text = original

        text, ok_sidebar = replace_block(
            text, "SIDEBAR", build_sidebar(parts, page)
        )
        text, ok_pager = replace_block(
            text, "PAGER", build_pager(flat, i, page)
        )

        missing = []
        if not ok_sidebar:
            missing.append("SIDEBAR")
        if not ok_pager:
            missing.append("PAGER")
        if missing:
            skipped.append(f"{page.path} — {', '.join(missing)} 표시 없음")

        if text != original:
            changed += 1
            print(f"  갱신  {page.path}")
            if not check_only:
                path.write_text(text, encoding="utf-8")

    if skipped:
        print("\n표시가 없어 건너뛴 부분:")
        for line in skipped:
            print(f"  {line}")

    print()
    if changed == 0:
        print("바뀐 파일이 없습니다")
    elif check_only:
        print(f"{changed}개 파일이 바뀔 예정입니다 (--check 이므로 쓰지 않았습니다)")
    else:
        print(f"{changed}개 파일을 갱신했습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

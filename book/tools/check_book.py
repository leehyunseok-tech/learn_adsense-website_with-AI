"""책 원고 검증기.

세 가지를 검사합니다.

1. 예제 코드 폭   — 인쇄 기준 88칼럼. 한글은 2칸으로 셉니다.
2. 챕터 구성 요소 — STYLEGUIDE.md가 정한 최소 개수를 채웠는가.
3. SVG 하드코딩 색 — 다크모드·인쇄에서 깨지는 원인이라 금지.

사용법:
    python tools/check_book.py            # 전체 검사
    python tools/check_book.py chapters/ch04.html
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_WIDTH = 88          # book.json 의 max_width 로 덮어쓸 수 있습니다

# STYLEGUIDE.md 5.1 — 챕터당 최소 개수
REQUIRED = {
    "chapter-goals": 1,
    "analogy": 2,
    "ai-prompt": 1,
    "ai-trap": 1,
    "pitfall": 1,
    "summary": 1,
    "quiz__item": 3,
    "next-preview": 1,
}

# 부록은 성격이 다릅니다.
# 통독용이 아니라 필요할 때 펴보는 참조 파트라, 비유·퀴즈·요약을
# 본문과 같은 기준으로 요구하면 억지로 채우게 됩니다.
# 대신 "이 부록이 필요한 사람" 안내와 다음 안내는 반드시 있어야 합니다.
REQUIRED_APPENDIX = {
    "next-preview": 1,
}

# 참고용으로 함께 세는 것들 (최소 개수 없음)
COUNT_ALSO = ["concept", "check", "deepdive", "example", "figure"]

# 정확히 1개여야 하는 것
EXACTLY_ONE = {"summary", "next-preview", "chapter-goals"}


def is_appendix(path: Path) -> bool:
    return path.parent.name in ("appendix", "front", "back")




def 설정() -> dict:
    """book.json 을 읽습니다. 책마다 다른 값은 전부 여기 있습니다."""
    import json
    p = ROOT / "book.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def display_width(text: str) -> int:
    """인쇄했을 때 차지하는 칼럼 수. 한글·한자·전각은 2칸."""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def check_code_width() -> list[str]:
    """code/ 아래 모든 .py 파일의 줄 폭을 검사합니다."""
    problems = []
    code_dir = ROOT / "code"
    if not code_dir.exists():
        return problems

    for path in sorted(code_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            width = display_width(line)
            if width > MAX_WIDTH:
                rel = path.relative_to(ROOT).as_posix()
                problems.append(f"{rel}:{lineno} 인쇄 폭 {width}칸 (한계 {MAX_WIDTH})")
    return problems


def strip_quoted(html: str) -> str:
    """인용된 내용을 걷어냅니다.

    코드 블록과 AI 프롬프트 안에는 예시로 넣은 HTML이 들어갈 수 있는데,
    그 안의 class= 는 이 페이지의 구조가 아니라 '보여주는 글'입니다.
    구성 요소를 셀 때는 빼야 합니다.
    """
    for pattern in (
        r'<div class="example__code"[^>]*>.*?</div>',
        r'<div class="ai-prompt__text"[^>]*>.*?</div>',
    ):
        html = re.sub(pattern, "", html, flags=re.DOTALL)
    return html


def count_class(html: str, name: str) -> int:
    """class="foo" 또는 class="foo bar" 형태를 모두 셉니다."""
    pattern = re.compile(r'class="([^"]*)"')
    total = 0
    for match in pattern.finditer(html):
        if name in match.group(1).split():
            total += 1
    return total


def check_chapter(path: Path) -> tuple[list[str], dict[str, int]]:
    """챕터 HTML 하나를 검사합니다."""
    raw = path.read_text(encoding="utf-8")
    html = strip_quoted(raw)      # 인용된 HTML은 세지 않습니다
    rel = path.relative_to(ROOT).as_posix()
    problems = []
    counts = {}

    기준 = REQUIRED_APPENDIX if is_appendix(path) else REQUIRED

    for name, minimum in 기준.items():
        found = count_class(html, name)
        counts[name] = found
        if found < minimum:
            problems.append(f"{rel}: .{name} {found}개 (최소 {minimum}개 필요)")
        elif name in EXACTLY_ONE and found > 1:
            problems.append(f"{rel}: .{name} {found}개 (정확히 1개여야 함)")

    # 기준에 없는 것도 참고로 세어 둡니다
    for name in list(REQUIRED) + COUNT_ALSO:
        if name not in counts:
            counts[name] = count_class(html, name)

    # SVG 안의 하드코딩 색
    hardcoded = re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,8})"', html)
    if hardcoded:
        unique = sorted(set(hardcoded))
        problems.append(
            f"{rel}: SVG 하드코딩 색 {len(hardcoded)}건 {unique} "
            "— var(--fig-*)를 쓰십시오"
        )

    # 예제에 실행 결과가 붙어 있는지
    runnable = len(re.findall(r'data-run="true"', html))
    expected = len(re.findall(r'data-expected="true"', html))
    counts["example(실행)"] = runnable
    if runnable > expected:
        problems.append(
            f"{rel}: data-run 예제 {runnable}개 중 {expected}개만 "
            "실행 결과가 있습니다"
        )

    return problems, counts


def check_xrefs(path: Path, cache: dict[str, str]) -> list[str]:
    """상호참조가 실제로 도달하는지 확인합니다.

    아직 안 쓴 장을 가리키는 것은 문제가 아닙니다(곧 씁니다).
    이미 있는 파일인데 그 앵커가 없는 경우만 잡습니다.
    """
    html = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    problems = []

    pattern = re.compile(r'<a class="xref" href="([^"#]+)#([^"]+)"')
    for target, anchor in pattern.findall(html):
        # ../appendix/... 같은 상대경로를 풀어 줍니다
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            continue                      # 아직 안 쓴 장 — 넘어갑니다
        key = str(resolved)
        if key not in cache:
            cache[key] = resolved.read_text(encoding="utf-8")
        if f'id="{anchor}"' not in cache[key]:
            problems.append(f"{rel}: 앵커 없음 — {target}#{anchor}")

    return problems


def check_deprecated(path: Path) -> list[str]:
    """폐기된 API가 본문에 남아 있는지 검사합니다.

    함정 상자에서 일부러 보여주는 경우는 data-deprecated-ok로 예외 처리합니다.
    """
    # 인용된 내용은 빼고 봅니다.
    # AI 프롬프트에 "agg(np.sum) 같은 옛날 문법은 쓰지 마" 라고
    # 적는 것은 올바른 지시이지 위반이 아닙니다.
    html = strip_quoted(path.read_text(encoding="utf-8"))
    rel = path.relative_to(ROOT).as_posix()

    banned = 설정().get("deprecated", {})

    # data-deprecated-ok가 붙은 요소는 통째로 제외합니다.
    # 코드 블록(<div>)뿐 아니라 본문에서 "이건 옛날 문법입니다"라고
    # 설명하며 인용하는 인라인 <code>에도 붙일 수 있습니다.
    cleaned = re.sub(
        r'<div class="example__code"[^>]*data-deprecated-ok[^>]*>.*?</div>',
        "",
        html,
        flags=re.DOTALL,
    )
    cleaned = re.sub(
        r"<code[^>]*data-deprecated-ok[^>]*>.*?</code>",
        "",
        cleaned,
        flags=re.DOTALL,
    )

    problems = []
    for pattern, message in banned.items():
        if re.search(pattern, cleaned):
            problems.append(f"{rel}: 폐기 API — {message}")
    return problems


def main() -> int:
    targets = []
    if len(sys.argv) > 1:
        targets = [ROOT / arg for arg in sys.argv[1:]]
    else:
        for folder in ("chapters", "appendix", "front", "back"):
            targets.extend(sorted((ROOT / folder).glob("*.html")))

    global MAX_WIDTH
    conf = 설정()
    MAX_WIDTH = conf.get("max_width", MAX_WIDTH)
    for 이름, 값 in conf.get("minimums", {}).items():
        REQUIRED[이름] = 값

    all_problems = []
    xref_cache: dict[str, str] = {}

    print("=" * 62)
    print("1. 예제 코드 인쇄 폭")
    print("=" * 62)
    width_problems = check_code_width()
    if width_problems:
        for problem in width_problems:
            print(f"  실패  {problem}")
        all_problems.extend(width_problems)
    else:
        print(f"  통과  code/ 아래 모든 줄이 {MAX_WIDTH}칸 이내입니다")

    print()
    print("=" * 62)
    print("2. 챕터 구성 요소")
    print("=" * 62)

    if not targets:
        print("  검사할 HTML이 없습니다")
    for path in targets:
        if not path.exists():
            print(f"  건너뜀  {path} 없음")
            continue

        problems, counts = check_chapter(path)
        problems += check_deprecated(path)
        problems += check_xrefs(path, xref_cache)
        rel = path.relative_to(ROOT).as_posix()

        if problems:
            print(f"\n  [{rel}]")
            for problem in problems:
                print(f"    실패  {problem.split(': ', 1)[-1]}")
            all_problems.extend(problems)
        else:
            summary = "  ".join(
                f"{name} {counts[name]}"
                for name in ("analogy", "pitfall", "ai-prompt", "ai-trap",
                             "example", "figure", "quiz__item")
            )
            print(f"  통과  {rel}")
            print(f"        {summary}")

    print()
    print("=" * 62)
    if all_problems:
        print(f"문제 {len(all_problems)}건")
        return 1
    print("전부 통과했습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

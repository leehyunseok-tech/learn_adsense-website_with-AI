"""빌드를 전부, 올바른 순서로 돌립니다.

순서가 중요합니다. 목차를 먼저 맞춘 뒤에야 사이드바가 제대로 나오고,
사이드바가 있어야 합본이 온전합니다.

    python tools/build.py            # 목차 · 사이드바 · 이력 · 검색 · 합본
    python tools/build.py --pdf      # 위에 더해 A4 PDF 까지
"""

import subprocess
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent
ROOT = 여기.parent

단계 = [
    # 순서가 중요합니다.
    # 쪽을 다 만든 뒤에야 사이드바를 주입할 수 있습니다.
    # 순서를 바꾸면 나중에 만든 쪽의 사이드바가 빕니다.
    ("sync_toc_sections.py", ["--write"], "실제 절 제목을 TOC.md 에 반영"),
    ("build_changelog.py",   [],          "바뀐 것들 쪽 만들기"),
    ("build_index.py",       [],          "표지와 전체 목차 만들기"),
    ("build_toc.py",         [],          "모든 쪽에 사이드바·이전/다음 주입"),
    ("build_search.py",      [],          "검색 색인"),
    ("build_print.py",       [],          "전권 합본 print.html"),
]


def 돌리기(이름: str, 인자: list[str]) -> tuple[int, str]:
    p = 여기 / 이름
    if not p.exists():
        return 0, f"(없음 — 건너뜀)"
    r = subprocess.run(
        [sys.executable, str(p), *인자],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    끝줄 = [x for x in (r.stdout or "").splitlines() if x.strip()]
    return r.returncode, (끝줄[-1] if 끝줄 else "")


def main() -> int:
    실패 = 0
    print("=" * 62)
    for 이름, 인자, 설명 in 단계:
        코드, 마지막 = 돌리기(이름, 인자)
        표시 = "  " if 코드 == 0 else "!!"
        print(f"{표시} {설명:28} {마지막[:34]}")
        if 코드 != 0:
            실패 += 1

    if "--pdf" in sys.argv:
        코드, 마지막 = 돌리기("build_pdf.py", [])
        표시 = "  " if 코드 == 0 else "!!"
        print(f"{표시} {'A4 PDF':28} {마지막[:34]}")
        if 코드 != 0:
            실패 += 1

    print("=" * 62)
    if 실패:
        print(f"{실패}단계가 실패했습니다. 위 !! 표시를 직접 돌려 보십시오.")
        return 1
    print("빌드 완료. 이어서 python tools/check.py 를 돌리십시오.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

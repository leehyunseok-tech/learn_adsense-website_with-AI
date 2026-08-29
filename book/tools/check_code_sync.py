"""지면에 실린 코드가 code/ 의 실제 파일과 같은지 대조합니다.

책에 적힌 코드와 저장소의 파일이 어긋나면 독자가 따라 할 수 없습니다.
data-file 이 붙은 코드 블록을 전부 찾아 바이트 단위로 맞춰 봅니다.

    python tools/check_code_sync.py
"""

import html as htmlmod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

블록 = re.compile(
    r'<div class="example__code"[^>]*data-file="([^"]+)"[^>]*>\s*<pre>(.*?)</pre>',
    re.DOTALL,
)


def 벗기기(코드html: str) -> str:
    """문법 강조 태그를 걷어내고 엔티티를 되돌립니다."""
    글 = re.sub(r"<[^>]+>", "", 코드html)
    return htmlmod.unescape(글).strip()


def 첫차이(지면: str, 파일: str) -> str:
    지면줄, 파일줄 = 지면.splitlines(), 파일.splitlines()
    for i, (a, b) in enumerate(zip(지면줄, 파일줄), 1):
        if a != b:
            return f"{i}행\n        지면: {a!r}\n        파일: {b!r}"
    if len(지면줄) != len(파일줄):
        return f"줄 수가 다릅니다 (지면 {len(지면줄)} / 파일 {len(파일줄)})"
    return "(원인을 못 찾았습니다)"


def main() -> int:
    쪽들 = sorted(ROOT.glob("chapters/*.html"))
    쪽들 += sorted(ROOT.glob("appendix/*.html"))

    맞음 = 틀림 = 0
    문제 = []

    for 쪽 in 쪽들:
        원문 = 쪽.read_text(encoding="utf-8")
        쌍들 = 블록.findall(원문)
        if not 쌍들:
            continue

        이름 = 쪽.relative_to(ROOT).as_posix()
        print(f"[{이름}]  {len(쌍들)}건")

        for 파일경로, 코드html in 쌍들:
            실제 = ROOT / 파일경로
            if not 실제.exists():
                문제.append(f"{이름}: 파일이 없습니다 — {파일경로}")
                틀림 += 1
                continue

            지면 = 벗기기(코드html)
            파일 = 실제.read_text(encoding="utf-8").strip()

            if 지면 == 파일:
                맞음 += 1
            else:
                문제.append(
                    f"{이름}: 내용이 다릅니다 — {파일경로}\n"
                    f"        {첫차이(지면, 파일)}"
                )
                틀림 += 1

    print()
    print("=" * 62)
    if 문제:
        for 줄 in 문제:
            print("  실패  " + 줄)
        print()
        print(f"대조 {맞음 + 틀림}건 — 일치 {맞음}, 차이 {틀림}")
        return 1

    print(f"대조 {맞음}건 전부 일치합니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""검사를 전부 돌립니다.

    python tools/check.py             # 빠른 것만 (몇 초)
    python tools/check.py --all       # 예제 실행 대조까지 (오래 걸립니다)
"""

import subprocess
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent
ROOT = 여기.parent

빠른것 = [
    ("check_book.py",      "상자 최소 개수 · 코드 폭 · SVG 색 · 낡은 문법"),
    ("check_sections.py",  "TOC.md 와 실제 절이 일치하는가"),
    ("check_glossary.py",  "용어가 사전에 있는가"),
    ("check_code_sync.py", "지면 코드 = 저장소 파일"),
    ("check_escaping.py",  "코드 블록이 이스케이프됐는가"),
]
느린것 = [
    ("check_outputs.py",   "지면의 실행 결과 = 실제 출력"),
]


def 돌리기(이름: str) -> tuple[int, str]:
    p = 여기 / 이름
    if not p.exists():
        return 0, "(없음 — 건너뜀)"
    r = subprocess.run(
        [sys.executable, str(p)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    줄 = [x for x in (r.stdout or "").splitlines() if x.strip()]
    끝 = 줄[-1] if 줄 else ""
    if r.returncode != 0:
        실패줄 = [x.strip() for x in 줄 if "실패" in x][:3]
        if 실패줄:
            끝 = " / ".join(실패줄)
    return r.returncode, 끝


def main() -> int:
    목록 = 빠른것 + (느린것 if "--all" in sys.argv else [])
    실패 = 0

    print("=" * 62)
    for 이름, 설명 in 목록:
        코드, 끝 = 돌리기(이름)
        표시 = "통과" if 코드 == 0 else "실패"
        print(f"  [{표시}] {설명}")
        if 코드 != 0:
            print(f"         {끝[:120]}")
            실패 += 1
    print("=" * 62)

    if "--all" not in sys.argv:
        print("  실행 결과 대조는 --all 을 붙여야 돕니다.")

    if 실패:
        print(f"\n{실패}건 실패. 자세히 보려면 그 도구를 직접 돌리십시오.")
        return 1
    print("\n전부 통과했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""TOC.md에 적힌 절이 실제 페이지에 있는지 대조합니다.

장 안의 미니 목차가 없는 절을 가리키면 독자가 클릭했을 때
아무 데도 안 갑니다. TOC.md 를 기준으로 전수 확인합니다.

    python tools/check_sections.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"

쪽패턴 = re.compile(r"^### \[([^\]]+)\]\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\w+)\s*$")
절패턴 = re.compile(r"^- (\d+)\.(\d+)\s")
부록절패턴 = re.compile(r"^- ([A-H])\.(\d+)\s")



def ch숫자(쪽id: str) -> bool:
    """ch01 처럼 ch 뒤에 숫자가 오는 것만 본문 장입니다.

    changelog 도 ch 로 시작하기 때문에 접두사만 보면 안 됩니다.
    """
    return re.match(r"^ch\d", 쪽id) is not None

def 페이지경로(쪽id: str) -> Path:
    if ch숫자(쪽id):
        return ROOT / "chapters" / f"{쪽id}.html"
    if 쪽id.startswith("apx-"):
        return ROOT / "appendix" / f"{쪽id}.html"
    if 쪽id in ("prologue", "howto"):
        return ROOT / "front" / f"{쪽id}.html"
    return ROOT / "back" / f"{쪽id}.html"


def main() -> int:
    현재 = None
    상태 = None
    기대 = {}

    for 줄 in TOC.read_text(encoding="utf-8").splitlines():
        m = 쪽패턴.match(줄)
        if m:
            현재, _, _, 상태 = m.groups()
            기대[현재] = {"상태": 상태, "절": []}
            continue
        if 현재 is None:
            continue
        s = 절패턴.match(줄) or 부록절패턴.match(줄)
        if s:
            기대[현재]["절"].append(f"s{s.group(1)}-{s.group(2)}")

    문제 = []
    확인한쪽 = 0

    for 쪽id, 정보 in 기대.items():
        경로 = 페이지경로(쪽id)
        if not 경로.exists():
            continue                      # 아직 안 쓴 것 — 정상
        확인한쪽 += 1

        원문 = 경로.read_text(encoding="utf-8")
        있는절 = set(
            re.findall(r'<section class="section" id="([^"]+)"', 원문)
        )
        rel = 경로.relative_to(ROOT).as_posix()

        for 절 in 정보["절"]:
            if 절 not in 있는절:
                문제.append(f"{rel}: TOC.md 의 {절} 이 페이지에 없습니다")

        # 페이지 안에서 없는 절을 가리키는 링크
        가리킴 = set(re.findall(r'<li><a href="#(s[\d\w-]+)"', 원문))
        for 절 in sorted(가리킴 - 있는절):
            문제.append(f"{rel}: 미니 목차가 없는 절을 가리킵니다 — #{절}")

    print("=" * 62)
    print(f"쪽 {확인한쪽}개 대조")
    print("=" * 62)

    if 문제:
        for 줄 in sorted(set(문제)):
            print("  실패  " + 줄)
        print(f"\n문제 {len(set(문제))}건")
        return 1

    print("\nTOC.md 와 실제 페이지가 일치합니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""이미 쓴 페이지의 실제 절 제목을 TOC.md 에 되반영합니다.

TOC.md 가 목차의 단일 원본이지만, 글을 쓰다 보면 절을 합치거나
제목을 다듬게 됩니다. 그때 TOC.md 를 안 고치면 사이드바가
없는 절을 가리켜 클릭해도 아무 데도 안 갑니다.

이 도구는 '이미 쓴 페이지'에 한해 TOC.md 를 실제에 맞춥니다.
아직 안 쓴 페이지의 계획은 그대로 둡니다.

    python tools/sync_toc_sections.py          # 무엇이 바뀔지만 보여줍니다
    python tools/sync_toc_sections.py --write  # 실제로 고칩니다
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"

쪽패턴 = re.compile(r"^### \[([^\]]+)\]")
절줄패턴 = re.compile(r"^- (?:\d+|[A-H])\.\d+\s")
절추출 = re.compile(
    # 본문은 s17-3, 부록은 sC-12 처럼 씁니다
    r'<section class="section" id="s[\dA-H-]+">\s*<h2>([^<]+)</h2>'
)



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


def 실제절(쪽id: str) -> list[str] | None:
    경로 = 페이지경로(쪽id)
    if not 경로.exists():
        return None
    원문 = 경로.read_text(encoding="utf-8")
    절들 = [t.strip() for t in 절추출.findall(원문)]
    # HTML 엔티티를 되돌립니다 (제목에 &amp; 같은 것이 있습니다)
    절들 = [
        t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        for t in 절들
    ]
    return 절들 or None


def main() -> int:
    쓰기 = "--write" in sys.argv
    줄들 = TOC.read_text(encoding="utf-8").splitlines()

    결과 = []
    i = 0
    바뀐쪽 = []

    while i < len(줄들):
        줄 = 줄들[i]
        m = 쪽패턴.match(줄)
        if not m:
            결과.append(줄)
            i += 1
            continue

        쪽id = m.group(1)
        결과.append(줄)
        i += 1

        # 표지용 한 줄 설명(> ...)이 있으면 그대로 두고 건너뜁니다
        while i < len(줄들) and 줄들[i].startswith(">"):
            결과.append(줄들[i])
            i += 1

        # 이 쪽에 딸린 기존 절 줄들을 모읍니다
        기존 = []
        while i < len(줄들) and 절줄패턴.match(줄들[i]):
            기존.append(줄들[i])
            i += 1

        새것 = 실제절(쪽id)
        if 새것 is None:
            결과.extend(기존)          # 아직 안 쓴 쪽 — 계획 그대로
            continue

        새줄들 = [f"- {t}" for t in 새것]
        if 새줄들 != 기존:
            바뀐쪽.append((쪽id, len(기존), len(새줄들)))
        결과.extend(새줄들)

    if not 바뀐쪽:
        print("TOC.md 가 이미 실제와 일치합니다")
        return 0

    print("=" * 62)
    print("TOC.md 를 실제 페이지에 맞춥니다")
    print("=" * 62)
    for 쪽id, 전, 후 in 바뀐쪽:
        표시 = f"{전}절 → {후}절" if 전 != 후 else f"{후}절 (제목만 다름)"
        print(f"  {쪽id:18} {표시}")

    if not 쓰기:
        print("\n실제로 고치려면 --write 를 붙이십시오")
        return 0

    TOC.write_text("\n".join(결과) + "\n", encoding="utf-8")
    print(f"\n{len(바뀐쪽)}개 쪽을 갱신했습니다")
    print("이어서 python tools/build_toc.py 를 돌리십시오")
    return 0


if __name__ == "__main__":
    sys.exit(main())

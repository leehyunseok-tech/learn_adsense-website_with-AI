"""본문의 .keyword 용어가 부록 H에 실제로 있는지 대조합니다.

book.js 가 용어를 부록 H 앵커로 자동 연결하므로,
사전에 항목이 없으면 링크가 헛돕니다. 그것을 미리 잡습니다.

    python tools/check_glossary.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
사전경로 = ROOT / "appendix" / "apx-h-glossary.html"

용어패턴 = re.compile(r'<span class="keyword" data-term="([^"]+)"')
항목패턴 = re.compile(r'<div class="glossary__item" id="t-([^"]+)"')
색인패턴 = re.compile(r'<a href="#t-([^"]+)">')


def 앵커(용어: str) -> str:
    """book.js 의 규칙과 같아야 합니다."""
    return re.sub(r"\s+", "-", 용어.strip())


def main() -> int:
    if not 사전경로.exists():
        print("부록 H 가 아직 없습니다 — 대조를 건너뜁니다")
        return 0

    사전 = 사전경로.read_text(encoding="utf-8")
    있는것 = set(항목패턴.findall(사전))
    색인 = set(색인패턴.findall(사전))

    쓰인것 = {}
    for 쪽 in sorted(ROOT.glob("chapters/*.html")):
        for 용어 in 용어패턴.findall(쪽.read_text(encoding="utf-8")):
            쓰인것.setdefault(용어, []).append(쪽.stem)

    문제 = []

    for 용어, 장들 in sorted(쓰인것.items()):
        a = 앵커(용어)
        if a not in 있는것:
            문제.append(f"사전에 없습니다 — '{용어}' ({장들[0]}에서 씀)")

    # 색인과 항목이 어긋나는지도 봅니다
    for a in sorted(있는것 - 색인):
        문제.append(f"항목은 있는데 위쪽 색인에 없습니다 — '{a}'")
    for a in sorted(색인 - 있는것):
        문제.append(f"색인에는 있는데 항목이 없습니다 — '{a}'")

    print("=" * 62)
    print(f"본문에 쓰인 용어 {len(쓰인것)}개 · 사전 항목 {len(있는것)}개")
    print("=" * 62)

    if 문제:
        for 줄 in 문제:
            print("  실패  " + 줄)
        print(f"\n문제 {len(문제)}건")
        return 1

    안쓴것 = sorted(있는것 - {앵커(t) for t in 쓰인것})
    if 안쓴것:
        print(f"  참고  본문에서 아직 안 쓴 항목 {len(안쓴것)}개 — "
              + ", ".join(안쓴것))
    print("\n전부 이어집니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

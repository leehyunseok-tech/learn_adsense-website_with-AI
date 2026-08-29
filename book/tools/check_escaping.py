"""코드·프롬프트 블록 안의 HTML 이 이스케이프됐는지 검사합니다.

프롬프트에 HTML 조각을 보여줄 때 &lt; 로 바꾸지 않으면
브라우저가 진짜 태그로 해석합니다. 그러면 독자에게는
태그가 아예 안 보이고, 프롬프트의 요점이 사라집니다.

19장에서 실제로 이런 일이 있어 만든 검사입니다.

    python tools/check_escaping.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

블록 = re.compile(
    r'<div class="ai-prompt__text">(.*?)</div>|'
    r'<div class="example__code"[^>]*>\s*<pre>(.*?)</pre>',
    re.DOTALL,
)

# 문법 강조용 span 은 우리가 넣은 것이라 정상입니다
강조 = re.compile(r"</?span[^>]*>")
태그 = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")


def 쪽들() -> list[Path]:
    모음 = []
    for 폴더 in ("front", "chapters", "appendix", "back"):
        모음 += sorted((ROOT / 폴더).glob("*.html"))
    return 모음


def main() -> int:
    문제 = []
    검사한블록 = 0

    for 쪽 in 쪽들():
        원문 = 쪽.read_text(encoding="utf-8")
        rel = 쪽.relative_to(ROOT).as_posix()

        for m in 블록.finditer(원문):
            덩어리 = m.group(1) or m.group(2) or ""
            검사한블록 += 1

            남은 = 강조.sub("", 덩어리)
            찾은 = sorted(set(태그.findall(남은)))
            if 찾은:
                줄 = 원문[: m.start()].count("\n") + 1
                문제.append(
                    f"{rel}:{줄} — 이스케이프 안 된 태그 {찾은}\n"
                    f"          &lt; 와 &gt; 로 바꾸십시오"
                )

    print("=" * 62)
    print(f"코드·프롬프트 블록 {검사한블록}개 검사")
    print("=" * 62)

    if 문제:
        for 줄 in 문제:
            print("  실패  " + 줄)
        print(f"\n문제 {len(문제)}건")
        return 1

    print("전부 제대로 이스케이프됐습니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

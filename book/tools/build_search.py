"""검색 색인을 만듭니다.

각 페이지에서 장 제목·절 제목·상자 제목을 뽑아
assets/search-index.js 를 만들고, 모든 페이지에 그 파일을 읽는
script 태그를 넣습니다.

왜 .json 이 아니라 .js 인가 —
파일을 직접 열면(file://) 브라우저가 fetch 를 막습니다.
script 태그는 막지 않습니다. 이 책은 서버 없이 열려야 하므로
.js 로 만들어 전역 변수에 담습니다.

    python tools/build_search.py
"""

import html as htmlmod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
색인파일 = ROOT / "assets" / "search-index.js"

표시 = "<!-- BUILD:SEARCH -->"
넣을것 = '{표시}\n<script src="{뿌리}assets/search-index.js"></script>'


def 글만(덩어리: str) -> str:
    """태그를 걷어내고 공백을 정리합니다."""
    글 = re.sub(r"<[^>]+>", " ", 덩어리)
    글 = htmlmod.unescape(글)
    return re.sub(r"\s+", " ", 글).strip()


def 쪽들() -> list[Path]:
    모음 = []
    for 폴더 in ("front", "chapters", "appendix", "back"):
        모음 += sorted((ROOT / 폴더).glob("*.html"))
    return 모음


def 뽑기(쪽: Path) -> list[dict]:
    원문 = 쪽.read_text(encoding="utf-8")
    상대 = 쪽.relative_to(ROOT).as_posix()

    제목m = re.search(r'<h1 class="chapter-hero__title">(.*?)</h1>', 원문, re.DOTALL)
    장제목 = 글만(제목m.group(1)) if 제목m else 쪽.stem

    부m = re.search(r'<p class="chapter-hero__part">(.*?)</p>', 원문, re.DOTALL)
    부 = 글만(부m.group(1)) if 부m else ""

    번호m = re.search(r'<span class="chapter-hero__num">(.*?)</span>', 원문, re.DOTALL)
    번호 = 글만(번호m.group(1)) if 번호m else ""

    항목들 = []

    # ① 페이지 자체
    항목들.append({
        "u": 상대,
        "t": (f"{번호}. {장제목}" if 번호.isdigit() else 장제목),
        "c": 부,
        "b": "",
    })

    # ② 절
    for 절id, 절제목덩어리 in re.findall(
        r'<section class="section" id="([^"]+)">\s*<h2>(.*?)</h2>', 원문, re.DOTALL
    ):
        항목들.append({
            "u": f"{상대}#{절id}",
            "t": 글만(절제목덩어리),
            "c": 장제목,
            "b": "",
        })

    # ③ 눈에 띄는 상자 — 제목만 담습니다
    상자패턴 = [
        (r'<p class="pitfall__title">(.*?)</p>', "함정"),
        (r'<p class="ai-trap__title">(.*?)</p>', "AI 함정"),
        (r'<p class="concept__title">(.*?)</p>', "개념"),
        (r'<p class="analogy__title">(.*?)</p>', "비유"),
        (r'<figcaption class="figure__caption">(.*?)</figcaption>', "그림"),
    ]
    for 패턴, 종류 in 상자패턴:
        for 덩어리 in re.findall(패턴, 원문, re.DOTALL):
            제목 = 글만(덩어리)
            # 라벨과 아이콘 흔적을 걷어냅니다
            제목 = re.sub(r"^\[[^\]]+\]\s*", "", 제목)
            제목 = re.sub(r"^[^\w가-힣]+", "", 제목).strip()
            if len(제목) < 3:
                continue
            항목들.append({
                "u": 상대,
                "t": 제목,
                "c": f"{장제목} · {종류}",
                "b": 종류,
            })

    # ④ 용어 사전 항목
    for 앵커, 용어덩어리 in re.findall(
        r'<div class="glossary__item" id="(t-[^"]+)">\s*<dt>(.*?)</dt>', 원문, re.DOTALL
    ):
        항목들.append({
            "u": f"{상대}#{앵커}",
            "t": 글만(용어덩어리),
            "c": "용어 사전",
            "b": "용어",
        })

    # ⑤ 에러 카드
    for 앵커, 이름덩어리 in re.findall(
        r'<div class="errcard" id="(e-[^"]+)">\s*<p class="errcard__name">(.*?)</p>',
        원문, re.DOTALL
    ):
        항목들.append({
            "u": f"{상대}#{앵커}",
            "t": 글만(이름덩어리),
            "c": "에러 사전",
            "b": "에러 error",
        })

    return 항목들


def 스크립트넣기(쪽: Path) -> bool:
    """페이지에 색인 파일을 읽는 script 태그를 넣습니다."""
    원문 = 쪽.read_text(encoding="utf-8")
    뿌리 = "../" if 쪽.parent != ROOT else ""

    새줄 = 넣을것.format(표시=표시, 뿌리=뿌리)

    if 표시 in 원문:
        새원문 = re.sub(
            re.escape(표시) + r'\n<script src="[^"]*search-index\.js"></script>',
            새줄, 원문
        )
    else:
        # book.js 바로 앞에 넣습니다 — 색인이 먼저 읽혀야 합니다
        찾을것 = re.search(r'<script src="([^"]*)book\.js"></script>', 원문)
        if not 찾을것:
            return False
        새원문 = 원문.replace(찾을것.group(0), 새줄 + "\n" + 찾을것.group(0))

    if 새원문 != 원문:
        쪽.write_text(새원문, encoding="utf-8")
        return True
    return False


def main() -> int:
    항목 = []
    for 쪽 in 쪽들():
        항목 += 뽑기(쪽)

    # index.html 도 넣습니다
    표지 = ROOT / "index.html"
    if 표지.exists():
        항목.insert(0, {
            "u": "index.html",
            "t": "표지와 전체 목차",
            "c": "",
            "b": "목차 index 처음",
        })

    # 같은 곳을 가리키는 중복 제목을 걷어냅니다
    본것 = set()
    깔끔 = []
    for it in 항목:
        열쇠 = (it["u"], it["t"])
        if 열쇠 in 본것:
            continue
        본것.add(열쇠)
        깔끔.append(it)

    본문 = json.dumps(깔끔, ensure_ascii=False, separators=(",", ":"))
    색인파일.parent.mkdir(exist_ok=True)
    색인파일.write_text(
        "/* 자동 생성 파일입니다. tools/build_search.py 가 만듭니다.\n"
        "   손으로 고치지 마십시오. */\n"
        f"window.PYBOOK_SEARCH = {본문};\n",
        encoding="utf-8",
    )

    넣은쪽 = sum(스크립트넣기(쪽) for 쪽 in 쪽들())
    if 표지.exists():
        넣은쪽 += 스크립트넣기(표지)

    크기 = 색인파일.stat().st_size
    print("=" * 62)
    print(f"검색 색인 {len(깔끔)}개 항목  ({크기 / 1024:.1f} KB)")
    print(f"script 태그를 넣은 쪽: {넣은쪽}개")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""전권 합본을 A4 PDF 로 뽑습니다.

브라우저의 인쇄 기능을 헤드리스로 부릅니다.
설치할 파이썬 패키지가 없습니다 — 크롬이나 엣지만 있으면 됩니다.

    python tools/build_pdf.py            # print.html -> book.pdf
    python tools/build_pdf.py --pages    # 쪽수와 용지 크기만 확인

먼저 build_print.py 로 print.html 을 만들어 두어야 합니다.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
합본 = ROOT / "print.html"
결과 = ROOT / "book.pdf"

# 흔한 설치 위치. 앞에서부터 찾습니다.
후보 = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def 브라우저찾기() -> str | None:
    for 이름 in ("chrome", "chromium", "google-chrome", "msedge"):
        찾음 = shutil.which(이름)
        if 찾음:
            return 찾음
    for 길 in 후보:
        if Path(길).exists():
            return 길
    return None


def 파일주소(p: Path) -> str:
    return p.resolve().as_uri()


def 쪽수와용지(pdf: Path) -> tuple[int, str]:
    raw = pdf.read_bytes()
    n = len(re.findall(rb"/Type\s*/Page\b", raw))
    m = re.search(rb"/MediaBox\s*\[\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", raw)
    용지 = "알 수 없음"
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        mmw, mmh = w / 72 * 25.4, h / 72 * 25.4
        이름 = "A4" if abs(mmw - 210) < 2 and abs(mmh - 297) < 2 else "비표준"
        용지 = f"{mmw:.0f} x {mmh:.0f} mm ({이름})"
    return n, 용지


def main() -> int:
    if "--pages" in sys.argv:
        if not 결과.exists():
            print("book.pdf 가 없습니다. 먼저 인자 없이 실행하십시오.")
            return 1
        n, 용지 = 쪽수와용지(결과)
        print(f"{n}쪽 · {용지} · {결과.stat().st_size / 1024 / 1024:.1f} MB")
        return 0

    if not 합본.exists():
        print("print.html 이 없습니다. 먼저 이것부터 돌리십시오:")
        print("    python tools/build_print.py")
        return 1

    브라우저 = 브라우저찾기()
    if not 브라우저:
        print("크롬이나 엣지를 못 찾았습니다.")
        print("설치했는데도 이 메시지가 나오면 아래를 직접 고치십시오:")
        print(f"    {Path(__file__).name} 의 '후보' 목록")
        return 1

    결과.unlink(missing_ok=True)
    print(f"브라우저: {브라우저}")
    print("PDF 를 만듭니다. 쪽이 많으면 1~2분 걸립니다...")

    명령 = [
        브라우저,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",      # 머리글·바닥글의 URL 과 쪽번호를 뺍니다
        f"--print-to-pdf={결과}",
        파일주소(합본),
    ]
    r = subprocess.run(명령, capture_output=True, text=True, timeout=900)

    if not 결과.exists():
        print("PDF 가 안 만들어졌습니다.")
        print((r.stderr or "")[-800:])
        return 1

    n, 용지 = 쪽수와용지(결과)
    크기 = 결과.stat().st_size / 1024 / 1024

    print("=" * 62)
    print(f"book.pdf — {n}쪽 · {용지} · {크기:.1f} MB")
    print("=" * 62)

    if "비표준" in 용지:
        print("  주의: A4 가 아닙니다. book.css 의 @page size 를 확인하십시오.")

    # 쪽당 글자수가 너무 적으면 여백이 낭비되고 있다는 뜻입니다.
    글자 = 본문글자수()
    # 내용이 어느 정도 찬 뒤라야 의미 있는 신호입니다.
    # 뼈대만 있는 책은 원래 글자가 적습니다.
    if n and 글자 > 20000:
        쪽당 = 글자 // n
        print(f"  쪽당 약 {쪽당:,}자", end="")
        if 쪽당 < 800:
            print("  <- 너무 적습니다. 인쇄 CSS 를 의심하십시오.")
            print("     크기가 안 정해진 아이콘이나 넉넉한 여백이 흔한 원인입니다.")
        else:
            print("  (A4 10.5pt 기준 1,000~1,600자면 적정)")
    return 0


def 본문글자수() -> int:
    총 = 0
    for 폴더 in ("front", "chapters", "appendix", "back"):
        for 쪽 in (ROOT / 폴더).glob("*.html"):
            t = 쪽.read_text(encoding="utf-8")
            m = re.search(r'<main class="chapter-body" id="main">(.*?)</main>', t, re.S)
            if not m:
                continue
            글 = re.sub(r"<[^>]+>", " ", m.group(1))
            총 += len(re.sub(r"\s+", " ", 글).strip())
    return 총


if __name__ == "__main__":
    sys.exit(main())

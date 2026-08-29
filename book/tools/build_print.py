"""전권 합본 print.html 을 만듭니다.

35쪽을 하나의 파일로 이어 붙입니다. 브라우저에서 열어
한 번에 인쇄하거나 PDF 로 뽑기 위한 것입니다.

화면용 요소(사이드바·헤더·검색창·이전다음)는 빼고,
본문과 오른쪽 목록만 남깁니다.

    python tools/build_print.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"
결과파일 = ROOT / "print.html"


def 설정() -> dict:
    p = ROOT / "book.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

쪽패턴 = re.compile(r"^### \[([^\]]+)\]\s*(.+?)\s*\|\s*(\d+)\s*\|")
부패턴 = re.compile(r"^## (.+)$")



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


def 본문뽑기(쪽: Path) -> str:
    """main 안쪽만 꺼내고, 경로를 합본 기준으로 고칩니다."""
    원문 = 쪽.read_text(encoding="utf-8")

    m = re.search(r'<main class="chapter-body" id="main">(.*?)</main>', 원문, re.DOTALL)
    if not m:
        return ""
    본문 = m.group(1)

    # 오른쪽 목록도 살립니다 (인쇄에서는 CSS 가 알아서 처리합니다)
    r = re.search(r'<aside class="rail".*?</aside>', 원문, re.DOTALL)
    레일 = r.group(0) if r else ""

    폴더 = 쪽.parent.name

    쪽이름 = 쪽.stem

    # 어느 쪽으로 이어지는 링크인지 미리 알아 둡니다
    쪽번호 = {}
    for 폴더이름 in ("front", "chapters", "appendix", "back"):
        for p in (ROOT / 폴더이름).glob("*.html"):
            쪽번호[p.name] = p.stem

    def 경로고치기(글: str) -> str:
        """다른 쪽으로 가는 링크를 합본 안의 앵커로 바꿉니다.

        합본은 한 파일이므로 chapters/ch08.html#s8-2 같은 링크는
        #ch08--s8-2 로 가야 합니다.
        """
        def 바꾸기(m):
            앞, 주소 = m.group(1), m.group(2)

            # 같은 쪽 안의 앵커 — 접두사만 붙입니다
            if 주소.startswith("#"):
                return f'{앞}="#{쪽이름}--{주소[1:]}"'

            # 바깥 주소나 절대경로는 그대로 둡니다
            if 주소.startswith(("http", "mailto:", "/")):
                return m.group(0)

            경로, _, 앵커 = 주소.partition("#")
            파일이름 = Path(경로).name

            # 책의 다른 쪽이면 합본 안의 앵커로
            if 파일이름 in 쪽번호:
                대상 = 쪽번호[파일이름]
                return f'{앞}="#{대상}--{앵커}"' if 앵커 else f'{앞}="#{대상}"'

            # index.html 은 합본 밖에 있으므로 그대로 (경로만 정리)
            if 주소.startswith("../"):
                return f'{앞}="{주소[3:]}"'
            return f'{앞}="{폴더}/{주소}"'

        return re.sub(r'(href|src)="([^"]*)"', 바꾸기, 글)

    def id고치기(글: str) -> str:
        """같은 id 가 두 번 나오지 않게 쪽 이름을 앞에 붙입니다."""
        return re.sub(
            r'\bid="((?:s[\dA-H]|fig-|ex-|t-|e-)[^"]*)"',
            rf'id="{쪽이름}--\1"',
            글,
        )

    # 순서가 중요합니다 — id 를 먼저 바꾸면 링크가 못 따라옵니다
    본문 = id고치기(경로고치기(본문))
    레일 = id고치기(경로고치기(레일))

    return (f'<article class="print-page" id="{쪽이름}">\n'
            f'{본문}\n{레일}\n</article>\n')


def main() -> int:
    현재부 = None
    조각들 = []
    쪽수 = 0
    빠진쪽 = []

    for 줄 in TOC.read_text(encoding="utf-8").splitlines():
        b = 부패턴.match(줄)
        if b and not 줄.startswith("## 파싱"):
            현재부 = b.group(1).strip()
            continue

        m = 쪽패턴.match(줄)
        if not m:
            continue

        쪽id, 제목, _ = m.groups()
        경로 = 페이지경로(쪽id)
        if not 경로.exists():
            빠진쪽.append(쪽id)
            continue

        if 현재부:
            조각들.append(
                f'<div class="print-part"><p>{현재부}</p></div>\n'
            )
            현재부 = None

        덩어리 = 본문뽑기(경로)
        if not 덩어리:
            빠진쪽.append(f"{쪽id} (main 을 못 찾음)")
            continue
        조각들.append(덩어리)
        쪽수 += 1

    conf = 설정()
    제목 = conf.get("title") or "책"
    부제 = conf.get("subtitle") or ""

    머리 = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — 전권</title>
<meta name="description" content="__PAGES__쪽 전권 합본. 브라우저에서 한 번에 인쇄하거나 PDF로 뽑기 위한 것입니다.">
<link rel="stylesheet" href="assets/book.css">
<style>
  /* 합본 전용 — 화면에서 볼 때의 최소 꾸밈 */
  body.printbook { background: var(--bg); }
  .print-cover {
    max-width: 68ch; margin: 0 auto; padding: 18vh 24px 12vh;
    text-align: center;
  }
  .print-cover h1 { font-size: 2.25rem; line-height: 1.35; margin-bottom: 12px; }
  .print-cover p { color: var(--fg-muted); }
  .print-cover .print-cover__note {
    margin-top: 40px; padding: 16px; border: 1px solid var(--border);
    border-radius: 10px; font-size: 0.9375rem; text-align: left;
  }
  .print-part {
    max-width: 68ch; margin: 0 auto; padding: 60px 24px 20px;
    border-bottom: 2px solid var(--border-strong);
  }
  .print-part p {
    font-size: 1.375rem; font-weight: 700; letter-spacing: -0.01em;
  }
  .print-page { padding-bottom: 40px; }
  .printbook .chapter-body { max-width: 68ch; margin: 0 auto; padding: 0 24px; }
  .printbook .rail { display: none; }

  @media print {
    .print-cover { break-after: page; padding: 30vh 0 0; }
    .print-part  { break-before: page; break-after: avoid; border: none; }
    .print-page  { padding-bottom: 0; }
    .print-cover__note { display: none; }

    /* 장마다 강제로 새 쪽을 시작시키면(break-before: page),
       앞 장의 next-preview 상자 하나만 겨우 넘어간 직후 이 장이
       또 새 쪽을 강제해서 거의 빈 쪽이 남는 경우가 잦다. 대신
       장은 굵은 위 테두리와 넉넉한 위 여백만으로 구분하고,
       남은 공간이 있으면 그대로 이어 붙인다. */
    .print-page + .print-page { break-before: auto; }
    .print-page .chapter-hero {
      break-before: auto !important;
      break-inside: avoid;
      margin-top: 28pt; padding-top: 18pt; border-top: 2pt solid #000;
    }

    /* 부 표지 다음 쪽은 항상 새 쪽에서 시작한다 */
    .print-part + .print-page { break-before: auto; }
    .print-part + .print-page .chapter-hero {
      margin-top: 0; padding-top: 0; border-top: none;
    }
  }
</style>
</head>
<body class="printbook" data-root="">

<div class="print-cover">
  <h1>__TITLE__</h1>
  <p>__SUBTITLE__</p>
  <div class="print-cover__note">
    <p><strong>이 파일은 전권 합본입니다.</strong>
       __PAGES__쪽을 하나로 이어 붙였습니다.</p>
    <p style="margin-top:8px">
       브라우저의 <strong>인쇄(Ctrl+P)</strong>에서
       <strong>용지 A4</strong>, <strong>배경 그래픽 켜기</strong>를 고르면
       책 모양으로 나옵니다. 이 안내는 인쇄되지 않습니다.</p>
    <p style="margin-top:8px">
       한 쪽씩 읽으시려면
       <a href="index.html">표지와 전체 목차</a>로 가십시오.</p>
  </div>
</div>

"""

    꼬리 = """
<footer class="book-footer">
  <p>__TITLE__</p>
</footer>

<script src="assets/book.js"></script>
</body>
</html>
"""

    def 채우기(글: str) -> str:
        return (
            글.replace("__TITLE__", 제목)
              .replace("__SUBTITLE__", 부제 or 제목)
              .replace("__PAGES__", str(쪽수))
        )

    결과파일.write_text(채우기(머리) + "".join(조각들) + 채우기(꼬리), encoding="utf-8")

    크기 = 결과파일.stat().st_size
    print("=" * 62)
    print(f"print.html — {쪽수}쪽을 합쳤습니다  ({크기 / 1024:.0f} KB)")
    if 빠진쪽:
        print(f"  빠진 쪽: {', '.join(빠진쪽)}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())

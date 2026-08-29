"""지면에 실은 실행 결과가 진짜 출력과 같은지 대조합니다.

책에 적힌 출력을 손으로 옮기다 보면 숫자 하나가 틀립니다.
독자는 그대로 따라 하는데 결과가 다르면 자기가 틀린 줄 압니다.
그래서 기계로 맞춰 봅니다.

data-file 이 붙은 코드 블록 바로 뒤에 실행 결과가 있으면,
그 파일을 실제로 돌려 비교합니다.

    python tools/check_outputs.py            # 전부
    python tools/check_outputs.py apx-c      # 이름에 apx-c 가 든 것만
"""

import html as htmlmod
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

코드시작 = re.compile(
    r'<div class="example__code"[^>]*data-file="([^"]+)"[^>]*>'
)
출력시작 = re.compile(
    r'^\s*<div class="example__output" data-expected="true">\s*'
    r'<span class="example__output-label">[^<]*</span>\s*<pre>'
)


def 벗기기(덩어리: str) -> str:
    글 = re.sub(r"<[^>]+>", "", 덩어리)
    return htmlmod.unescape(글)


def 다듬기(글: str) -> list[str]:
    """줄 끝 공백만 걷어냅니다. 가운데 정렬은 그대로 봅니다."""
    return [줄.rstrip() for 줄 in 글.strip().splitlines()]


def 쌍찾기(원문: str) -> list[tuple[str, str]]:
    """코드 블록과 '바로 뒤에 붙은' 출력 블록만 짝지어 돌려줍니다.

    정규식 하나로 하면 예제 경계를 넘어가 엉뚱한 출력을 잡습니다.
    그래서 위치를 따라가며 확인합니다.
    """
    쌍들 = []
    for m in 코드시작.finditer(원문):
        파일경로 = m.group(1)

        끝pre = 원문.find("</pre>", m.end())
        if 끝pre == -1:
            continue
        끝div = 원문.find("</div>", 끝pre)
        if 끝div == -1:
            continue

        뒤 = 원문[끝div + len("</div>"):]
        o = 출력시작.match(뒤)
        if not o:
            continue                      # 실행 결과가 없는 예제 — 넘어갑니다

        출력끝 = 뒤.find("</pre>", o.end())
        if 출력끝 == -1:
            continue
        쌍들.append((파일경로, 뒤[o.end():출력끝]))

    return 쌍들


생략표시 = "⋯"


def 생략맞추기(지면: list[str], 진짜: list[str]) -> bool:
    """지면에 ⋯ 이 있으면 그 자리에서 몇 줄이 빠진 것으로 봅니다.

    트레이스백처럼 가운데가 길고 덜 중요한 출력을 실을 때 씁니다.
    앞 토막은 처음부터, 뒤 토막은 끝까지 정확히 맞아야 합니다.
    """
    if 생략표시 not in 지면:
        return False

    토막들 = []
    현재 = []
    for 줄 in 지면:
        if 줄.strip() == 생략표시:
            토막들.append(현재)
            현재 = []
        else:
            현재.append(줄)
    토막들.append(현재)

    위치 = 0
    for i, 토막 in enumerate(토막들):
        if not 토막:
            continue
        if i == 0:
            if 진짜[:len(토막)] != 토막:
                return False
            위치 = len(토막)
        elif i == len(토막들) - 1:
            if 진짜[-len(토막):] != 토막:
                return False
        else:
            # 가운데 토막은 순서만 맞으면 됩니다
            for j in range(위치, len(진짜) - len(토막) + 1):
                if 진짜[j:j + len(토막)] == 토막:
                    위치 = j + len(토막)
                    break
            else:
                return False
    return True


def 인자가필요한가(파일: Path) -> bool:
    """sys.argv 를 쓰는 스크립트는 인자 없이 돌리면 다른 결과가 나옵니다."""
    글 = 파일.read_text(encoding="utf-8")
    return "sys.argv" in 글


def 생성물치우기(폴더: Path) -> list[str]:
    """.gitignore 에 적힌 생성물을 지웁니다.

    돌리면 파일을 남기는 예제가 있습니다. 그대로 두면 다음 검사에서
    "새 기사 0건" 처럼 다른 결과가 나옵니다. 독자가 저장소를 처음
    받았을 때와 같은 상태에서 돌려야 지면과 맞습니다.

    code/ 안에서만, .gitignore 에 이름이 적힌 파일만 지웁니다.
    """
    무시파일 = 폴더 / ".gitignore"
    if not 무시파일.exists():
        return []
    if ROOT / "code" not in 폴더.parents and 폴더 != ROOT / "code":
        return []

    지운것 = []
    for 줄 in 무시파일.read_text(encoding="utf-8").splitlines():
        패턴 = 줄.strip()
        if not 패턴 or 패턴.startswith("#") or 패턴.endswith("/"):
            continue
        for 대상 in 폴더.glob(패턴):
            if 대상.is_file():
                대상.unlink()
                지운것.append(대상.name)
    return 지운것


def 돌리기(파일: Path) -> str:
    """표준 출력과 표준 오류를 합쳐 돌려줍니다.

    일부러 에러를 내는 예제가 있어서 트레이스백도 봐야 합니다.
    """
    생성물치우기(파일.parent)
    결과 = subprocess.run(
        [sys.executable, 파일.name],
        cwd=파일.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=180,
    )
    return 결과.stdout + 결과.stderr


def main() -> int:
    거르기 = sys.argv[1] if len(sys.argv) > 1 else ""

    쪽들 = sorted(ROOT.glob("chapters/*.html")) + sorted(ROOT.glob("appendix/*.html"))
    맞음 = 틀림 = 건너뜀 = 0
    문제 = []

    for 쪽 in 쪽들:
        if 거르기 and 거르기 not in 쪽.stem:
            continue

        원문 = 쪽.read_text(encoding="utf-8")
        쌍들 = 쌍찾기(원문)
        if not 쌍들:
            continue

        이름 = 쪽.relative_to(ROOT).as_posix()
        print(f"[{이름}]  {len(쌍들)}쌍")

        for 파일경로, 출력덩어리 in 쌍들:
            실제파일 = ROOT / 파일경로
            보일이름 = Path(파일경로).name

            if not 실제파일.exists():
                문제.append(f"{이름}: 파일 없음 — {파일경로}")
                틀림 += 1
                continue

            if 인자가필요한가(실제파일):
                print(f"    넘김  {보일이름} (실행 인자가 필요합니다)")
                건너뜀 += 1
                continue

            지면 = 다듬기(벗기기(출력덩어리))
            진짜 = 다듬기(돌리기(실제파일))

            if 지면 == 진짜:
                맞음 += 1
                print(f"    일치  {보일이름}")
                continue

            # 지면이 앞부분만 실은 경우는 문제가 아닙니다
            if len(진짜) > len(지면) and 진짜[:len(지면)] == 지면:
                맞음 += 1
                print(f"    일치  {보일이름} (앞부분만 실림)")
                continue

            # 끝부분만 실은 경우도 인정합니다.
            # 에러를 보여주는 예제는 트레이스백 대신 마지막 메시지 줄만
            # 싣는 편이 읽기 좋습니다.
            if len(진짜) > len(지면) and 진짜[-len(지면):] == 지면:
                맞음 += 1
                print(f"    일치  {보일이름} (끝부분만 실림)")
                continue

            # 가운데를 생략한 경우 — 지면에 ⋯ 한 줄을 두면 됩니다
            if 생략맞추기(지면, 진짜):
                맞음 += 1
                print(f"    일치  {보일이름} (가운데 생략)")
                continue

            어긋난줄 = "끝까지 같은데 길이가 다릅니다"
            for i, 줄 in enumerate(지면):
                if i >= len(진짜):
                    어긋난줄 = f"{i + 1}행 — 지면에만 있는 줄: {줄!r}"
                    break
                if 줄 != 진짜[i]:
                    어긋난줄 = (f"{i + 1}행\n          지면: {줄!r}"
                              f"\n          실제: {진짜[i]!r}")
                    break

            문제.append(f"{이름}: {보일이름} 출력이 다릅니다 — {어긋난줄}")
            틀림 += 1
            print(f"    차이  {보일이름}")

    print()
    print("=" * 62)
    if 문제:
        for 줄 in 문제:
            print("  실패  " + 줄)
        print(f"\n대조 {맞음 + 틀림}쌍 — 일치 {맞음}, 차이 {틀림}, 넘김 {건너뜀}")
        return 1

    print(f"대조 {맞음}쌍 전부 일치합니다 (인자가 필요해 넘긴 것 {건너뜀}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

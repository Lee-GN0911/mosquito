"""기상청 ASOS 서울(108) 일자료를 연도별 원문으로 수집한다."""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import time

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
OUT = ROOT / "data" / "raw" / "weather_api"
URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd3.php"


def auth_key():
    if not ENV.exists():
        raise SystemExit("오류: mosquito 폴더에 .env 파일이 없습니다.")
    for raw in ENV.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = raw.strip().partition("=")
        if sep and key.strip() == "KMA_AUTH_KEY" and value.strip():
            return value.strip().strip("\"'")
    raise SystemExit("오류: .env에 KMA_AUTH_KEY=인증키 형식으로 입력해주세요.")


def fetch(year, key):
    query = urlencode({"tm1": f"{year}0101", "tm2": f"{year}1231",
                       "stn": 108, "disp": 0, "help": 1, "authKey": key})
    req = Request(f"{URL}?{query}", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=90) as response:
        body = response.read()
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"{year}년 응답의 문자 인코딩을 판별하지 못했습니다.")


def main():
    key = auth_key()
    OUT.mkdir(parents=True, exist_ok=True)
    for year in range(2008, 2024):
        print(f"{year}년 다운로드 중...", flush=True)
        text = fetch(year, key)
        if "#START7777" not in text or "#7777END" not in text:
            raise RuntimeError(f"{year}년 응답이 관측자료 형식이 아닙니다.\n{text[:500]}")
        (OUT / f"seoul_asos_{year}.txt").write_text(text, encoding="utf-8")
        print("  저장 완료", flush=True)
        time.sleep(.5)
    print("\n완료: data\\raw\\weather_api에 16개 원자료가 저장됐습니다.")


if __name__ == "__main__":
    main()

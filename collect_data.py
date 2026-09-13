"""이미 포함된 서울시 공식 모기 원본을 다시 확보할 때만 실행한다."""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
import io
import zipfile

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "data/raw/mosquito_2008_2023.xlsx"
SOURCE = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false"
EXPECTED = "ceca3280e49b607d15ed0851818c8f6a813c7622b8c9463451b28cdc2ad535ea"


def main():
    if TARGET.exists():
        print("원본이 이미 있습니다. 기존 파일을 보존합니다.")
        return
    data = urlencode({"infId": "OA-22301", "seqNo": "", "seq": "823", "infSeq": "1"}).encode()
    request = Request(SOURCE, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(request, timeout=30) as response:
        content = response.read()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if archive.testzip() is not None or "xl/workbook.xml" not in archive.namelist():
            raise ValueError("정상적인 엑셀 파일이 아닙니다.")
    if hashlib.sha256(content).hexdigest() != EXPECTED:
        raise ValueError("제공기관 원본이 변경되었습니다. 기존 분석과 비교하기 전에 내용을 확인해야 합니다.")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(content)
    print("공식 원본 다운로드와 파일 검증을 완료했습니다.")


if __name__ == "__main__":
    main()

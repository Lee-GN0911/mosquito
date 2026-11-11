"""우주 발사·비용·유인비행 원자료를 내려받는다.

실행: python collect_data.py
받은 파일은 data/raw 에 그대로 저장하고, 출처와 받은 시각을 sources.json 에 남긴다.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data/raw"

SOURCES = {
    "launch.tsv": {
        "url": "https://planet4589.org/space/gcat/tsv/launch/launch.tsv",
        "name": "GCAT 발사 목록 (Jonathan McDowell)",
        "note": "1942년 이후 모든 로켓 발사. LaunchCode 첫 글자 O = 궤도 발사",
    },
    "missions.tsv": {
        "url": "https://planet4589.org/space/astro/tsv/missions.tsv",
        "name": "유인 우주비행 임무 목록 (Jonathan McDowell)",
        "note": "80km 이상 도달한 유인비행. OrbID가 ORB = 궤도, SO = 준궤도",
    },
    "rides.tsv": {
        "url": "https://planet4589.org/space/astro/tsv/rides.tsv",
        "name": "유인 우주비행 탑승자 목록 (Jonathan McDowell)",
        "note": "한 사람이 한 번 비행할 때마다 한 줄",
    },
    "owid_launch_cost.csv": {
        "url": "https://ourworldindata.org/grapher/cost-space-launches-low-earth-orbit.csv"
               "?v=1&csvType=full&useColumnShortNames=false",
        "name": "저궤도 발사 비용 (Our World in Data, 원자료 CSIS Aerospace Security)",
        "note": "로켓별 kg당 비용, 2021년 미국 달러 기준, 첫 성공 발사 연도",
    },
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    for filename, info in SOURCES.items():
        print("받는 중:", info["name"])
        req = urllib.request.Request(info["url"], headers={"User-Agent": "data-class-example"})
        with urllib.request.urlopen(req, timeout=120) as res:
            (RAW / filename).write_bytes(res.read())
        log[filename] = {**info, "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (RAW / "sources.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("완료:", RAW)


if __name__ == "__main__":
    main()

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
OUTPUT_JSON = ROOT / "episodes.json"


def to_rfc2822(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def make_title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return stem.replace("_", " ").replace("-", " ")


def scan_mp3_files() -> list[Path]:
    return sorted(
        ROOT.glob("*.mp3"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def build_episode(mp3_path: Path, index_from_newest: int) -> dict:
    stat = mp3_path.stat()
    modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    stem = mp3_path.stem
    title = make_title_from_filename(mp3_path.name)

    return {
        "id": stem,
        "title": title,
        "description": title,
        "audio_file": mp3_path.name,
        "pub_date": to_rfc2822(modified_dt),
        "duration": 0,               # 先占位，后面可升级成自动读取真实时长
        "episode": index_from_newest,
        "season": 1,
        "episode_type": "full"
    }


def main() -> None:
    mp3_files = scan_mp3_files()
    episodes = []

    total = len(mp3_files)
    for i, mp3_path in enumerate(mp3_files, start=1):
        # 最新文件 episode 编号最大，或你也可以改成最新=1
        episode = build_episode(mp3_path, total - i + 1)
        episodes.append(episode)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    print(f"已生成: {OUTPUT_JSON}")
    print(f"共写入 {len(episodes)} 集")


if __name__ == "__main__":
    main()
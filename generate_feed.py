import json
import mimetypes
from pathlib import Path
from typing import Any
from datetime import datetime
from email.utils import format_datetime

from mutagen import File as MutagenFile

# =========================
# 基础配置
# =========================
BASE_URL = "https://genres-terry-choice-technique.trycloudflare.com"
FEED_PATH = "/feed.xml"
FEED_URL = f"{BASE_URL}{FEED_PATH}"

PODCAST_TITLE = "little jing's talk"
PODCAST_LINK = BASE_URL
PODCAST_LANGUAGE = "zh-CN"
PODCAST_DESCRIPTION = "AI podcast"
PODCAST_AUTHOR = "jingjing"
PODCAST_OWNER_NAME = "jingjing"
PODCAST_OWNER_EMAIL = "wenq20220430@gmail.com"

PODCAST_CATEGORY = "Technology"

# ✅ 修复1：不要再用过时的 Podcasting 子类
# 方案A（推荐）：直接不写子分类
PODCAST_SUBCATEGORY = None
# 方案B：换成仍可能被 Apple 支持的 Technology 子类（按需启用）
# PODCAST_SUBCATEGORY = "Tech News"
# PODCAST_SUBCATEGORY = "Software How-To"
# PODCAST_SUBCATEGORY = "Gadgets"

PODCAST_EXPLICIT = "false"
PODCAST_TYPE = "episodic"
COVER_FILE = "cover.jpg"
COVER_URL = f"{BASE_URL}/{COVER_FILE}"

PODCAST_COPYRIGHT = "© 2026 jingjing"
PODCAST_KEYWORDS = "AI,podcast,technology"

ROOT = Path(__file__).parent
EPISODES_JSON = ROOT / "episodes.json"
OUTPUT_XML = ROOT / "feed.xml"

# =========================
# 工具函数 & 音频处理
# =========================
def xml_escape(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

def cdata(text: Any) -> str:
    text = str(text).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{text}]]>"

def ensure_file_exists(path: Path, file_desc: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{file_desc} 不存在: {path}")

def guess_mime_type(file_name: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_name)
    if file_name.lower().endswith(".mp3"):
        return "audio/mpeg"
    return mime_type or "application/octet-stream"

def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_audio_duration(file_path: Path) -> int:
    """
    语音/音频处理：用 mutagen 解析音频头部获取真实时长（秒）
    """
    try:
        audio = MutagenFile(file_path)
        if audio is not None and getattr(audio, "info", None) is not None:
            length = getattr(audio.info, "length", 0)
            return int(length) if length else 0
    except Exception as e:
        print(f"⚠️ 警告: 无法读取音频时长 {file_path}: {e}")
    return 0

def format_pub_date(date_str: str) -> str:
    """
    将 ISO 8601 转为 RFC 2822（pubDate 标准格式）
    """
    try:
        dt = datetime.fromisoformat(date_str)
        return format_datetime(dt)
    except ValueError:
        return date_str

def load_episodes() -> list[dict]:
    ensure_file_exists(EPISODES_JSON, "episodes.json")
    with open(EPISODES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("episodes.json 顶层必须是列表 list")
    return data

# =========================
# 构建单集 item
# =========================
def build_item(ep: dict) -> str:
    audio_file = ep["audio_file"]
    audio_path = ROOT / audio_file
    ensure_file_exists(audio_path, f"音频文件 {audio_file}")

    file_size = audio_path.stat().st_size
    audio_url = f"{BASE_URL}/{audio_file}"
    mime_type = guess_mime_type(audio_file)

    title = ep["title"]
    description = ep["description"]
    guid = ep["id"]
    pub_date = format_pub_date(ep["pub_date"])

    duration_seconds = get_audio_duration(audio_path)
    if duration_seconds == 0 and "duration" in ep:
        duration_seconds = int(ep["duration"])  # fallback
    duration_str = format_duration(duration_seconds)

    episode_num = ep.get("episode")
    season_num = ep.get("season")
    episode_type = ep.get("episode_type", "full")
    explicit = str(ep.get("explicit", PODCAST_EXPLICIT)).lower()
    item_link = ep.get("link", audio_url)

    parts = [
        "    <item>",
        f"      <title>{xml_escape(title)}</title>",
        f"      <link>{xml_escape(item_link)}</link>",
        f"      <author>{xml_escape(PODCAST_OWNER_EMAIL)} ({xml_escape(PODCAST_AUTHOR)})</author>",
        f"      <description>{cdata(description)}</description>",
        f"      <content:encoded>{cdata(description)}</content:encoded>",
        f"      <itunes:summary>{cdata(description)}</itunes:summary>",
        f"      <itunes:author>{xml_escape(PODCAST_AUTHOR)}</itunes:author>",
        f"      <itunes:duration>{xml_escape(duration_str)}</itunes:duration>",
        f"      <itunes:explicit>{xml_escape(explicit)}</itunes:explicit>",
        f"      <guid isPermaLink=\"false\">{xml_escape(guid)}</guid>",
        f"      <pubDate>{pub_date}</pubDate>",
        f"      <enclosure url=\"{xml_escape(audio_url)}\" length=\"{file_size}\" type=\"{xml_escape(mime_type)}\" />",
    ]

    if episode_num is not None:
        parts.append(f"      <itunes:episode>{xml_escape(episode_num)}</itunes:episode>")
    if season_num is not None:
        parts.append(f"      <itunes:season>{xml_escape(season_num)}</itunes:season>")
    if episode_type:
        parts.append(f"      <itunes:episodeType>{xml_escape(episode_type)}</itunes:episodeType>")

    item_image = ep.get("image")
    if item_image:
        parts.append(f"      <itunes:image href=\"{xml_escape(item_image)}\"/>")

    parts.append("    </item>")
    return "\n".join(parts)

# =========================
# 构建整个 feed
# =========================
def build_itunes_category_xml() -> str:
    """
    ✅ 修复1：避免输出过时子分类；若配置了子类则输出嵌套结构
    """
    if PODCAST_SUBCATEGORY:
        return (
            f'    <itunes:category text="{xml_escape(PODCAST_CATEGORY)}">\n'
            f'      <itunes:category text="{xml_escape(PODCAST_SUBCATEGORY)}"/>\n'
            f"    </itunes:category>"
        )
    return f'    <itunes:category text="{xml_escape(PODCAST_CATEGORY)}"/>'

def build_feed(episodes: list[dict]) -> str:
    cover_path = ROOT / COVER_FILE
    ensure_file_exists(cover_path, "封面文件")

    items_xml = "\n".join(build_item(ep) for ep in episodes)
    itunes_category_xml = build_itunes_category_xml()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{xml_escape(PODCAST_TITLE)}</title>
    <link>{xml_escape(PODCAST_LINK)}</link>

    <!-- ✅ 修复2：Atom self link，提升各类播客客户端兼容性 -->
    <atom:link href="{xml_escape(FEED_URL)}" rel="self" type="application/rss+xml" />

    <language>{xml_escape(PODCAST_LANGUAGE)}</language>
    <description>{cdata(PODCAST_DESCRIPTION)}</description>
    <copyright>{xml_escape(PODCAST_COPYRIGHT)}</copyright>
    <generator>Custom Podcast RSS Generator</generator>
    <managingEditor>{xml_escape(PODCAST_OWNER_EMAIL)} ({xml_escape(PODCAST_OWNER_NAME)})</managingEditor>
    <webMaster>{xml_escape(PODCAST_OWNER_EMAIL)} ({xml_escape(PODCAST_OWNER_NAME)})</webMaster>

    <image>
      <url>{xml_escape(COVER_URL)}</url>
      <title>{xml_escape(PODCAST_TITLE)}</title>
      <link>{xml_escape(PODCAST_LINK)}</link>
    </image>

    <itunes:type>{xml_escape(PODCAST_TYPE)}</itunes:type>
    <itunes:author>{xml_escape(PODCAST_AUTHOR)}</itunes:author>
    <itunes:summary>{cdata(PODCAST_DESCRIPTION)}</itunes:summary>
    <itunes:explicit>{xml_escape(PODCAST_EXPLICIT)}</itunes:explicit>
    <itunes:image href="{xml_escape(COVER_URL)}"/>
    <itunes:keywords>{xml_escape(PODCAST_KEYWORDS)}</itunes:keywords>

    <itunes:owner>
      <itunes:name>{xml_escape(PODCAST_OWNER_NAME)}</itunes:name>
      <itunes:email>{xml_escape(PODCAST_OWNER_EMAIL)}</itunes:email>
    </itunes:owner>

{itunes_category_xml}

{items_xml}
  </channel>
</rss>
"""

def main() -> None:
    episodes = load_episodes()
    feed_xml = build_feed(episodes)
    with open(OUTPUT_XML, "w", encoding="utf-8", newline="\n") as f:
        f.write(feed_xml)
    print(f"✅ 已成功生成: {OUTPUT_XML}")
    print(f"📻 RSS 地址: {FEED_URL}")

if __name__ == "__main__":
    main()
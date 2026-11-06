"""Archive the public records used by NEA's latest-policy-file listing."""
from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from lxml import html

PAGE = "https://www.nea.gov.cn/policy/zxwj.htm"
FEED_URL = "https://raw.githubusercontent.com/zhengboyuan/nea-policy-rss/main/public/feed.xml"
ROOT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")


def fetch(url: str) -> bytes:
    return subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error",
         "--retry", "2", "--retry-delay", "2", "--max-time", "40", url],
        check=True, capture_output=True,
    ).stdout


def plain(value: str) -> str:
    if not value.strip():
        return ""
    root = html.fragment_fromstring(value, create_parent="div")
    for node in root.xpath(".//script|.//style"):
        node.drop_tree()
    return " ".join(root.text_content().split())


def discover_source(raw: bytes) -> tuple[str, int]:
    text = raw.decode("utf-8")
    tree = html.fromstring(text)
    nodes = tree.xpath('//*[@id="showData0"]')
    if len(nodes) != 1:
        raise ValueError("Latest-files list is missing or ambiguous")
    node = nodes[0]
    source = re.fullmatch(r"datasource:([a-f0-9]{32})", node.get("data", ""))
    if not source or node.get("preview") != "ds_":
        raise ValueError("Unknown data-source format")
    size = re.search(r"pageSize:\s*(\d+)", text)
    if not size or int(size[1]) <= 0:
        raise ValueError("Page size missing")
    return urljoin(PAGE, f"ds_{source[1]}.json"), int(size[1])


def parse_records(payload: dict) -> tuple[list[dict], int]:
    rows = payload.get("datasource")
    if not isinstance(rows, list) or not rows:
        raise ValueError("No source records; keep the previous archive")
    unique = {}
    for row in rows:
        title = plain(row.get("showTitle") or row.get("title") or "")
        link = urljoin(PAGE, row.get("publishUrl") or "")
        if not row.get("publishUrl") or not title or urlparse(link).scheme not in {"http", "https"}:
            raise ValueError(f"Invalid source record: {row.get('contentId')}")
        published = datetime.strptime(row["publishTime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
        item = {"title": title, "url": link, "published_at": published.isoformat(),
                "summary": plain(row.get("summary") or "")}
        old = unique.get(link)
        if not old or old["published_at"] < item["published_at"]:
            unique[link] = item
    return list(unique.values()), len(rows)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def main() -> None:
    archive_path = ROOT / "data/notices.json"
    previous = json.loads(archive_path.read_text()) if archive_path.exists() else []
    records = {item["url"]: item for item in previous}
    source, page_size = discover_source(fetch(PAGE))
    current, source_count = parse_records(json.loads(fetch(source)))
    print(f"Source: {source_count} records, {len(current)} unique links", flush=True)
    records.update({item["url"]: item for item in current})
    items = sorted(records.values(), key=lambda x: (x["published_at"], x["url"]), reverse=True)
    now = datetime.now(CST)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for tag, value in {
        "title": "国家能源局｜最新文件（历史归档与更新）",
        "link": PAGE,
        "description": "非官方 RSS：收录国家能源局最新文件栏目当前公开列表并持续保留历史记录。内容版权归原发布单位。",
        "language": "zh-cn", "ttl": "360", "lastBuildDate": format_datetime(now),
    }.items():
        ET.SubElement(channel, tag).text = value
    ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link", {
        "href": FEED_URL, "rel": "self", "type": "application/rss+xml",
    })
    for item in items:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "link").text = item["url"]
        ET.SubElement(node, "guid", isPermaLink="true").text = item["url"]
        date = datetime.fromisoformat(item["published_at"])
        ET.SubElement(node, "pubDate").text = format_datetime(date)
        ET.SubElement(node, "description").text = (
            f"{item['summary'] or item['title']}\n发布日期：{date:%Y-%m-%d}\n"
            "来源：国家能源局最新文件栏目。点击原文查看正文或附件。"
        )
    ET.indent(rss)
    xml = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    assert len(ET.fromstring(xml).findall("./channel/item")) == len(items)
    status = {
        "updated_at": now.isoformat(), "source_page": PAGE, "source_data_url": source,
        "source_record_count": source_count, "source_pages": (source_count + page_size - 1) // page_size,
        "currently_listed_unique_count": len(current), "archive_count": len(items),
        "oldest_date": items[-1]["published_at"][:10], "newest_date": items[0]["published_at"][:10],
        "coverage": "官网当前公开列表及此后积累的记录，不代表已找回官网未列出的全部更早历史文件。",
    }
    for path, obj in [(archive_path, items), (ROOT / "public/status.json", status)]:
        atomic_write(path, (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode())
    atomic_write(ROOT / "public/feed.xml", xml)
    print(f"Published {len(items)} archived files", flush=True)


if __name__ == "__main__":
    main()

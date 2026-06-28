#!/usr/bin/env python3
"""
下载所有规则源到本地 sources/ 目录
用于离线合并，避免上游源波动
"""
import yaml
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import time

SOURCES_FILE = os.environ.get("SOURCES_FILE", "sources.yaml")
OUTPUT_DIR = os.environ.get("SOURCES_DIR", "sources")
USER_AGENT = "AdGuardRulesMerger/3.0"
TIMEOUT = 120


def fetch_url(url, retries=3):
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError, Exception) as e:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            print("  ⚠️ Failed: %s -> %s" % (url, e), file=sys.stderr)
            return None


def sanitize_filename(name):
    """将规则源名称转为安全文件名"""
    return name.replace("/", "-").replace(" ", "_") + ".txt"


def main():
    print("📥 Downloading all rule sources to local cache...")
    print("=" * 50)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_sources = []

    # 收集所有源
    for src in config.get("blocklist", []):
        all_sources.append(src)
    for src in config.get("blocklist_extra", []):
        all_sources.append(src)
    for src in config.get("whitelist", {}).get("sources", []):
        all_sources.append(src)

    success = 0
    failed = 0

    for src in all_sources:
        name = src["name"]
        url = src["url"]
        filename = sanitize_filename(name)
        filepath = os.path.join(OUTPUT_DIR, filename)

        print("  ⬇️ %s: %s" % (name, url))
        content = fetch_url(url)
        if content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            size = len(content)
            print("      → ✅ %s (%d bytes)" % (filename, size))
            success += 1
        else:
            print("      → ❌ failed")
            failed += 1

    print("\n" + "=" * 50)
    print("✅ Downloaded: %d, ❌ Failed: %d" % (success, failed))
    print("📁 Sources saved to: %s/" % OUTPUT_DIR)


if __name__ == "__main__":
    main()

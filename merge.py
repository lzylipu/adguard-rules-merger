#!/usr/bin/env python3
"""
🛡️ AdGuard Home Rules Merger v4 (本地化模式)
- 本地优先: 优先从 sources/ 目录读取已下载的规则源
- 离线合并: 避免上游源波动导致规则数不稳定
- DNS-only: 只保留 AG Home DNS 层能生效的规则
- AG兼容: 支持 $third-party、$important、$badfilter 等DNS修饰符
- Domain-dedup: 跨源去重
- 双版本: blocklist.txt(标准版，去白名单) + blocklist-full.txt(完整版，不去白名单)
"""
import yaml
import re
import json
import sys
import os
from datetime import datetime, timezone, timedelta

SOURCES_FILE = os.environ.get("SOURCES_FILE", "sources.yaml")
SOURCES_DIR = os.environ.get("SOURCES_DIR", "sources")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", ".")
USE_LOCAL = os.environ.get("USE_LOCAL", "1") == "1"
CST = timezone(timedelta(hours=8))

# AG Home DNS 层不支持的浏览器级修饰符（这些要过滤）
BROWSER_ONLY_MODS = {
    "csp", "cookie", "replace", "redirect", "redirect-rule",
    "popup", "image", "stylesheet", "script", "subdocument",
    "xmlhttprequest", "websocket", "font", "media", "object",
    "ping", "beacon", "other", "inline-font", "inline-script",
    "elemhide", "generichide", "jsinject", "extension",
}

# AG Home DNS 层支持的修饰符（这些保留）
DNS_SUPPORTED_MODS = {
    "third-party", "important", "badfilter", "domain",
    "denyallow", "method", "header", "removeparam",
}

# 核心服务域名保护列表 - 这些域名即使出现在规则源中也不拦截
CORE_DOMAINS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "google.com", "www.google.com", "googleapis.com",
    "baidu.com", "www.baidu.com",
    "bilibili.com", "www.bilibili.com",
    "qq.com", "www.qq.com",
    "taobao.com", "www.taobao.com",
    "jd.com", "www.jd.com",
    "alipay.com", "www.alipay.com",
    "weibo.com", "www.weibo.com",
    "douyin.com", "www.douyin.com",
    "github.com", "www.github.com", "raw.githubusercontent.com",
}

def sanitize_filename(name):
    return name.replace("/", "-").replace(" ", "_") + ".txt"

def load_local_source(name):
    filename = sanitize_filename(name)
    filepath = os.path.join(SOURCES_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return None

def fetch_url(url):
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    try:
        req = Request(url, headers={"User-Agent": "AdGuard-Rules-Merger/4.0"})
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError) as e:
        print(f"      → ❌ fetch failed: {e}")
        return None

def get_source_content(src):
    name, url = src["name"], src["url"]
    if USE_LOCAL:
        content = load_local_source(name)
        if content:
            print(f"  📁 {name}: loaded from local cache ({len(content)} bytes)")
            return content
        print(f"  📁 {name}: local cache miss, fetching...")
    content = fetch_url(url)
    if content:
        print(f"  📁 {name}: fetched ({len(content)} bytes)")
    return content

def is_dns_compatible(rule):
    """判断规则在 AG Home DNS 层是否有效。"""
    if not rule or rule.startswith("!") or rule.startswith("#") or rule.startswith("["):
        return False
    if rule.startswith("!#"):
        return False
    if "##" in rule and not rule.startswith("@@"):
        return False
    if "#@#" in rule or "#?#" in rule or "$$" in rule:
        return False
    if rule.startswith("$"):
        return False
    
    # 核心域名保护 - 跳过 youtube.com 等核心服务（仅精确匹配主域）
    domain = extract_domain(rule)
    if domain and domain.lower() in CORE_DOMAINS:
        return False
    
    # 检查修饰符
    if "$" in rule:
        idx = rule.index("$")
        mods_str = rule[idx + 1:]
        if not mods_str or mods_str.strip() == "":
            return False
        for part in mods_str.split(","):
            mod = part.split("=")[0].split("~")[-1].strip().lower()
            if mod in BROWSER_ONLY_MODS:
                return False
    return True

def extract_domain(rule):
    """从规则提取主域名（去重key）。支持带$修饰符的规则。"""
    m = re.match(r'(?:@@)?\|\|([a-z0-9.*_-]+)\^', rule, re.IGNORECASE)
    if m:
        d = m.group(1).lower()
        if d.startswith("*."):
            d = d[2:]
        if d.endswith(".*"):
            d = d[:-2]
        return d
    return None

def merge_sources(domain_map, new_map):
    added = 0
    for k, rule in new_map.items():
        if k not in domain_map:
            domain_map[k] = rule
            added += 1
        else:
            old = domain_map[k]
            if rule.startswith("@@") and not old.startswith("@@"):
                domain_map[k] = rule
            elif "$" not in rule and "$" in old and not rule.startswith("@@"):
                domain_map[k] = rule
    return added

def apply_whitelist(domain_map, wl_domains):
    removed = 0
    result = {}
    for k, rule in domain_map.items():
        domain = extract_domain(rule)
        if domain and any(domain == w or domain.endswith("." + w) for w in wl_domains):
            removed += 1
            continue
        result[k] = rule
    return result, removed

def write_blocklist(filepath, rules, header_extra, timestamp, sources_count, custom_count):
    header = """! 🛡️ AdGuard Home Merged DNS Blocklist
! Auto-merged by adguard-rules-merger v4 (local mode)
! Updated: %s
! Sources: %s blocklist + whitelist(%s custom)
! Rules: %s (DNS-only, domain-deduped)
%s! License: https://github.com/lzylipu/adguard-rules-merger
! ============================================================
""" % (timestamp, sources_count, custom_count, "{:,}".format(len(rules)), header_extra)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        for rule in sorted(rules.values()):
            f.write(rule + "\n")

def main():
    print("🛡️ AdGuard Home Rules Merger v4 (本地化模式, AG兼容)")
    print("=" * 50)
    print("USE_LOCAL=%s, SOURCES_DIR=%s" % (USE_LOCAL, SOURCES_DIR))
    print("=" * 50)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. 标准版
    print("\n📥 [标准版] Loading blocklist sources...")
    bl_sources = config.get("blocklist", [])
    std_map = {}
    std_stats = {}

    for src in bl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        content = get_source_content(src)
        if not content:
            std_stats[name] = {"raw": 0, "dns_ok": 0, "new": 0, "desc": desc, "error": True}
            continue
        raw = dns_ok = 0
        domain_map = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
                continue
            raw += 1
            if not is_dns_compatible(line):
                continue
            dns_ok += 1
            domain = extract_domain(line)
            if domain and domain not in domain_map:
                domain_map[domain] = line
        std_stats[name] = {"raw": raw, "dns_ok": dns_ok, "new": len(domain_map), "desc": desc}
        added = merge_sources(std_map, domain_map)
        print("      → raw:%s  dns_ok:%s  增量:%s" % (
            "{:,}".format(raw), "{:,}".format(dns_ok), "{:,}".format(added)))

    print("\n  📊 标准版: %s unique DNS rules" % "{:,}".format(len(std_map)))

    # 2. 完整版
    bl_extra = config.get("blocklist_extra", [])
    full_map = dict(std_map)
    full_stats = {}

    if bl_extra:
        print("\n📥 [完整版] Loading extra sources...")
        for src in bl_extra:
            name, url, desc = src["name"], src["url"], src.get("desc", "")
            content = get_source_content(src)
            if not content:
                full_stats[name] = {"raw": 0, "dns_ok": 0, "new": 0, "desc": desc, "error": True}
                continue
            raw = dns_ok = 0
            domain_map = {}
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
                    continue
                raw += 1
                if not is_dns_compatible(line):
                    continue
                dns_ok += 1
                domain = extract_domain(line)
                if domain and domain not in domain_map:
                    domain_map[domain] = line
            full_stats[name] = {"raw": raw, "dns_ok": dns_ok, "new": len(domain_map), "desc": desc}
            added = merge_sources(full_map, domain_map)
            print("      → raw:%s  dns_ok:%s  增量:%s" % (
                "{:,}".format(raw), "{:,}".format(dns_ok), "{:,}".format(added)))
        print("\n  📊 完整版(去重后): %s unique DNS rules" % "{:,}".format(len(full_map)))

    # 3. 白名单
    print("\n🛡️ Loading whitelist...")
    wl_config = config.get("whitelist", {})
    wl_sources = wl_config.get("sources", [])
    wl_custom = wl_config.get("custom", [])
    wl_domains = set()
    wl_rules = []

    for src in wl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        print("  📁 %s: %s" % (name, desc))
        content = get_source_content(src)
        if not content:
            print("      → ❌ failed")
            continue
        count = 0
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
                continue
            if not is_dns_compatible(line):
                continue
            domain = extract_domain(line)
            if domain:
                wl_domains.add(domain)
                wl_rules.append(line)
                count += 1
        print("      → %s DNS白名单" % "{:,}".format(count))

    custom_count = 0
    for rule in wl_custom:
        domain = extract_domain(rule)
        if domain:
            wl_domains.add(domain)
            wl_rules.append(rule)
            custom_count += 1
    print("  ✏️ Custom: %s rules, 总白名单域名: %s" % (custom_count, "{:,}".format(len(wl_domains))))

    # 4. 应用白名单
    print("\n✂️ Applying whitelist (标准版应用，完整版跳过)...")
    std_final, std_wl_rm = apply_whitelist(std_map, wl_domains)
    full_final = dict(full_map)
    print("  标准版: 去掉 %s 条 → %s 条" % ("{:,}".format(std_wl_rm), "{:,}".format(len(std_final))))
    print("  完整版: 保留全量 %s 条 (不去白名单)" % "{:,}".format(len(full_final)))

    final_wl = list(dict.fromkeys(wl_rules))

    # 5. 写文件
    print("\n💾 Writing output files...")
    now = datetime.now(CST)
    ts = now.strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    total_src = len(bl_sources) + len(bl_extra)

    write_blocklist(os.path.join(OUTPUT_DIR, "blocklist.txt"), std_final,
                    "! Edition: Standard (recommended, whitelisted)\n", ts, len(bl_sources), custom_count)

    if bl_extra:
        write_blocklist(os.path.join(OUTPUT_DIR, "blocklist-full.txt"), full_final,
                        "! Edition: Full (comprehensive, NO whitelist filtering)\n", ts, total_src, custom_count)

    wl_header = """! ✅ AdGuard Home Merged DNS Whitelist
! Auto-merged by adguard-rules-merger v4 (local mode)
! Updated: %s
! Sources: %s upstream + %s custom
! Rules: %s (DNS-only, deduped)
! ============================================================
""" % (ts, len(wl_sources), custom_count, "{:,}".format(len(final_wl)))
    with open(os.path.join(OUTPUT_DIR, "whitelist.txt"), "w", encoding="utf-8") as f:
        f.write(wl_header)
        for rule in sorted(final_wl):
            f.write(rule + "\n")

    stats = {
        "updated": ts, "version": "4.0", "mode": "local" if USE_LOCAL else "online",
        "standard": {"total": len(std_final), "sources": std_stats, "whitelist_removed": std_wl_rm},
        "whitelist": {"total": len(final_wl), "unique_domains": len(wl_domains), "upstream_sources": len(wl_sources), "custom_rules": custom_count},
    }
    if bl_extra:
        stats["full"] = {"total": len(full_final), "sources": full_stats, "whitelist_removed": 0, "whitelist_note": "Full edition does NOT apply whitelist"}

    with open(os.path.join(OUTPUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print("\n✅ Done!")
    print("  📄 blocklist.txt       → %s rules (标准版)" % "{:,}".format(len(std_final)))
    if bl_extra:
        print("  📄 blocklist-full.txt  → %s rules (完整版, 全量不去白名单)" % "{:,}".format(len(full_final)))
    print("  ✅ whitelist.txt        → %s rules" % "{:,}".format(len(final_wl)))

if __name__ == "__main__":
    main()

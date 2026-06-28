#!/usr/bin/env python3
"""
🛡️ AdGuard Home Rules Merger v4 (本地化模式)
- 本地优先: 优先从 sources/ 目录读取已下载的规则源
- 离线合并: 避免上游源波动导致规则数不稳定
- DNS-only: 只保留 AG Home DNS 层能生效的规则
- AG兼容: 支持 $third-party、$important、$badfilter 等DNS修饰符
- Browser→DNS 转换: 从浏览器级元素隐藏规则(##)提取域名
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
    "csp", "cookie", "replace", "redirect", "popup",
    "generichide", "stealth", "subdocument", "object",
    "object-subrequest", "xbl", "dtd", "ping",
    "xmlhttprequest", "websocket", "webrtc", "media",
    "font", "image", "stylesheet", "script", "other",
    "all", "elemhide", "content", "specifichide",
    "inline-script", "popunder", "redirect-rule",
}

# AG Home DNS 层支持的修饰符（这些保留）
DNS_SUPPORTED_MODS = {
    "third-party", "important", "badfilter", "domain",
    "denyallow", "method", "header", "removeparam",
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
    import time
    USER_AGENT = "AdGuardRulesMerger/4.0"
    TIMEOUT = 90
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError, Exception) as e:
            if attempt < 2:
                time.sleep(5)
                continue
            print("  ⚠️ Failed: %s -> %s" % (url, e), file=sys.stderr)
            return None

def get_source_content(src):
    name = src["name"]
    url = src["url"]
    if USE_LOCAL:
        content = load_local_source(name)
        if content:
            print("  📁 %s: loaded from local cache (%d bytes)" % (name, len(content)))
            return content
        print("  ⚠️ %s: local cache not found, trying online..." % name)
    content = fetch_url(url)
    if content:
        print("  ⬇️ %s: downloaded (%d bytes)" % (name, len(content)))
        if USE_LOCAL:
            os.makedirs(SOURCES_DIR, exist_ok=True)
            filepath = os.path.join(SOURCES_DIR, sanitize_filename(name))
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
    return content

def is_dns_compatible(rule):
    """判断规则在 AG Home DNS 层是否有效。"""
    if not rule or rule.startswith("!") or rule.startswith("#") or rule.startswith("["):
        return False
    if rule.startswith("!#"):
        return False
    # CSS/HTML 选择器（这些走 convert_elemhide_domains 另行处理）
    if "##" in rule and not rule.startswith("@@"):
        return False
    if "#@#" in rule or "#?#" in rule or "$$" in rule:
        return False
    # 纯修饰符行
    if rule.startswith("$"):
        return False
    
    # 检查修饰符
    if "$" in rule:
        idx = rule.index("$")
        mods_str = rule[idx + 1:]
        for part in mods_str.split(","):
            mod = part.split("=")[0].split("~")[-1].strip().lower()
            # 如果是浏览器专用修饰符，过滤掉
            if mod in BROWSER_ONLY_MODS:
                return False
            # 未知修饰符也过滤（保守策略）
            # 但允许空修饰符和已知DNS修饰符
    return True

def extract_domain(rule):
    """从规则提取主域名（去重key）。支持带$修饰符的规则。"""
    # 匹配 ||domain^ 或 ||domain^$xxx
    m = re.match(r'(?:@@)?\|\|([a-z0-9.*_-]+)\^', rule, re.IGNORECASE)
    if m:
        d = m.group(1).lower()
        if d.startswith("*."):
            d = d[2:]
        if d.endswith(".*"):
            d = d[:-2]
        return d
    return None

def convert_elemhide_domains(content, name):
    """从浏览器级元素隐藏规则(##)提取域名限定符，转为 ||domain^ DNS规则。"""
    converted = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("[") or line.startswith("@@"):
            continue
        if "##" not in line:
            continue
        sep_idx = line.index("##")
        if sep_idx == 0:
            continue
        domain_part = line[:sep_idx]
        for d in domain_part.split(","):
            d = d.strip()
            if d.startswith("~"):
                continue
            if d.startswith("/") and d.endswith("/"):
                continue
            d = d.lstrip("*.").rstrip(".*")
            if "." in d and len(d) > 3 and not d.startswith("-"):
                d_lower = d.lower()
                if d_lower not in converted:
                    converted[d_lower] = "||%s^" % d_lower
    return converted

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

def write_blocklist(filepath, rules, header_extra, timestamp, sources_count, custom_count, converted_total):
    header = """! 🛡️ AdGuard Home Merged DNS Blocklist
! Auto-merged by adguard-rules-merger v4 (local mode)
! Updated: %s
! Sources: %s blocklist + whitelist(%s custom)
! Rules: %s (DNS-only, domain-deduped)
! Browser→DNS converted: %s domains from elemhide rules
%s! License: https://github.com/lzylipu/adguard-rules-merger
! ============================================================
""" % (timestamp, sources_count, custom_count, "{:,}".format(len(rules)), "{:,}".format(converted_total), header_extra)
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
    std_converted = 0

    for src in bl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        content = get_source_content(src)
        if not content:
            std_stats[name] = {"raw": 0, "dns_ok": 0, "new": 0, "converted": 0, "desc": desc, "error": True}
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
        converted_map = convert_elemhide_domains(content, name)
        converted_count = 0
        for domain, rule in converted_map.items():
            if domain not in domain_map:
                domain_map[domain] = rule
                converted_count += 1
        std_stats[name] = {"raw": raw, "dns_ok": dns_ok, "new": len(domain_map), "converted": converted_count, "desc": desc}
        added = merge_sources(std_map, domain_map)
        std_converted += converted_count
        print("      → raw:%s  dns_ok:%s  增量:%s  (转换:%s)" % (
            "{:,}".format(raw), "{:,}".format(dns_ok), "{:,}".format(added), "{:,}".format(converted_count)))

    print("\n  📊 标准版: %s unique DNS rules" % "{:,}".format(len(std_map)))

    # 2. 完整版
    bl_extra = config.get("blocklist_extra", [])
    full_map = dict(std_map)
    full_stats = {}
    full_converted = std_converted

    if bl_extra:
        print("\n📥 [完整版] Loading extra sources...")
        for src in bl_extra:
            name, url, desc = src["name"], src["url"], src.get("desc", "")
            content = get_source_content(src)
            if not content:
                full_stats[name] = {"raw": 0, "dns_ok": 0, "new": 0, "converted": 0, "desc": desc, "error": True}
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
            converted_map = convert_elemhide_domains(content, name)
            converted_count = 0
            for domain, rule in converted_map.items():
                if domain not in domain_map:
                    domain_map[domain] = rule
                    converted_count += 1
            full_stats[name] = {"raw": raw, "dns_ok": dns_ok, "new": len(domain_map), "converted": converted_count, "desc": desc}
            added = merge_sources(full_map, domain_map)
            full_converted += converted_count
            print("      → raw:%s  dns_ok:%s  增量:%s  (转换:%s)" % (
                "{:,}".format(raw), "{:,}".format(dns_ok), "{:,}".format(added), "{:,}".format(converted_count)))
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
                    "! Edition: Standard (recommended, whitelisted)\n", ts, len(bl_sources), custom_count, std_converted)

    if bl_extra:
        write_blocklist(os.path.join(OUTPUT_DIR, "blocklist-full.txt"), full_final,
                        "! Edition: Full (comprehensive, NO whitelist filtering)\n", ts, total_src, custom_count, full_converted)

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
        "standard": {"total": len(std_final), "sources": std_stats, "whitelist_removed": std_wl_rm, "browser_converted": std_converted},
        "whitelist": {"total": len(final_wl), "unique_domains": len(wl_domains), "upstream_sources": len(wl_sources), "custom_rules": custom_count},
    }
    if bl_extra:
        stats["full"] = {"total": len(full_final), "sources": full_stats, "whitelist_removed": 0, "whitelist_note": "Full edition does NOT apply whitelist", "browser_converted": full_converted}

    with open(os.path.join(OUTPUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print("\n✅ Done!")
    print("  📄 blocklist.txt       → %s rules (标准版)" % "{:,}".format(len(std_final)))
    if bl_extra:
        print("  📄 blocklist-full.txt  → %s rules (完整版, 全量不去白名单)" % "{:,}".format(len(full_final)))
    print("  ✅ whitelist.txt        → %s rules" % "{:,}".format(len(final_wl)))

if __name__ == "__main__":
    main()

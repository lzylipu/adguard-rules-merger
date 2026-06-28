#!/usr/bin/env python3
"""
🛡️ AdGuard Home Rules Merger v2
- DNS-only: 只保留 AG Home DNS 层能生效的规则
- Domain-dedup: 基于域名去重，真正消除多源重叠
- 双版本输出: blocklist.txt(标准~16万) + blocklist-full.txt(完整~35万)
- 实用白名单: 只保留 DNS 级有效的反误杀
"""

import yaml
import re
import json
import time
import sys
import os
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

SOURCES_FILE = os.environ.get("SOURCES_FILE", "sources.yaml")
USER_AGENT = "AdGuardRulesMerger/2.0"
TIMEOUT = 90
CST = timezone(timedelta(hours=8))

# AG Home DNS 层不支持的浏览器级修饰符
BROWSER_MODS = {
    "csp", "cookie", "replace", "redirect", "popup",
    "generichide", "stealth", "subdocument", "object",
    "object-subrequest", "xbl", "dtd", "ping",
    "xmlhttprequest", "websocket", "webrtc", "media",
    "font", "image", "stylesheet", "script", "other",
    "all", "elemhide", "content", "specifichide",
    "inline-script", "popunder", "redirect-rule",
}


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
            print(f"  ⚠️ Failed: {url} -> {e}", file=sys.stderr)
            return None


def is_dns_compatible(rule):
    """判断规则在 AG Home DNS 层是否有效。"""
    if not rule or rule.startswith("!") or rule.startswith("#") or rule.startswith("["):
        return False
    if rule.startswith("!#"):
        return False
    # CSS/HTML 选择器
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
            if mod in BROWSER_MODS:
                return False
    return True


def extract_domain(rule):
    """从规则提取主域名（去重key）。"""
    m = re.match(r'(?:@@)?\|\|([a-z0-9.*_-]+)\^', rule, re.IGNORECASE)
    if m:
        d = m.group(1).lower()
        if d.startswith("*."):
            d = d[2:]
        if d.endswith(".*"):
            d = d[:-2]
        return d
    return None


def domain_is_whitelisted(domain, wl_domains):
    parts = domain.split(".")
    for i in range(len(parts)):
        if ".".join(parts[i:]) in wl_domains:
            return True
    return False


def download_and_parse(url, name, desc):
    """下载源并提取 DNS 级有效域名的规则映射。"""
    print(f"  ⬇️ {name}: {desc}")
    content = fetch_url(url)
    if not content:
        return {}, {"raw": 0, "dns_ok": 0, "new": 0, "desc": desc, "error": True}

    raw = 0
    dns_ok = 0
    domain_map = {}  # domain -> rule

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
            continue
        raw += 1
        if not is_dns_compatible(line):
            continue
        dns_ok += 1

        domain = extract_domain(line)
        if domain:
            if domain not in domain_map:
                domain_map[domain] = line
            else:
                # 同域名优选: @@白名单 > 简单规则 > 复杂规则
                old = domain_map[domain]
                if line.startswith("@@") and not old.startswith("@@"):
                    domain_map[domain] = line
                elif "$" not in line and "$" in old and not line.startswith("@@"):
                    domain_map[domain] = line
        else:
            # 非标准格式但DNS有效 → 用规则文本做key
            key = line.lower().strip()
            if key not in domain_map:
                domain_map[key] = line

    return domain_map, {"raw": raw, "dns_ok": dns_ok, "new": len(domain_map), "desc": desc}


def merge_sources(domain_map, new_map):
    """合并新源到现有 domain_map，只加入新域名。"""
    added = 0
    for k, rule in new_map.items():
        if k not in domain_map:
            domain_map[k] = rule
            added += 1
        else:
            # 同域名优选
            old = domain_map[k]
            if rule.startswith("@@") and not old.startswith("@@"):
                domain_map[k] = rule
            elif "$" not in rule and "$" in old and not rule.startswith("@@"):
                domain_map[k] = rule
    return added


def apply_whitelist(domain_map, wl_domains):
    """去掉白名单域名对应的拦截规则。"""
    removed = 0
    result = {}
    for k, rule in domain_map.items():
        domain = extract_domain(rule)
        if domain and domain_is_whitelisted(domain, wl_domains):
            removed += 1
            continue
        result[k] = rule
    return result, removed


def write_blocklist(filepath, rules, header_extra, timestamp, sources_count, custom_count):
    header = f"""! 🛡️ AdGuard Home Merged DNS Blocklist
! Auto-merged by adguard-rules-merger v2
! Updated: {timestamp}
! Sources: {sources_count} blocklist + whitelist({custom_count} custom)
! Rules: {len(rules):,} (DNS-only, domain-deduped, whitelisted)
{header_extra}! License: https://github.com/lzylipu/adguard-rules-merger
! ============================================================
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        for rule in sorted(rules.values()):
            f.write(rule + "\n")


def main():
    print("🛡️ AdGuard Home Rules Merger v2")
    print("=" * 50)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # ── 1. 标准版 blocklist ──
    print("\n📥 [标准版] Downloading blocklist sources...")
    bl_sources = config.get("blocklist", [])
    std_map = {}
    std_stats = {}

    for src in bl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        new_map, stat = download_and_parse(url, name, desc)
        std_stats[name] = stat
        added = merge_sources(std_map, new_map)
        print(f"      → raw:{stat['raw']:,}  dns_ok:{stat['dns_ok']:,}  增量域名:{added:,}")

    print(f"\n  📊 标准版: {len(std_map):,} unique DNS rules")

    # ── 2. 完整版 (标准 + 额外源) ──
    bl_extra = config.get("blocklist_extra", [])
    full_map = dict(std_map)  # 复制标准版
    full_stats = {}

    if bl_extra:
        print(f"\n📥 [完整版] Downloading extra sources...")
        for src in bl_extra:
            name, url, desc = src["name"], src["url"], src.get("desc", "")
            new_map, stat = download_and_parse(url, name, desc)
            full_stats[name] = stat
            added = merge_sources(full_map, new_map)
            print(f"      → raw:{stat['raw']:,}  dns_ok:{stat['dns_ok']:,}  增量域名:{added:,}")
        print(f"\n  📊 完整版: {len(full_map):,} unique DNS rules")

    # ── 3. 白名单 ──
    print("\n🛡️ Downloading whitelist...")
    wl_config = config.get("whitelist", {})
    wl_sources = wl_config.get("sources", [])
    wl_custom = wl_config.get("custom", [])

    wl_domains = set()
    wl_rules = []

    for src in wl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        print(f"  ⬇️ {name}: {desc}")
        content = fetch_url(url)
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
        print(f"      → {count:,} DNS级白名单")

    custom_count = 0
    for rule in wl_custom:
        domain = extract_domain(rule)
        if domain:
            wl_domains.add(domain)
            wl_rules.append(rule)
            custom_count += 1
    print(f"  ✏️ Custom: {custom_count} rules")
    print(f"  📊 Whitelist: {len(wl_domains):,} unique domains")

    # ── 4. 应用白名单 ──
    print("\n✂️ Applying whitelist...")
    std_final, std_wl_rm = apply_whitelist(std_map, wl_domains)
    full_final, full_wl_rm = apply_whitelist(full_map, wl_domains)
    print(f"  标准版: 去掉 {std_wl_rm:,} 条 → {len(std_final):,} 条")
    print(f"  完整版: 去掉 {full_wl_rm:,} 条 → {len(full_final):,} 条")

    # ── 5. 去重白名单 ──
    final_wl = list(dict.fromkeys(wl_rules))

    # ── 6. 写出文件 ──
    print("\n💾 Writing output files...")
    now = datetime.now(CST)
    ts = now.strftime("%Y-%m-%d %H:%M:%S (UTC+8)")

    total_src = len(bl_sources) + len(bl_extra)

    write_blocklist("blocklist.txt", std_final,
                    "! Edition: Standard (recommended)\n", ts, len(bl_sources), custom_count)

    if bl_extra:
        write_blocklist("blocklist-full.txt", full_final,
                        "! Edition: Full (comprehensive)\n", ts, total_src, custom_count)

    # whitelist.txt
    wl_header = f"""! ✅ AdGuard Home Merged DNS Whitelist
! Auto-merged by adguard-rules-merger v2
! Updated: {ts}
! Sources: {len(wl_sources)} upstream + {custom_count} custom
! Rules: {len(final_wl):,} (DNS-only, deduped)
! ============================================================
"""
    with open("whitelist.txt", "w", encoding="utf-8") as f:
        f.write(wl_header)
        for rule in sorted(final_wl):
            f.write(rule + "\n")

    # stats.json
    stats = {
        "updated": ts,
        "version": "2.0",
        "standard": {
            "total": len(std_final),
            "sources": std_stats,
            "whitelist_removed": std_wl_rm,
        },
        "whitelist": {
            "total": len(final_wl),
            "unique_domains": len(wl_domains),
            "upstream_sources": len(wl_sources),
            "custom_rules": custom_count,
        },
    }
    if bl_extra:
        stats["full"] = {
            "total": len(full_final),
            "sources": full_stats,
            "whitelist_removed": full_wl_rm,
        }

    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done!")
    print(f"  📄 blocklist.txt       → {len(std_final):,} rules (标准版)")
    if bl_extra:
        print(f"  📄 blocklist-full.txt  → {len(full_final):,} rules (完整版)")
    print(f"  ✅ whitelist.txt        → {len(final_wl):,} rules")
    print(f"  📊 stats.json           → generated")


if __name__ == "__main__":
    main()

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

# hosts 文件格式行：0.0.0.0 domain / 127.0.0.1 domain / :: domain / ::ffff:127.0.0.1 domain
_HOSTS_RE = re.compile(r'^\s*(?:0\.0\.0\.0|127\.0\.0\.1|::|::ffff:127\.0\.0\.1)\s+([a-z0-9._*-]+)\s*$', re.IGNORECASE)

def normalize_rule(line):
    """将 hosts/裸域名/浏览器白名单(@@|)格式规则转为 AG Home 兼容的 ||/@@|| 格式。
    返回 None 表示该行无法转换为 DNS 规则（丢弃）。"""
    if line.startswith("||") or line.startswith("@@||"):
        return line
    # 浏览器白名单 @@|domain^ -> @@||domain^ （hl2guide 等源）
    m_abp = re.match(r'^@@\|\*?\.?([a-z0-9.*_-]+)\^', line)
    if m_abp:
        d = m_abp.group(1).lower().rstrip('^').rstrip('.')
        if not d or d.startswith('*') or '*' in d:  # 含通配的跳过,避免过度释放
            return None
        return "@@||" + d + "^"
    m = _HOSTS_RE.match(line)
    if m:
        d = m.group(1).strip().lower()
        if d.endswith("."):  # 去掉尾部点
            d = d[:-1]
        if not d:
            return None
        # 跳过纯 IP 行
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', d) or ":" in d:
            return None
        return "||" + d + "^"
    # 裸域名格式（217heidai 等，每行一个域名，无前缀无修饰）
    if re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$', line, re.IGNORECASE):
        d = line.lower()
        if d.endswith("."):
            d = d[:-1]
        return "||" + d + "^"
    return None

def merge_sources(domain_map, new_map):
    added = 0
    for k, rule in new_map.items():
        # 带 $denyallow 的通配符规则（如 ||*.top^$denyallow=...）不能按域名去重
        # 不同来源的白名单列表必须全部保留，否则会丢失白名单保护
        if "$denyallow" in rule:
            # 使用完整规则作为 key，避免覆盖其他来源的白名单
            unique_key = rule  # 完整规则作为唯一标识
            if unique_key not in domain_map:
                domain_map[unique_key] = rule
                added += 1
            continue
        
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


# 作用域白名单：@@||domain^$domain=a,b 只在 a/b 域下生效，不能当全局放行
_SCOPED_WL_RE = re.compile(r'^@@\|\|([a-z0-9.*_-]+)\^\$(.*)$', re.IGNORECASE)

def parse_whitelist_rule(norm):
    """解析白名单规则。
    返回 (global_domain, scoped_rule)：
      - global_domain: 可全局放行的域名；作用域规则返回 None
      - scoped_rule:   带 $domain= 的作用域规则（原样写入 whitelist.txt，交 AGH 执行）
    """
    m = _SCOPED_WL_RE.match(norm)
    if not m:
        return extract_domain(norm), None
    modifiers = m.group(2)
    dm = re.search(r'(?:^|,)domain=([^,]+)', modifiers, re.IGNORECASE)
    if not dm:
        return extract_domain(norm), None
    scopes = [x.strip().lower() for x in dm.group(1).split('|') if x.strip()]
    if not scopes:
        return None, None
    own = m.group(1).lower()
    if own.startswith("*."):
        own = own[2:]
    # 作用域覆盖自身或父域时，等价于全局放行
    if all(own == sc or own.endswith("." + sc) for sc in scopes):
        return own, None
    return None, norm

def apply_whitelist(domain_map, wl_domains):
    removed = 0
    result = {}
    wl_set = {w.lower().rstrip('.') for w in wl_domains}
    for k, rule in domain_map.items():
        domain = extract_domain(rule)
        if domain:
            d_lower = domain.lower().rstrip('.')
            # 精确匹配或后缀匹配：沿域名逐级剥离最左标签,判断父域是否在白名单
            matched = False
            parts = d_lower.split('.')
            for i in range(len(parts)):
                sub = '.'.join(parts[i:])
                if sub in wl_set:
                    matched = True
                    break
            if matched:
                removed += 1
                continue
        result[k] = rule
    return result, removed


# 动态DNS / 短链 / 静态托管等「共享域」噪音：这些域下是用户自建内容，不是广告
SHARED_DOMAIN_NOISE = {
    "no-ip.biz", "no-ip.org", "no-ip.info", "ddns.net", "duckdns.org", "zapto.org",
    "hopto.org", "sytes.net", "myftp.org", "redirectme.net", "servebeer.com",
    "bounceme.net", "freedynamicdns.net", "gotdns.ch", "loginto.me", "myvnc.com",
    "ontheweb.nu", "redhem.net", "servehttp.com", "serveftp.com", "ufcfan.org",
    "withgoogle.com", "workisboring.com", "web.app", "glitch.me", "r2.dev",
    "000webhostapp.com", "webwave.dev", "blogspot.com",
}

def is_shared_noise(domain):
    """判断域名是否属于共享托管/动态DNS噪音（拦了会误伤用户自建服务）。"""
    if not domain:
        return False
    d = domain.lower()
    for n in SHARED_DOMAIN_NOISE:
        if d == n or d.endswith("." + n):
            return True
    return False

def drop_subdomain_redundancy(domain_map):
    """删除「父域规则已存在且无修饰符」的子域规则。
    AGH 语义下 ||parent^ 已覆盖全部子域，子域规则纯属冗余。
    父域带 $ 修饰符（如 $third-party/$domain）时语义不同，保留子域。
    子域本身是白名单或带修饰符时也保留。
    """
    dropped = set()
    for d, rule in domain_map.items():
        parts = d.split(".")
        if len(parts) < 3:
            continue
        # 沿标签逐级向上找最近的祖先规则，只删「被祖先直接覆盖」的
        prule = None
        for i in range(1, len(parts) - 1):
            cand = ".".join(parts[i:])
            r = domain_map.get(cand)
            if r is not None:
                prule = r
                break
        if not prule:
            continue
        if "$" in prule or "$" in rule:
            continue
        if rule.startswith("@@") or prule.startswith("@@"):
            continue
        # 祖先规则必须真的覆盖该子域（祖先域名是它的后缀）
        if not d.endswith("." + cand):
            continue
        dropped.add(d)
    for d in dropped:
        del domain_map[d]
    return len(dropped)

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
            norm = normalize_rule(line)
            if not norm:
                continue
            if not is_dns_compatible(norm):
                continue
            dns_ok += 1
            domain = extract_domain(norm)
            if domain and domain not in domain_map:
                domain_map[domain] = norm
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
                norm = normalize_rule(line)
                if not norm:
                    continue
                if not is_dns_compatible(norm):
                    continue
                dns_ok += 1
                domain = extract_domain(norm)
                if domain and domain not in domain_map:
                    domain_map[domain] = norm
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
    scoped_total = 0
    failed_sources = []

    for src in wl_sources:
        name, url, desc = src["name"], src["url"], src.get("desc", "")
        print("  📁 %s: %s" % (name, desc))
        scoped_here = 0
        content = get_source_content(src)
        if not content:
            print("      → ❌ failed (URL 失效，已跳过)")
            failed_sources.append(name)
            continue
        count = 0
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
                continue
            norm = normalize_rule(line) or line  # 兼容 hosts/裸域名白名单源
            if not is_dns_compatible(norm):
                continue
            gdom, scoped = parse_whitelist_rule(norm)
            if scoped:
                wl_rules.append(scoped)
                scoped_here += 1
                continue
            if gdom:
                wl_domains.add(gdom)
                wl_rules.append(norm)
                count += 1
        msg = "      → %s DNS白名单" % "{:,}".format(count)
        if scoped_here:
            msg += " (+%s 作用域规则, 交 AGH 执行)" % "{:,}".format(scoped_here)
        print(msg)
        scoped_total += scoped_here

    custom_count = 0
    for rule in wl_custom:
        gdom, scoped = parse_whitelist_rule(rule)
        if scoped:
            wl_rules.append(scoped)
            scoped_total += 1
            continue
        if gdom:
            wl_domains.add(gdom)
            wl_rules.append(rule)
            custom_count += 1
    print("  ✏️ Custom: %s rules, 总白名单域名: %s" % (custom_count, "{:,}".format(len(wl_domains))))
    if scoped_total:
        print("  ℹ️ 作用域白名单 %s 条已写入 whitelist.txt（不全局放行）" % "{:,}".format(scoped_total))
    if failed_sources:
        print("  ⚠️ 以下白名单源下载失败，请检查 URL: %s" % ", ".join(failed_sources))
        if os.environ.get("STRICT_SOURCES") == "1":
            raise SystemExit("白名单源必须全部可用（STRICT_SOURCES=1），终止。")

    # 4. 应用白名单
    print("\n✂️ Applying whitelist (标准版应用，完整版跳过)...")
    std_final, std_wl_rm = apply_whitelist(std_map, wl_domains)
    full_final = full_map
    print("  标准版: 去掉 %s 条 → %s 条" % ("{:,}".format(std_wl_rm), "{:,}".format(len(std_final))))
    print("  完整版: 保留全量 %s 条 (不去白名单)" % "{:,}".format(len(full_final)))

    final_wl = list(dict.fromkeys(wl_rules))

    # 4.5 精简：去共享域噪音 + 去子域冗余（语义等价，规则数大幅下降）
    print("\n✂️ Trimming redundancy...")
    noise_full = 0
    for k in list(full_map):
        if is_shared_noise(extract_domain(full_map[k])):
            del full_map[k]
            noise_full += 1
    noise_std = 0
    for k in list(std_final):
        if is_shared_noise(extract_domain(std_final[k])):
            del std_final[k]
            noise_std += 1
    sub_full = drop_subdomain_redundancy(full_map)
    sub_std = drop_subdomain_redundancy(std_final)
    print("  共享域噪音: 完整版 -%s, 标准版 -%s" % ("{:,}".format(noise_full), "{:,}".format(noise_std)))
    print("  子域冗余:   完整版 -%s, 标准版 -%s" % ("{:,}".format(sub_full), "{:,}".format(sub_std)))

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

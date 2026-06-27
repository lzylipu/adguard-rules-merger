#!/usr/bin/env python3
"""
🛡️ AdGuard Home Rules Merger
Downloads, parses, deduplicates and merges blocklist + whitelist sources.
Outputs: blocklist.txt, whitelist.txt, stats.json
"""

import yaml
import re
import json
import hashlib
import time
import sys
import os
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── Config ───
SOURCES_FILE = os.environ.get("SOURCES_FILE", "sources.yaml")
USER_AGENT = "AdGuardRulesMerger/1.0"
TIMEOUT = 60
CST = timezone(timedelta(hours=8))

# ─── Helpers ───
def fetch_url(url, retries=2):
    """Fetch URL content with retry."""
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError, Exception) as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            print(f"  ⚠️  Failed: {url} -> {e}", file=sys.stderr)
            return None

def parse_rules(text, source_name=""):
    """Parse adblock/hosts format into normalized rules."""
    rules = set()
    if not text:
        return rules
    for line in text.splitlines():
        line = line.strip()
        # Skip empty, comments, headers
        if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
            continue
        # Skip cosmetic rules (##, !!#) — not DNS compatible
        if "##" in line and not line.startswith("@@"):
            continue
        # Skip element hiding, script injection
        if line.startswith("!#"):
            continue
        # Normalize: trim whitespace
        rule = line.strip()
        if not rule:
            continue
        rules.add(rule)
    return rules

def extract_domains_from_whitelist(text):
    """Extract domain patterns from whitelist sources."""
    rules = set()
    if not text:
        return rules
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("#") or line.startswith("["):
            continue
        # Accept @@ rules and ||domain^ patterns
        if line.startswith("@@") or line.startswith("||"):
            rules.add(line)
        elif "." in line and not line.startswith("/"):
            # Plain domain -> convert to adblock format
            domain = line.strip()
            if not domain.startswith("||"):
                domain = f"||{domain}^"
            rules.add(domain)
    return rules

def normalize_for_dedup(rule):
    """Normalize a rule for dedup comparison."""
    r = rule.lower().strip()
    # Remove trailing dots/spaces
    r = r.rstrip(". ")
    return r

def domain_from_rule(rule):
    """Extract domain from ||domain^ or @@||domain^ pattern."""
    m = re.match(r'(?:@@)?\|\|([a-z0-9._-]+)\^', rule, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None

# ─── Main ───
def main():
    print("🛡️ AdGuard Home Rules Merger")
    print("=" * 50)

    # Load sources config
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # ── 1. Process Blocklist Sources ──
    print("\n📥 Downloading blocklist sources...")
    blocklist_sources = config.get("blocklist", [])
    all_block_rules = set()
    block_stats = {}

    for src in blocklist_sources:
        name = src["name"]
        url = src["url"]
        desc = src.get("desc", "")
        print(f"  ⬇️  {name}: {desc}")
        content = fetch_url(url)
        if content:
            rules = parse_rules(content, name)
            # Filter DNS-compatible rules only
            dns_rules = set()
            for r in rules:
                # Keep: ||domain^, @@||domain^, /regex/, domain-specific rules
                # Skip: cosmetic (##), script injection ($$)
                if "##" in r and not r.startswith("@@"):
                    continue
                if "$$" in r:
                    continue
                dns_rules.add(r)
            block_stats[name] = {
                "raw_rules": len(rules),
                "dns_rules": len(dns_rules),
                "desc": desc
            }
            all_block_rules.update(dns_rules)
            print(f"      → {len(rules)} raw, {len(dns_rules)} DNS-compatible")
        else:
            block_stats[name] = {"raw_rules": 0, "dns_rules": 0, "error": True}

    print(f"\n📊 Total block rules before dedup: {len(all_block_rules)}")

    # ── 2. Process Whitelist Sources ──
    print("\n🛡️ Downloading whitelist sources...")
    wl_config = config.get("whitelist", {})
    wl_sources = wl_config.get("sources", [])
    wl_custom = wl_config.get("custom", [])

    all_whitelist_rules = set()

    # Upstream whitelist sources
    for src in wl_sources:
        name = src["name"]
        url = src["url"]
        desc = src.get("desc", "")
        print(f"  ⬇️  {name}: {desc}")
        content = fetch_url(url)
        if content:
            rules = extract_domains_from_whitelist(content)
            print(f"      → {len(rules)} whitelist rules")
            all_whitelist_rules.update(rules)
        else:
            print(f"      → ❌ failed")

    # Custom whitelist
    print(f"  ✏️  Custom whitelist: {len(wl_custom)} rules")
    for rule in wl_custom:
        all_whitelist_rules.add(rule)

    print(f"\n📊 Total whitelist rules: {len(all_whitelist_rules)}")

    # ── 3. Deduplicate blocklist ──
    print("\n🔄 Deduplicating blocklist...")
    seen_normalized = {}
    deduped_blocks = set()
    for rule in all_block_rules:
        norm = normalize_for_dedup(rule)
        if norm not in seen_normalized:
            seen_normalized[norm] = rule
            deduped_blocks.add(rule)
        else:
            # Prefer shorter simpler rule
            existing = seen_normalized[norm]
            if len(rule) < len(existing):
                deduped_blocks.discard(existing)
                deduped_blocks.add(rule)
                seen_normalized[norm] = rule

    print(f"  → After dedup: {len(deduped_blocks)} rules (removed {len(all_block_rules) - len(deduped_blocks)} duplicates)")

    # ── 4. Apply whitelist (remove whitelisted domains from blocklist) ──
    print("\n✂️ Applying whitelist exclusions...")
    whitelist_domains = set()
    for wl_rule in all_whitelist_rules:
        dom = domain_from_rule(wl_rule)
        if dom:
            whitelist_domains.add(dom)
    
    # Also extract domains from @@|| patterns in whitelist
    wl_block_patterns = set()
    for wl_rule in all_whitelist_rules:
        if wl_rule.startswith("@@||"):
            dom = domain_from_rule(wl_rule)
            if dom:
                whitelist_domains.add(dom)

    removed_by_whitelist = 0
    final_blocks = set()
    for rule in deduped_blocks:
        dom = domain_from_rule(rule)
        if dom:
            # Check if this domain or its parent is whitelisted
            parts = dom.split(".")
            is_whitelisted = False
            # Check domain and all parent domains
            for i in range(len(parts)):
                parent = ".".join(parts[i:])
                if parent in whitelist_domains:
                    is_whitelisted = True
                    break
            if is_whitelisted:
                removed_by_whitelist += 1
                continue
        final_blocks.add(rule)

    print(f"  → Whitelist removed: {removed_by_whitelist} rules")
    print(f"  → Final blocklist: {len(final_blocks)} rules")

    # ── 5. Deduplicate whitelist ──
    print("\n🔄 Deduplicating whitelist...")
    wl_seen = {}
    final_whitelist = set()
    for rule in all_whitelist_rules:
        norm = normalize_for_dedup(rule)
        if norm not in wl_seen:
            wl_seen[norm] = rule
            final_whitelist.add(rule)
    print(f"  → After dedup: {len(final_whitelist)} rules")

    # ── 6. Write output files ──
    print("\n💾 Writing output files...")
    now = datetime.now(CST)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S (UTC+8)")

    # blocklist.txt
    header = f"""! 🛡️ AdGuard Home Merged Blocklist
! Auto-merged by adguard-rules-merger
! Updated: {timestamp}
! Sources: {len(blocklist_sources)} blocklist + {len(wl_sources)} whitelist + {len(wl_custom)} custom
! Rules: {len(final_blocks)} (deduped & whitelisted)
! License: https://github.com/lzylipu/adguard-rules-merger
! ============================================================
"""
    with open("blocklist.txt", "w", encoding="utf-8") as f:
        f.write(header)
        for rule in sorted(final_blocks):
            f.write(rule + "\n")

    # whitelist.txt
    wl_header = f"""! ✅ AdGuard Home Merged Whitelist
! Auto-merged by adguard-rules-merger
! Updated: {timestamp}
! Sources: {len(wl_sources)} upstream + {len(wl_custom)} custom
! Rules: {len(final_whitelist)} (deduped)
! ============================================================
"""
    with open("whitelist.txt", "w", encoding="utf-8") as f:
        f.write(wl_header)
        for rule in sorted(final_whitelist):
            f.write(rule + "\n")

    # stats.json
    stats = {
        "updated": timestamp,
        "blocklist": {
            "total": len(final_blocks),
            "before_dedup": len(all_block_rules),
            "duplicates_removed": len(all_block_rules) - len(deduped_blocks),
            "whitelist_removed": removed_by_whitelist,
            "sources": block_stats,
        },
        "whitelist": {
            "total": len(final_whitelist),
            "upstream_sources": len(wl_sources),
            "custom_rules": len(wl_custom),
        },
    }
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done!")
    print(f"  📄 blocklist.txt   → {len(final_blocks):,} rules")
    print(f"  ✅ whitelist.txt    → {len(final_whitelist):,} rules")
    print(f"  📊 stats.json      → generated")

if __name__ == "__main__":
    main()

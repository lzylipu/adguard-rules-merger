<div align="center">

# 🛡️ AdGuard Rules Merger

**Auto-merge, deduplicate and whitelist-filter AdGuard Home DNS blocklists → GitHub Pages**

[![Merge Workflow](https://img.shields.io/github/actions/workflow/status/lzylipu/adguard-rules-merger/merge.yml?style=flat-square&label=merge)](../../actions)
[![Rules Updated](https://img.shields.io/github/last-commit/lzylipu/adguard-rules-merger/gh-pages?style=flat-square&label=rules%20updated)](https://github.com/lzylipu/adguard-rules-merger/tree/gh-pages)
[![License](https://img.shields.io/github/license/lzylipu/adguard-rules-merger?style=flat-square)](./LICENSE)

**English | [简体中文](./README.md)**

</div>

---

> 🛡️ Pulls 12 DNS-native filter sources every 5 hours (plus 2 whitelist sources), auto-merges and deduplicates them, filters out browser-only rules for DNS-layer compatibility, and publishes three files via GitHub Pages: `blocklist.txt` (standard), `blocklist-full.txt` (full) and `whitelist.txt`.

---

## ✨ Core Features

- 🔄 **Auto Update** — Pulls 12 DNS-native rule sources every 5 hours, merges and deduplicates automatically
- 🔒 **DNS-Pure Compatibility** — Automatically filters out browser-only rules, keeping only DNS-layer applicable ones
- 🎯 **Cross-source Dedup** — Global domain deduplication to reduce redundancy
- 🛡️ **Whitelist Protection** — The standard build applies the whitelist automatically; the full build requires a separate whitelist subscription (against false positives)
- 💾 **Local Caching** — All sources are synced to `sources/` for stable offline merging
- 🛡️ **Core Domain Protection** — Automatically skips core services such as `youtube.com`, `google.com`, `baidu.com`
- 📊 **Transparent Stats** — Rule counts are refreshed automatically on every merge

## 📥 Subscribe

| Purpose | URL | Notes |
|---------|-----|-------|
| 🚫 **Standard** | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` | **Recommended for daily use**, whitelist applied |
| 🚫 **Full** | `https://lzylipu.github.io/adguard-rules-merger/blocklist-full.txt` | Full 12-source coverage, **no whitelist** (subscribe separately) |
| ✅ **Whitelist** | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` | Anti-false-positive rules, **required with the full build** |
| 📊 **Stats** | `https://lzylipu.github.io/adguard-rules-merger/stats.json` | JSON rule statistics |

## 🧩 Sources

> ⚠️ **GOODBYEADS note**: migrated from the deleted `868864/DNS_RULE` to `8680/GOODBYEADS`.

- **Standard build (7 sources)**: GOODBYEADS-DNS, Hagezi-Light, Hagezi-DOH, Hagezi-Fake, Anti-Ad, EasyPrivacy, Yoyo
- **Full build (+5 sources)**: Hagezi-Pro, 217heidai-DNS, OISD-Small, 1Hosts-Lite, DandelionSprout
- **Whitelist (2 sources + 40 custom entries)**: GOODBYEADS-Allow, Hagezi-Referral + custom CDN/payment/social/video/shopping rules

For per-source rule counts, see the [Chinese README](./README.md#-规则来源统计) — numbers refresh automatically on every merge.

## 🚀 Quick Start

### Option A — Standard (recommended for daily use)

1. Open **AdGuard Home** → **Filters** → **DNS blocklists**
2. Add: `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
3. Add the whitelist: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
4. ✅ Done. Rules auto-update every 5 hours.

### Option B — Full (maximum blocking)

1. Open **AdGuard Home** → **Filters** → **DNS blocklists**
2. Add: `https://lzylipu.github.io/adguard-rules-merger/blocklist-full.txt`
3. **Required**: also add the whitelist `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
4. ✅ Done. Stronger blocking, but the **whitelist is mandatory** to avoid false positives on domestic CDNs and API services.

## ⚙️ How It Works

```
sources.yaml ──▶ download_sources.py ──▶ sources/*.txt (local cache)
                                       │
merge.py ◀─────────────────────────────┘
   │
   ├───▶ blocklist.txt      ──▶ gh-pages ──▶ your router
   ├───▶ blocklist-full.txt
   ├───▶ whitelist.txt ─────┘
   ├───▶ stats.json ────────┘
   └───▶ README.md (auto-updated rule counts) ◀── CI
```

**Automation flow**: every 5 hours (cron) or on push → download sources → merge & dedup → apply whitelist (standard build) → publish to gh-pages → update stats in README.

## 🔧 Custom Maintenance

Add a new source or whitelist entry in `sources.yaml`, then push:

```yaml
sources:
  - name: my-own-list
    url: https://example.com/ads.txt
    desc: personally maintained rules 🎯

whitelist:
  custom:
    - "||my-essential-site.com^"
```

The push triggers GitHub Actions to rebuild everything automatically.

## 📊 FAQ

**Q: Why must the full build be paired with the whitelist?**
A: The full build carries massive lists (Hagezi-Pro, 217heidai, …) that frequently false-positive on domestic CDNs and API endpoints. The whitelist is the safety net — always subscribe to it.

**Q: Why isn't youtube.com blocked?**
A: The merge script has built-in core-domain protection and automatically skips youtube.com, google.com, baidu.com, etc. to prevent breakage.

**Q: How often do rules update?**
A: Every 5 hours automatically. Editing `sources.yaml` and pushing also triggers an immediate rebuild.

## 📄 License

[MIT](./LICENSE) License

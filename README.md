# 🛡️ AdGuard Rules Merger

<p align="center">
  <strong>Automatically merge, deduplicate & whitelist-filter AdGuard Home DNS blocklists</strong><br>
  <code>10+ sources → 1 blocklist + 1 whitelist → GitHub Pages → Your Router</code>
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/lzylipu/adguard-rules-merger/merge.yml?style=flat-square&label=merge" alt="Workflow">
  <img src="https://img.shields.io/github/last-commit/lzylipu/adguard-rules-merger/gh-pages?style=flat-square&label=rules%20updated" alt="Last updated">
  <img src="https://img.shields.io/github/repo-size/lzylipu/adguard-rules-merger?style=flat-square" alt="Size">
</p>

---

[English] | [中文](#-中文)

## ✨ Features

- 🔄 **Auto Merge** — Pulls from 10+ curated sources every 5 hours
- 🔒 **DNS-Only** — Filters out cosmetic/element-hiding rules, keeps only DNS-compatible entries
- 🎯 **Smart Dedup** — Normalizes and deduplicates across all sources
- 🛡️ **Whitelist Guard** — Upstream + custom whitelists prevent false positives
- 📦 **One URL** — Router/AdGuard pulls a single `blocklist.txt` from GitHub Pages
- ✅ **Anti-False-Positive** — GOODBYEADS + Hagezi native whitelists protect Amazon/Apple/TikTok etc.

## 📥 Subscription URLs

| File | URL | Usage |
|---|---|---|
| 🚫 Blocklist | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` | AdGuard Home → Filters → Add |
| ✅ Whitelist | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` | AdGuard Home → Whitelists → Add |
| 📊 Stats | `https://lzylipu.github.io/adguard-rules-merger/stats.json` | Check rule counts & sources |

## 🧩 Sources

### Blocklist Sources (10)

| Source | Description |
|---|---|
| 217heidai-DNS/Filters/Domain | DNS + browser + domain level blocking |
| GOODBYEADS-DNS | DNS-level ad blocking |
| Anti-Ad | Most popular Chinese DNS adblock |
| EasyListChina | Chinese ad supplement |
| AdGuard-CN-Adservers | AdGuard official Chinese adservers |
| EasyPrivacy | Global privacy/tracking blocker |
| Yoyo | Classic adserver list |
| Hagezi-ProPlus | Ad + tracking + crypto + scam + phishing |

### Whitelist Sources (5)

| Source | Description |
|---|---|
| GOODBYEADS-Allow | Official anti-false-positive whitelist (14k+ rules) |
| AnudeepND-Whitelist | Classic general whitelist (191 rules) |
| Hagezi-Native-Amazon | Protect Amazon shopping features |
| Hagezi-Native-Apple | Protect iCloud/push notifications |
| Hagezi-Native-TikTok | Protect normal TikTok usage |

+ Custom whitelist for Chinese/international core services (28 rules)

## 🚀 Quick Start

1. Open your **AdGuard Home** admin panel
2. Go to **Filters → DNS blocklists → Add blocklist**
3. Paste: `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
4. Go to **Filters → Allowlists → Add allowlist**
5. Paste: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
6. ✅ Done! Rules auto-update every 5 hours.

## ⚙️ How It Works

```
sources.yaml ──▶ merge.py ──▶ blocklist.txt  ──▶ gh-pages ──▶ Your Router
                           ──▶ whitelist.txt ──▶
                           ──▶ stats.json    ──▶
```

1. GitHub Actions triggers every 5 hours (or on push to `sources.yaml`)
2. `merge.py` downloads all sources from `sources.yaml`
3. Parses, filters DNS-incompatible rules, deduplicates
4. Applies whitelist (both upstream + custom) to remove false positives
5. Deploys to `gh-pages` branch

## 🔧 Customization

Edit `sources.yaml` to add/remove sources:

```yaml
blocklist:
  - name: My-List
    url: https://example.com/my-rules.txt
    desc: My custom rules 🎯

whitelist:
  custom:
    - "||my-important-site.com^"
```

Push to `main` → GitHub Actions auto-runs → Rules updated within minutes.

## 📊 Why Whitelists Matter

AdGuard Home operates at the DNS level — it can't see page content, only domain names.
This means **aggressive blocklists will break things** you actually use:

| Problem | Whitelist Fix |
|---|---|
| Amazon shopping broken | Hagezi Native Amazon 🛒 |
| Apple push notifications fail | Hagezi Native Apple 🍎 |
| TikTok won't load videos | Hagezi Native TikTok 🎵 |
| Bilibili/QQ/Taobao blocked | Custom CN whitelist 🇨🇳 |
| Payment APIs fail | Custom payment whitelist 💳 |

**Using a blocklist without a whitelist is like installing a burglar alarm that locks YOU out.** 🔐

## 📁 File Structure

```
adguard-rules-merger/
├── .github/workflows/
│   └── merge.yml          # GitHub Actions workflow
├── sources.yaml            # Source configuration (block + white)
├── merge.py                # Merge & dedup script
└── README.md               # This file
```

**Generated on `gh-pages` branch:**
```
gh-pages/
├── blocklist.txt           # Merged & deduped blocklist
├── whitelist.txt           # Merged & deduped whitelist
└── stats.json              # Statistics & metadata
```

## 📜 License

MIT — Use freely, modify as you wish.

---

<a id="-中文"></a>

## 🛡️ AdGuard 规则合并器

<p align="center">
  <strong>自动合并、去重、白名单过滤 AdGuard Home DNS 拦截规则</strong><br>
  <code>10+ 规则源 → 1个黑名单 + 1个白名单 → GitHub Pages → 你的路由器</code>
</p>

[English](#-english) | [中文]

### ✨ 特性

- 🔄 **自动合并** — 每5小时自动拉取10+精选规则源
- 🔒 **DNS兼容** — 自动过滤掉元素隐藏等浏览器专用规则，只保留DNS层可用的
- 🎯 **智能去重** — 跨源归一化去重，减少冗余
- 🛡️ **白名单保护** — 上游白名单 + 自定义白名单双保险，防止误杀
- 📦 **单一URL** — 路由器/AdGuard只需订阅一个地址
- ✅ **反误杀** — GOODBYEADS + Hagezi原生白名单保护 Amazon/Apple/TikTok 等

### 📥 订阅地址

| 文件 | 地址 | 用途 |
|---|---|---|
| 🚫 黑名单 | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` | AdGuard Home → 过滤器 → 添加拦截列表 |
| ✅ 白名单 | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` | AdGuard Home → 过滤器 → 添加白名单 |
| 📊 统计 | `https://lzylipu.github.io/adguard-rules-merger/stats.json` | 查看规则数量和来源 |

### 🧩 规则源

#### 黑名单源 (10个)

| 来源 | 说明 |
|---|---|
| 217heidai-DNS/Filters/Domain | DNS + 浏览器 + 域名三级拦截 |
| GOODBYEADS-DNS | DNS层去广告 |
| Anti-Ad | 国内最流行中文DNS去广告 |
| EasyListChina | 中文广告专项补充 |
| AdGuard-CN-Adservers | AdGuard官方中文广告服务器 |
| EasyPrivacy | 全球隐私追踪拦截 |
| Yoyo | 经典广告服务器列表 |
| Hagezi-ProPlus | 广告+追踪+挖矿+诈骗+仿冒全覆盖 |

#### 白名单源 (5个)

| 来源 | 说明 |
|---|---|
| GOODBYEADS-Allow | 官方反误杀白名单(1.4万+条) |
| AnudeepND-Whitelist | 经典通用白名单(191条) |
| Hagezi-Native-Amazon | 保护亚马逊购物功能 🛒 |
| Hagezi-Native-Apple | 保护iCloud/推送通知 🍎 |
| Hagezi-Native-TikTok | 保护抖音正常使用 🎵 |

+ 自定义白名单保护国内/国际核心服务(28条)

### 🚀 快速使用

1. 打开 **AdGuard Home** 管理后台
2. 进入 **过滤器 → DNS拦截列表 → 添加拦截列表**
3. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
4. 进入 **过滤器 → 白名单 → 添加白名单**
5. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
6. ✅ 完成！规则每5小时自动更新。

### 🔧 自定义

编辑 `sources.yaml` 添加/删除规则源：

```yaml
blocklist:
  - name: 我的规则
    url: https://example.com/my-rules.txt
    desc: 自定义规则 🎯

whitelist:
  custom:
    - "||my-important-site.com^"
```

推送到 `main` 分支 → GitHub Actions 自动运行 → 规则分钟级更新。

### 📊 为什么白名单很重要？

AdGuard Home 工作在 DNS 层——它看不到网页内容，只能看到域名。
这意味着**激进的拦截规则会误杀你正在用的功能**：

| 问题 | 白名单保护 |
|---|---|
| 亚马逊购物异常 | Hagezi Native Amazon 🛒 |
| 苹果推送通知失败 | Hagezi Native Apple 🍎 |
| 抖音视频加载不出 | Hagezi Native TikTok 🎵 |
| B站/QQ/淘宝被拦 | 自定义国内白名单 🇨🇳 |
| 支付接口被拦截 | 自定义支付白名单 💳 |

**用黑名单不加白名单，就像装了防盗门却把自己锁在外面。** 🔐

### 📁 文件结构

```
adguard-rules-merger/
├── .github/workflows/
│   └── merge.yml          # GitHub Actions 工作流
├── sources.yaml            # 规则源配置（黑名单+白名单）
├── merge.py                # 合并去重脚本
└── README.md               # 本文件
```

**`gh-pages` 分支自动生成：**
```
gh-pages/
├── blocklist.txt           # 合并去重后的黑名单
├── whitelist.txt           # 合并去重后的白名单
└── stats.json              # 统计信息
```

### 📜 许可证

MIT — 自由使用，随意修改。

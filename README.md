# 🛡️ AdGuard 规则合并器

<p align="center">
  <strong>自动合并、去重、白名单过滤 AdGuard Home DNS 拦截规则</strong><br>
  <code>13 规则源 → blocklist.txt(标准版) + blocklist-full.txt(完整版) + whitelist.txt → GitHub Pages</code>
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/lzylipu/adguard-rules-merger/merge.yml?style=flat-square&label=merge" alt="Workflow">
  <img src="https://img.shields.io/github/last-commit/lzylipu/adguard-rules-merger/gh-pages?style=flat-square&label=rules%20updated" alt="Last updated">
  <img src="https://img.shields.io/github/repo-size/lzylipu/adguard-rules-merger?style=flat-square" alt="Size">
</p>

---

[中文] | [English](#-english)

## ✨ 特性

- 🔄 **自动合并** — 每 5 小时自动拉取 13 个精选规则源
- 🔒 **DNS 兼容** — 自动过滤元素隐藏等浏览器专用规则，只保留 DNS 层可用的
- 🎯 **智能去重** — 跨源归一化去重，减少冗余
- 🛡️ **白名单保护** — 标准版应用白名单去误杀；完整版不去白名单（用户单独订阅 `whitelist.txt`）
- 📦 **单一 URL** — 路由器/AdGuard 只需订阅一个地址
- ✅ **反误杀** — Hagezi 推荐来源白名单 + 国内核心服务保护
- 🌐 **浏览器→DNS 转换** — 自动从 EasyListChina 等浏览器规则提取域名，转为 DNS 规则
- 💾 **本地化缓存** — 所有源同步到仓库 `sources/` 目录，离线合并稳定可靠
- 📊 **自动统计** — 每次合并后自动更新本文档的规则数统计

## 📥 订阅地址

| 文件 | 地址 | 用途 |
|------|------|------|
| 🚫 黑名单 (标准) | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` | AdGuard Home → 过滤器 → 添加拦截列表（推荐日常使用） |
| 🚫 黑名单 (完整) | `https://lzylipu.github.io/adguard-rules-merger/blocklist-full.txt` | 完整版，13 源全量合并，**不去白名单** |
| ✅ 白名单 | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` | AdGuard Home → 过滤器 → 添加白名单（完整版用户必订） |
| 📊 统计 | `https://lzylipu.github.io/adguard-rules-merger/stats.json` | 查看规则数量和来源 |

## 🧩 规则来源统计

> ⚠️ **GOODBYEADS 仓库迁移**: 原 `868864/DNS_RULE` 已被删除，现使用 `8680/GOODBYEADS`（master 分支）

### 🟢 标准版（7 源，推荐日常使用）

| 来源 | 说明 | 规则数 (||) |
|------|------|------------|
| GOODBYEADS-DNS | DNS 层去广告，中文优先 🇨🇳 | 116,505 |
| Hagezi-Light | 广告 + 追踪精简版 | 43,372 |
| Hagezi-DOH | DoH 绕过域名 | 3,437 |
| Hagezi-Fake | 仿冒/钓鱼域名拦截 | 16,851 |
| Anti-Ad | 中文 DNS 首选，easylist 格式 🇨🇳 | 97,540 |
| EasyPrivacy | 全球隐私追踪拦截 | 46,897 |
| Yoyo | 经典广告服务器列表 | 3,507 |
| **小计** | ~328k → **去重 + 白名单** | → **161,520** |

### 🔵 完整版（+6 源，13 源全量）

| 来源 | 说明 | 规则数 (||) |
|------|------|------------|
| EasyListChina | 中文广告专项 + 浏览器→DNS 自动转换 🇨🇳 | 61,355 |
| Hagezi-Pro | 广告 + 追踪 + 挖矿 + 诈骗 + 仿冒全覆盖 | 230,539 |
| 217heidai-DNS | DNS 规则合并（纯域名格式） | 71,802 |
| OISD-Small | 社区轻量推荐，Block. Don't break. 🆕 | 61,267 |
| 1Hosts-Lite | badmojr 维护，专注广告追踪 🆕 | 3,475 |
| DandelionSprout | 反恶意软件 + 诈骗，AG Home 原生 🆕 | 11,451 |
| **小计** | ~1.2M → **跨源去重（不含白名单）** | → **346,981** |

### ⚪ 白名单（2 源 + 40 条自定义）

| 来源 | 说明 | DNS 白名单数 |
|------|------|-------------|
| GOODBYEADS-Allow | GOODBYEADS 白名单 | 732 |
| Hagezi-Whitelist-Referral | HaGeZi 推荐来源保护 | 923 |
| **自定义规则** | CDN、包管理、云存储、支付、社交、视频、电商等 | 40 |
| **小计** | 防止核心服务误杀 | → **1,694** |

## 🚀 快速使用

### 方案 A：标准版（推荐，新手）

1. 打开 **AdGuard Home** 管理后台
2. 进入 **过滤器 → DNS 拦截列表 → 添加拦截列表**
3. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
4. 进入 **过滤器 → 白名单 → 添加白名单**
5. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
6. ✅ 完成！规则每 5 小时自动更新。

### 方案 B：完整版（追求全覆盖）

1. 打开 **AdGuard Home** 管理后台
2. 进入 **过滤器 → DNS 拦截列表 → 添加拦截列表**
3. 粘贴完整版: `https://lzylipu.github.io/adguard-rules-merger/blocklist-full.txt`
4. 进入 **过滤器 → 白名单 → 添加白名单**
5. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`（**必须订阅，否则误杀严重**）
6. ✅ 完成！规则每 5 小时自动更新。

## ⚙️ 工作原理

```
sources.yaml ──▶ download_sources.py ──▶ sources/*.txt (本地缓存)
                                        │
merge.py ◀──────────────────────────────┘
   │
   ├───▶ blocklist.txt  ──▶ gh-pages ──▶ 你的路由器
   ├───▶ blocklist-full.txt
   ├───▶ whitelist.txt ──┘
   ├───▶ stats.json    ──┘
   └───▶ README.md (自动更新规则数) ◀─── CI
```

### 自动化流程

1. GitHub Actions 每 5 小时触发（或推送 `sources.yaml`/`merge.py` 时立即触发）
2. `download_sources.py` 下载所有规则源到 `sources/` 目录（本地缓存）
3. `merge.py` 从本地缓存读取、解析、过滤 DNS 不兼容规则、跨源去重
4. 浏览器→DNS 转换：从 EasyListChina 等提取 ## 规则域名
5. 应用白名单（**仅标准版**）；完整版不去白名单
6. 生成 `stats.json`、`blocklist*.txt`、`whitelist.txt`
7. **自动更新 README.md** 中的规则数统计表
8. 部署到 `gh-pages` 分支

## 🔧 自定义

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

## 📊 为什么白名单很重要？

白名单防止误杀国内常用服务：
- CDN 加速域名（BootCSS、BootCDN、StaticFile 等）
- 包管理 CDN（unpkg、jsDelivr、cdnjs）
- 云服务商（阿里云、腾讯云、七牛、又排）
- 支付接口（银联）
- 国内主流应用（B 站、微博、知乎、抖音等）

**完整版用户必须订阅 `whitelist.txt`，否则误杀严重！**

## 📈 当前规则统计（自动更新）

> 最后更新：2026-06-28 18:46 (UTC+8) | 版本 v4 (local mode)

| 版本 | 规则数 | 来源 | 白名单 |
|------|--------|------|--------|
| 标准版 `blocklist.txt` | 161,520 | 7 个核心源 | ✅ 已应用 |
| 完整版 `blocklist-full.txt` | 346,981 | 13 个全量源 | ❌ 不应用（用户单独订阅） |
| 白名单 `whitelist.txt` | 1,694 | 2 上游 + 40 自定义 | - |

**浏览器→DNS 转换**: 10,292 域名从 EasyListChina 等元素隐藏规则提取

---

## 🇬🇧 English

### Features

- Auto-merge 13 filter sources every 5 hours
- DNS-only compatible rules (filter browser-specific rules)
- Cross-source deduplication
- Whitelist protection: Standard edition applies whitelist; Full edition does NOT (user subscribes `whitelist.txt` separately)
- Local cache: All sources synced to `sources/` directory for stable offline merge
- Browser→DNS conversion from element hiding rules
- Auto-update README with rule counts after each merge

### Subscribe

- **Standard Blocklist** (recommended): `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
- **Full Blocklist** (comprehensive): `https://lzylipu.github.io/adguard-rules-merger/blocklist-full.txt`
- **Whitelist** (required for Full edition): `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`

### Sources (13 total)

**Standard (7)**: GOODBYEADS-DNS (116k), Hagezi-Light (43k), Hagezi-DOH (3k), Hagezi-Fake (17k), Anti-Ad (97k), EasyPrivacy (47k), Yoyo (3k)

**Full Extra (6)**: EasyListChina (61k), Hagezi-Pro (230k), 217heidai-DNS (72k), OISD-Small (61k), 1Hosts-Lite (3k), DandelionSprout (11k)

**Whitelist (2+40)**: GOODBYEADS-Allow (732), Hagezi-Referral (923) + 40 custom Chinese CDN/service rules

### Note on GOODBYEADS

The original GOODBYEADS repository `868864/DNS_RULE` has been deleted. Current source is `8680/GOODBYEADS` (master branch, `data/rules/dns.txt`).

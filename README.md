# 🛡️ AdGuard 规则合并器

<p align="center">
  <strong>自动合并、去重、白名单过滤 AdGuard Home DNS 拦截规则</strong><br>
  <code>10 规则源 → 1个黑名单 + 1个白名单 → GitHub Pages → 你的路由器</code>
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/lzylipu/adguard-rules-merger/merge.yml?style=flat-square&label=merge" alt="Workflow">
  <img src="https://img.shields.io/github/last-commit/lzylipu/adguard-rules-merger/gh-pages?style=flat-square&label=rules%20updated" alt="Last updated">
  <img src="https://img.shields.io/github/repo-size/lzylipu/adguard-rules-merger?style=flat-square" alt="Size">
</p>

---

[中文] | [English](#-english)

## ✨ 特性

- 🔄 **自动合并** — 每5小时自动拉取10个精选规则源
- 🔒 **DNS兼容** — 自动过滤元素隐藏等浏览器专用规则，只保留DNS层可用的
- 🎯 **智能去重** — 跨源归一化去重，减少冗余
- 🛡️ **白名单保护** — 上游白名单 + 自定义白名单双保险，防止误杀
- 📦 **单一URL** — 路由器/AdGuard只需订阅一个地址
- ✅ **反误杀** — GOODBYEADS官方白名单(1.4万条) + 国内核心服务保护

## 📥 订阅地址

| 文件 | 地址 | 用途 |
|---|---|---|
| 🚫 黑名单 | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` | AdGuard Home → 过滤器 → 添加拦截列表 |
| ✅ 白名单 | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` | AdGuard Home → 过滤器 → 添加白名单 |
| 📊 统计 | `https://lzylipu.github.io/adguard-rules-merger/stats.json` | 查看规则数量和来源 |

## 🧩 规则源

### 黑名单源 (10个)

| 来源 | 说明 |
|---|---|
| 217heidai-DNS/Filters/Domain | DNS + 浏览器 + 域名三级拦截 |
| GOODBYEADS-DNS | DNS层去广告 |
| Anti-Ad | 国内最流行中文DNS去广告 🇨🇳 |
| EasyListChina | 中文广告专项补充 |
| AdGuard-CN-Adservers | AdGuard官方中文广告服务器 |
| EasyPrivacy | 全球隐私追踪拦截 |
| Yoyo | 经典广告服务器列表 |
| Hagezi-ProPlus | 广告+追踪+挖矿+诈骗+仿冒全覆盖 |

### 白名单源 (2个 + 自定义)

| 来源 | 说明 |
|---|---|
| GOODBYEADS-Allow | 官方反误杀白名单(1.4万条) ✅ |
| Hagezi-Native-TikTok | 抖音/TikTok反误杀 🎵 |

+ 自定义白名单保护国内核心服务：B站、QQ、淘宝、京东、支付宝、微信、抖音、支付接口、流媒体等(35条)

## 🚀 快速使用

1. 打开 **AdGuard Home** 管理后台
2. 进入 **过滤器 → DNS拦截列表 → 添加拦截列表**
3. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt`
4. 进入 **过滤器 → 白名单 → 添加白名单**
5. 粘贴: `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt`
6. ✅ 完成！规则每5小时自动更新。

## ⚙️ 工作原理

```
sources.yaml ──▶ merge.py ──▶ blocklist.txt  ──▶ gh-pages ──▶ 你的路由器
                           ──▶ whitelist.txt ──┘
                           ──▶ stats.json    ──┘
```

1. GitHub Actions 每5小时触发（或推送 `sources.yaml` 时立即触发）
2. `merge.py` 下载 `sources.yaml` 中配置的所有规则源
3. 解析、过滤DNS不兼容规则、跨源去重
4. 应用白名单（上游 + 自定义），移除误杀项
5. 部署到 `gh-pages` 分支

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

AdGuard Home 工作在 DNS 层——它看不到网页内容，只能看到域名。
**激进的拦截规则会误杀你正在用的功能**：

| 问题 | 白名单保护 |
|---|---|
| B站/QQ/淘宝被拦 | 自定义国内大站白名单 🇨🇳 |
| 抖音视频加载不出 | Hagezi Native TikTok 🎵 |
| 支付接口被拦截 | 自定义支付白名单 💳 |
| 微信小程序打不开 | 自定义微信生态白名单 💚 |

**用黑名单不加白名单，就像装了防盗门却把自己锁外面。** 🔐

## 📁 文件结构

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

## 📜 许可证

MIT — 自由使用，随意修改。

---

<a id="user-content-english"></a>

## 🛡️ AdGuard Rules Merger

<p align="center">
  <strong>Automatically merge, deduplicate & whitelist-filter AdGuard Home DNS blocklists</strong><br>
  <code>10 sources → 1 blocklist + 1 whitelist → GitHub Pages → Your Router</code>
</p>

[中文](#user-content-中文) | [English]

### ✨ Features

- 🔄 **Auto Merge** — Pulls from 10 curated sources every 5 hours
- 🔒 **DNS-Only** — Filters out cosmetic rules, keeps only DNS-compatible entries
- 🎯 **Smart Dedup** — Normalizes and deduplicates across all sources
- 🛡️ **Whitelist Guard** — Upstream + custom whitelists prevent false positives
- 📦 **One URL** — Router/AdGuard pulls a single `blocklist.txt` from GitHub Pages

### 📥 Subscription URLs

| File | URL |
|---|---|
| 🚫 Blocklist | `https://lzylipu.github.io/adguard-rules-merger/blocklist.txt` |
| ✅ Whitelist | `https://lzylipu.github.io/adguard-rules-merger/whitelist.txt` |
| 📊 Stats | `https://lzylipu.github.io/adguard-rules-merger/stats.json` |

### 🔧 Customize

Edit `sources.yaml` and push to `main` — GitHub Actions handles the rest.

### 📜 License

MIT — Use freely, modify as you wish.

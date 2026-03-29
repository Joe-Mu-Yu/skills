---
name: x-to-markdown-no-login
description: 当需要将 X (Twitter) 推文、线程或链接文章转换为干净的 Markdown 文件且不提供登录信息、API Key 或 Cookies 时使用。此技能通过浏览器模拟（Playwright）抓取公开内容，并支持自动下载图片和转换关联文章为 LLM 友好的 Markdown 格式。触发词：`X`, `Twitter`, `推文`, `Markdown`, `不登录`, `转 Markdown`.
trigger_words: ['X to Markdown', 'Twitter', '推文转 Markdown', 'x.com']
---

# X to Markdown (No-Login Version)

## 概述

这是一个专为“无需登录”场景设计的 X/Twitter 存档工具。它通过自动化浏览器（Playwright）模拟人类访问，直接抓取页面内容，并结合 `markdownify`、`markitdown` 和 `trafilatura` 等库，将复杂的推文 HTML、图片、推文线程以及推文链接的外部文章统一转换为结构清晰、包含 YAML 元数据的干净 Markdown 文件。

## 何时使用

1.  **无需登录**：当用户不想或无法提供 X 的 Cookies、Bearer Token 或账号信息时。
2.  **内容存档**：需要将推文（包括较长的推文或线程）保存为本地笔记（如 Obsidian, Logseq, Notion）。
3.  **多源转换**：原推文中包含大量外部文章链接，且希望一并提取其正文内容。
4.  **图片本地化**：希望将推文中的图片自动下载并以本地链接形式保存在 Markdown 中。

## 核心流程

1.  **接收 URL**：用户提供推文链接。
2.  **浏览器模拟**：使用 Playwright 无头模式访问页面，自动滚动以加载线程内容。
3.  **内容提取**：捕获推文 HTML、图片 URL 和关联外链。
4.  **自动命名与路径**：默认将文件保存至 `/Users/morgan/WorkSpace/Clippings`，文件名自动提取推文第一行内容并进行安全清理。
5.  **图片处理**：自动下载图片至本地 `imgs/` 目录，并更新 Markdown 中的引用路径。
6.  **外链处理**：识别推文中的 `t.co` 链接，提取真实 URL，并并发抓取文章正文。
7.  **文件输出**：生成包含 YAML 前置信息（Title, Author, Date, URL, Tags）的最终 Markdown。

## 依赖项

- **Python >= 3.10**
- **Libraries**: `playwright`, `markdownify`, `markitdown`, `trafilatura`, `requests`, `aiohttp`
- **Shell**: 需要安装 Chromium 浏览器驱动 (`playwright install chromium`)

## 使用示例

调用脚本（默认保存至 Clippings）：

```bash
/opt/homebrew/bin/python3.11 /Users/morgan/WorkSpace/06-工具/skills/x-to-markdown-no-login/scripts/main.py [TWEET_URL]
```

生成的 Markdown 文件示例：
`/Users/morgan/WorkSpace/07-资产/Clippings/顶尖学生的笔记方法论_2036105439256166808.md`

生成的 Markdown 文件示例（YAML 部分）：

```markdown
---
title: X 推文存档 - 2035945586751619284
author: GoSailGlobal
date: 2026-03-24 01:23
url: https://x.com/GoSailGlobal/status/2035945586751619284
tags: [x-archive, twitter]
---

# 推文正文

### 原推文内容...
![img](imgs/GoSailGlobal_2035945586751619284/tweet_0_img_0.jpg)

## 关联文章: https://...
...
```

## 常见错误与排查

- **TimeoutError**: 在网络不佳或 X 反爬较重时，`page.goto` 可能超时。建议适当增加网络等待时间或使用代理。
- **Selector Not Found**: 如果 X 的 DOM 结构发生剧烈变化（如 `data-testid="tweet"` 变动），可能无法提取内容。
- **Python Version**: 必须使用 Python 3.10 及以上版本，否则 `markitdown` 无法正常导入。
- **Playwright No Binary**: 如果提示找不到浏览器，请运行 `/opt/homebrew/bin/python3.11 -m playwright install chromium`。

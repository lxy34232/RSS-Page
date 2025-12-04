# RSS-Page

📰 一个自动抓取 RSS 源并生成静态新闻聚合页面的项目。

## 功能特点

- 🔄 **自动抓取**: 使用 Python 脚本定期抓取多个 RSS 源。
- 📁 **分组显示**: 按类别对 RSS 源进行分组展示。
- ✨ **编辑推荐**: 支持手动添加推荐内容，在页面顶部突出显示。
- 📄 **独立源页面**: 可以点击每个信息源，进入专属页面只看该源的内容。
- 🧭 **目录导航**: 页面提供一个浮动目录，方便在不同分组间快速跳转。
- ⏰ **时间过滤**: 支持配置显示时间范围（默认180天）。
- 🚀 **静态生成**: 使用 Astro 静态站点生成器构建页面。
- 📦 **GitHub Actions**: 每 6 小时自动抓取并重新构建。
- 🌐 **GitHub Pages**: 自动部署到 GitHub Pages。

## RSS 源分组

当前配置的 RSS 源按以下分组组织（实际列表请参考 `scripts/fetch_rss.py`）：

| 分组 | RSS 源 |
|------|--------|
| 国家政策 | 中国科学院科研进展、工信部政策文件、发改委发展改革板块 |
| 咨询机构 | 麦肯锡洞察、毕马威洞察、埃森哲洞察、Gartner |
| 研究院所 | 中国科学院科研进展、MIT Technology Review、阿里研究院 |

## 技术栈

- **前端框架**: [Astro](https://astro.build/)
- **RSS 抓取**: Python + feedparser
- **自动化**: GitHub Actions
- **托管**: GitHub Pages

## 本地开发

### 安装依赖

```bash
npm install
pip install feedparser
```

### 抓取 RSS

```bash
# 使用默认180天过滤
npm run fetch-rss

# 或指定天数
python scripts/fetch_rss.py --days 30
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

## 项目结构

```
├── .github/workflows/        # GitHub Actions 工作流
│   └── deploy.yml            # 自动抓取和部署
├── data/                     # 数据存储
│   ├── rss_feeds.json        # 抓取的 RSS 数据
│   └── editor_recommendations.json # 编辑推荐内容
├── scripts/                  # 脚本
│   └── fetch_rss.py          # RSS 抓取脚本
├── src/
│   ├── components/           # Astro 组件
│   │   ├── EditorRecommendation.astro # 编辑推荐组件
│   │   ├── FeedItem.astro           # 单条内容组件
│   │   ├── GroupSection.astro       # 分组区块组件
│   │   ├── SourceSection.astro      # 来源区块组件
│   │   └── TableOfContents.astro    # 目录组件
│   ├── layouts/              # 页面布局
│   └── pages/                # 页面
│       ├── index.astro       # 主页
│       └── feed/[feedname].astro # 单个源的动态页面
└── public/                   # 静态资源
```

## 自定义内容

### 1. 自定义 RSS 源

编辑 `scripts/fetch_rss.py` 中的 `RSS_FEED_GROUPS` 列表来添加或修改 RSS 源分组：

```python
RSS_FEED_GROUPS = [
    {
        "groupName": "分组名称",
        "feeds": [
            {
                "name": "源名称",
                "url": "RSS 源 URL 或 rsshub://path"
            },
            # 添加更多源...
        ]
    },
    # 添加更多分组...
]
```

**支持的 URL 格式**:
-   标准 RSS URL: `https://example.com/feed.xml`
-   RSSHub 路径: `rsshub://namespace/path` (会自动转换为配置的 RSSHub 服务地址)

### 2. 添加编辑推荐

手动编辑 `data/editor_recommendations.json` 文件来添加或修改推荐内容。文件是一个 JSON 数组，每个对象代表一条推荐：

```json
[
  {
    "title": "这是推荐文章的标题",
    "link": "https://example.com/recommended-article",
    "description": "这里是文章的简要描述或推荐语。"
  }
]
```

## License

MIT

# RSS-Page

📰 一个自动抓取 RSS 源并生成静态新闻聚合页面的项目。

## 功能特点

- 🔄 **自动抓取**: 使用 Python 脚本定期抓取多个 RSS 源
- 🚀 **静态生成**: 使用 Astro 静态站点生成器构建页面
- 📦 **GitHub Actions**: 每 6 小时自动抓取并重新构建
- 🌐 **GitHub Pages**: 自动部署到 GitHub Pages

## RSS 源

当前配置的 RSS 源：
- Hacker News (科技新闻)
- BBC News (国际新闻)
- TechCrunch (科技资讯)

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
npm run fetch-rss
# 或
python scripts/fetch_rss.py
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
├── .github/workflows/  # GitHub Actions 工作流
│   └── deploy.yml      # 自动抓取和部署
├── data/               # RSS 数据存储
│   └── rss_feeds.json  # 抓取的 RSS 数据
├── scripts/            # 脚本
│   └── fetch_rss.py    # RSS 抓取脚本
├── src/
│   ├── components/     # Astro 组件
│   ├── layouts/        # 页面布局
│   └── pages/          # 页面
└── public/             # 静态资源
```

## 自定义 RSS 源

编辑 `scripts/fetch_rss.py` 中的 `RSS_FEEDS` 列表来添加或修改 RSS 源：

```python
RSS_FEEDS = [
    {
        "name": "源名称",
        "url": "RSS 源 URL"
    },
    # 添加更多源...
]
```

## License

MIT
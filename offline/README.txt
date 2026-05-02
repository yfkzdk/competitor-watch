赛博监控 v2.0 — 竞品分析平台 (离线演示包)
══════════════════════════════════════════════════════

【使用方法】
  直接双击 index.html 即可浏览全部功能。无需安装任何软件。

  或按需打开：
  · index_v2_offline.html           — 数据仪表板（概览 + 竞品管理 + 图表）
  · product_detail_v2_offline.html  — 竞品详情（价格趋势、情感、变更diff）
  · alerts_v2_offline.html          — 告警中心（告警时间线 + 规则管理）
  · report_v2_offline.html          — 分析报告（AI 战略洞察 + 行动建议）

【技术栈】
  后端:  Python / FastAPI / SQLite / APScheduler
  前端:  Vue 3 / Chart.js / WebSocket
  分析:  jieba 中文分词 / TF-IDF 关键词提取 / LLM 集成

【网络需求】
  · Vue 3 / Chart.js 从 CDN 加载（首次访问需网络，浏览器会缓存）
  · Google Fonts 从 CDN 加载（完全离线时回退到系统默认字体）
  · 所有业务数据已内嵌在 HTML 中，无需 API 服务器

【数据说明】
  包含 5 家竞品（阿里云、腾讯云、华为云、AWS 中国、百度 AI 云）的：
  · 1600+ 条价格历史记录
  · 500+ 条用户评论（含情感评分）
  · 300+ 条变更检测记录
  · 30+ 条告警记录
  · 15 条 AI 分析报告

【关于项目】
  这是一个全栈个人项目，用于展示：
  · 复杂业务系统的前后端架构设计
  · 数据可视化与实时推送能力
  · 中文 NLP 在商业场景中的应用
  · 赛博朋克风格的 UI/UX 设计

  源码地址: 见上级目录 README.md
完整技术文档、架构设计、快速开始请阅读: ../README.md

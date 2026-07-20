# 📊 Ozon BI Dashboard

Ozon 电商平台 SKU 维度 BI 看板 — 多店铺商品同步、订单追踪、利润分析、广告 ROI 一站式。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D?logo=vuedotjs)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element_Plus-2.7+-409EFF)](https://element-plus.org/)
[![ECharts](https://img.shields.io/badge/ECharts-5.5+-AA344D)](https://echarts.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://www.postgresql.org/)

---

## 快速开始

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 配置环境变量（复制 .env 并填入密钥）
# DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
# OZON_CLIENT_ID / OZON_API_KEY

# 3. 初始化数据库（首次）
python scripts/init_db.py

# 4. 同步数据
python scripts/sync_data.py

# 5. 启动后端
uvicorn app.main:app --reload --port 8001

# 6. 启动前端（新终端）
cd frontend && npm install && npm run dev

# 浏览器打开 https://localhost:5173/dashboard
```

---

## 架构

```
浏览器 (Vue 3 :5173)          外部客户端 (curl / 脚本)
      │                              │
      │ Vite 代理                     │ REST API
      │                              │
      └──────────┬───────────────────┘
                 │
          FastAPI Gateway (:8001)
          ├── CORS 中间件
          ├── /api/v1/products    商品 + 库存
          ├── /api/v1/summary     日汇总 + 看板统计
          ├── /api/v1/finance     财务流水
          ├── /api/v1/advertising 广告数据
          ├── /api/v1/returns     退货分析
          ├── /api/v1/orders      订单追踪
          ├── /api/v1/sync        同步控制
          └── /health             健康检查
                 │
          ────── 数据层 ──────
          │
    Ozon Seller API (外部)       PostgreSQL 16
    ├── /v3/product/info/list   ├── ozon.products
    ├── /v3/analytics/data      ├── ozon.sku_daily_summary ← 看板核心表
    ├── /v3/finance/...         ├── ozon.finance_transactions
    ├── /v3/posting/fbs/list    ├── ozon.postings
    ├── /v1/returns/...         ├── ozon.returns
    └── /v1/adv/...             ├── ozon.ad_campaigns / ad_daily_stats / ad_sku_daily_stats
                                └── ozon.sync_log
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python FastAPI | REST API + CORS 中间件 |
| ORM | SQLAlchemy 2.0 | 9 张表，自然主键 + 自增主键混用 |
| 数据库 | PostgreSQL 16 | schema `ozon`，SKU 日汇总为核心 |
| 前端框架 | Vue 3 | Composition API + `<script setup lang="ts">` |
| UI 库 | Element Plus | 全部界面使用 Element Plus 组件 |
| 图表 | ECharts 5 | 趋势折线图 + 柱状图 + 饼图 |
| 构建 | Vite 5 | API 代理 + HMR |
| 外部 API | Ozon Seller API | 商品 / 分析 / 财务 / 订单 / 退货 / 广告 |

---

## 核心特性

### 数据同步

| 特性 | 说明 |
|------|------|
| **商品同步** | 从 Ozon API 拉取全量 SKU 信息 + FBO/FBS 库存 |
| **订单追踪** | posting 生命周期：created → delivered → cancelled，自动计算净销量 |
| **财务同步** | 全部 transaction 类型（orders / returns / service / compensation） |
| **退货分析** | 退货原因分类 + 状态追踪 + 退货率趋势 |
| **广告同步** | 广告活动 + 每日花费 + SKU 级广告统计 |
| **自动汇总** | 每次同步后自动聚合 `sku_daily_summary`，看板查询毫秒级响应 |

### 利润计算

| 特性 | 说明 |
|------|------|
| **收入归因** | `revenue` — 来自 analytics API 的销售收入 |
| **费用明细** | 佣金 / 物流费 / 退货退款 / 仓储费 / 广告费 / 其他费用 — 全部负数存储 |
| **净利润** | `net_profit = revenue + commissions + logistics + returns + storage + advertising + other` |
| **利润率** | `profit_margin = net_profit / revenue × 100%` |
| **数据质量** | `partial`（仅有销售数据）→ `complete`（含财务数据），逐步完善 |

### 前端看板

| 特性 | 说明 |
|------|------|
| **汇总卡片** | 6 张卡片：收入 / 利润 / 利润率 / 订单数 / 费用 / 广告花费 |
| **趋势图** | ECharts 折线图，收入 + 利润双轴对比 |
| **Top 商品** | SKU 排行榜，按收入 / 利润 / 利润率切换排序 |
| **日明细表** | el-table 展示每日 SKU 级数据，支持日期 + SKU 筛选 |
| **库存健康** | FBO/FBS 库存分布 + 缺货预警 |
| **广告分析** | 广告花费 ROI + 活动维度下钻 |
| **成本分析** | 费用构成饼图 + 费用趋势 |
| **退货分析** | 退货率趋势 + 退货原因分布 |
| **订单分析** | posting 状态分布 + 交付时效 |

---

## API 端点

基础路径: `/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/products` | 商品列表（SKU 筛选器数据源） |
| `GET` | `/summary` | SKU 日汇总列表（`?date_from=&date_to=&sku_id=`） |
| `GET` | `/summary/stats` | 看板顶部汇总卡片数据 |
| `GET` | `/summary/trend` | 收入/利润趋势（折线图数据） |
| `GET` | `/finance` | 财务流水明细 |
| `GET` | `/advertising/campaigns` | 广告活动列表 |
| `GET` | `/advertising/stats` | 广告每日/ SKU 级统计 |
| `GET` | `/returns` | 退货列表 + 退货率 |
| `GET` | `/returns/stats` | 退货汇总统计 |
| `GET` | `/orders` | 订单列表 + posting 状态 |
| `GET` | `/orders/stats` | 订单状态分布 |
| `POST` | `/sync` | 手动触发全量同步 |
| `GET` | `/sync/status` | 最近一次同步状态 |
| `GET` | `/health` | 健康检查 |

---

## 数据库

### 表结构 (schema `ozon`)

| 表 | 主键 | 记录数 | 说明 |
|----|------|--------|------|
| `products` | `sku_id` | 39 | 商品主数据 |
| `stocks` | `(sku_id, source)` | 32 | FBO/FBS 库存 |
| `postings` | `posting_number` | 1,934 | 订单追踪 |
| `finance_transactions` | `operation_id` | 5,727 | 财务流水 |
| `returns` | `id` | 363 | 退货记录 |
| `ad_campaigns` | `campaign_id` | 101 | 广告活动 |
| `ad_daily_stats` | `(campaign_id, date)` | 1,011 | 广告日汇总 |
| `ad_sku_daily_stats` | `(sku_id, campaign_id, date)` | 1,412 | 广告 SKU 日汇总 |
| `sku_daily_summary` | `(date, sku_id)` | 2,868 | **看板核心表** |
| `sync_log` | `id` BIGSERIAL | — | 同步审计日志 |

> 主键设计：业务表使用**自然主键**，日志表使用**自增主键**。详见 [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md)。

---

## CLI

```bash
python scripts/init_db.py              # 初始化数据库表结构
python scripts/reset_db.py             # 删表重建（所有 ozon 表）
python scripts/sync_data.py            # 命令行触发全量同步
python scripts/sync_advertising.py     # 单独同步广告数据
python scripts/backfill_ad_sku.py      # 回填广告 SKU 历史数据
python scripts/backfill_delivered_at.py # 回填订单交付时间
python scripts/query_cost.py           # 查询费用明细
```

---

## 项目结构

```
├── app/                          # 后端 FastAPI 应用
│   ├── main.py                   #   入口 + CORS
│   ├── config.py                 #   配置（从 .env 读取）
│   ├── database.py               #   SQLAlchemy 引擎 + 会话
│   ├── models.py                 #   ORM 模型（9 张表，全部字段带中文注释）
│   ├── api/                      #   REST API 路由
│   │   ├── __init__.py           #     APIRouter 聚合
│   │   ├── products.py           #     商品 + 库存
│   │   ├── summary.py            #     日汇总 + 看板统计 + 趋势
│   │   ├── finance.py            #     财务流水
│   │   ├── advertising.py        #     广告数据
│   │   ├── returns.py            #     退货分析
│   │   ├── orders.py             #     订单追踪
│   │   └── sync.py               #     同步控制
│   ├── clients/
│   │   └── ozon.py               #   Ozon Seller API HTTP 客户端
│   ├── schemas/                  #   Pydantic 数据模型
│   └── services/                 #   业务逻辑层
│       ├── product_sync.py       #     商品 + 库存同步
│       ├── analytics_sync.py     #     销售分析同步
│       ├── finance_sync.py       #     财务流水同步
│       ├── posting_sync.py       #     订单 posting 同步
│       ├── summary_service.py    #     SKU 日汇总聚合
│       └── sync_service.py       #     全量同步编排
├── frontend/                     # Vue 3 前端
│   └── src/
│       ├── main.ts               #   入口（Element Plus + 图标）
│       ├── App.vue               #   根组件
│       ├── api/index.ts          #   API 调用函数
│       ├── types/index.ts        #   TypeScript 类型
│       ├── router/index.ts       #   路由
│       ├── composables/          #   业务逻辑
│       │   ├── useDashboard.ts   #     看板筛选/聚合/同步
│       │   └── useOrders.ts      #     订单数据
│       ├── views/
│       │   └── Dashboard.vue     #   主页面布局
│       └── components/           #   图表组件
│           ├── SummaryCards.vue      # 6 张汇总卡
│           ├── TrendChart.vue        # 收入/利润趋势
│           ├── TopProducts.vue       # Top 商品排行
│           ├── DailyTable.vue        # 日明细表格
│           ├── InventoryHealth.vue   # 库存健康
│           ├── AdvertisingAnalysis.vue # 广告分析
│           ├── CostAnalysis.vue      # 费用构成
│           ├── ReturnAnalysis.vue    # 退货分析
│           └── OrderAnalysis.vue     # 订单分析
├── scripts/                      # 工具脚本
├── plan/                         # 设计文档
├── sandbox/                      # API 探索测试
├── .env                          # 数据库 + API 密钥（不提交）
├── CLAUDE.md                     # 开发规范
├── DATA_ARCHITECTURE.md          # 数据架构文档
└── requirements.txt
```

---

## 配置参考

全部配置项见 `.env`，核心项：

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ozon_sku
DB_USER=postgres
DB_PASSWORD=your-password

# Ozon Seller API
OZON_CLIENT_ID=your-client-id
OZON_API_KEY=your-api-key

# 服务端口
API_PORT=8001
```

---

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | 商品 + 库存同步 + 基础看板 | ✅ |
| Phase 2 | 财务流水 + SKU 日汇总 + 利润计算 | ✅ |
| Phase 3 | 订单追踪 + 退货分析 + 广告同步 | ✅ |
| Phase 4 | 库存健康 + 广告 ROI + 成本构成 | ✅ |
| Phase 5 | 订单分析 + 交付时效 + 净销量 | ✅ |
| Phase 6 | 自动化定时同步 + 数据质量标记 | 🔜 |

---

## 开发规范

参见 [CLAUDE.md](CLAUDE.md)，主要原则：

1. **Think Before Coding** — 先想清楚再写
2. **Simplicity First** — 不多写一个不需要的功能
3. **Surgical Changes** — 只改必须改的地方
4. **Vue 3 规范** — Composition API + `<script setup lang="ts">` + Element Plus，不手写原生样式

---

## 文档

- [CLAUDE.md](CLAUDE.md) — 开发规范 + 技术栈约定
- [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) — 数据架构 + 表关系 + 关联方式
- [plan/](plan/) — 架构设计 + 数据库设计 + 阶段路线图

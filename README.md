# Ozon BI Dashboard

Ozon 电商平台 SKU 维度 BI 看板 — 多店铺商品数据同步、财务分析、利润看板。

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Python FastAPI | ≥0.115 |
| ORM | SQLAlchemy 2.0 | ≥2.0 |
| 数据库 | PostgreSQL 16 | — |
| 前端框架 | Vue 3 (Composition API + `<script setup>`) | ≥3.4 |
| UI 库 | Element Plus | ≥2.7 |
| 图表 | ECharts 5 | ≥5.5 |
| 构建 | Vite | ≥5.4 |

## 项目结构

```
ozon-sku/
├── app/                          # 后端 Python 应用
│   ├── main.py                   # FastAPI 入口 + CORS
│   ├── config.py                 # 配置 (从 .env 读取)
│   ├── database.py               # SQLAlchemy 引擎 + 会话
│   ├── models.py                 # ORM 模型 (5 张表，全部字段带中文注释)
│   ├── api/                      # REST API 路由
│   │   ├── __init__.py           # APIRouter 聚合 (/api/v1)
│   │   ├── products.py           # GET /products — 商品列表
│   │   ├── summary.py            # GET /summary, /summary/stats — 看板数据
│   │   └── sync.py               # POST /sync, GET /sync/status — 同步控制
│   ├── clients/
│   │   └── ozon.py               # Ozon Seller API HTTP 客户端
│   ├── schemas/
│   │   ├── product.py            # ProductItem Pydantic 模型
│   │   └── summary.py            # SummaryItem / SummaryStats Pydantic 模型
│   └── services/
│       ├── product_sync.py       # 商品 + 库存同步
│       ├── analytics_sync.py     # 销售分析同步
│       ├── finance_sync.py       # 财务流水同步
│       ├── summary_service.py    # SKU 日汇总聚合
│       └── sync_service.py       # 全量同步编排
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── main.ts               # 入口 (Element Plus + 图标注册)
│   │   ├── App.vue               # 根组件
│   │   ├── api/index.ts          # API 调用函数
│   │   ├── types/index.ts        # TypeScript 类型定义
│   │   ├── router/index.ts       # 路由 (/ → /dashboard)
│   │   ├── composables/
│   │   │   └── useDashboard.ts   # 看板业务逻辑 (筛选/聚合/同步)
│   │   ├── views/
│   │   │   └── Dashboard.vue     # 主页面布局
│   │   └── components/
│   │       ├── SummaryCards.vue   # 6 张汇总卡片
│   │       ├── TrendChart.vue    # 收入/利润趋势折线图
│   │       ├── TopProducts.vue   # Top 10 商品排行榜
│   │       └── DailyTable.vue    # 日销售明细表格
│   ├── vite.config.ts            # Vite + API 代理
│   └── package.json
├── scripts/                      # 工具脚本
│   ├── reset_db.py               # 删表重建 (所有 ozon 表)
│   ├── init_db.py                # 初始化数据库表结构
│   └── sync_data.py              # 命令行触发全量同步
├── sandbox/                      # 探索测试
│   ├── 01_test_db.py
│   ├── 02_test_ozon_api.py
│   ├── 02a_test_product_list.py
│   ├── 02b_test_product_info.py
│   ├── 02c_test_analytics.py
│   └── 02d_test_finance.py
├── plan/                         # 设计文档
├── .env                          # 数据库 + API 密钥 (不提交)
├── .gitignore
├── CLAUDE.md                     # 开发规范
└── requirements.txt
```

## 数据库

### 表结构 (schema `ozon`)

| 表 | 主键 | 说明 |
|----|------|------|
| `products` | `sku_id` | 商品主数据 (Ozon /v3/product/info/list) |
| `stocks` | `(sku_id, source)` | 库存明细 (FBO/FBS) |
| `sku_daily_summary` | `(date, sku_id)` | SKU 日汇总（看板核心表） |
| `finance_transactions` | `operation_id` | 财务流水原始数据 |
| `sync_log` | `id` BIGSERIAL | 同步审计日志 |

主键设计原则：业务表使用**自然主键**（业务上唯一），日志表使用**自增主键**（顺序递增）。

### sku_daily_summary 各字段含义

该表是看板核心，每行 = 一个 SKU 在一天内的汇总：

- **收入**: `revenue` — 来自 analytics API 的销售收入
- **费用**（均为负数）:
  - `commissions` — Ozon 佣金
  - `logistics_costs` — 物流费
  - `returns_amount` — 退货退款
  - `storage_fees` — 仓储费
  - `advertising` — 广告费
  - `other_costs` — 其他费用（银行手续费、包装、销毁等）
- **利润**: `net_profit = revenue + commissions + logistics + returns + storage + advertising + other`
- **利润率**: `profit_margin = net_profit / revenue × 100`
- **数据质量**: `data_quality = partial`（仅有销售数据）/ `complete`（含财务数据）

## API 接口

基础路径: `/api/v1`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/products` | 商品列表（用于 SKU 筛选器） |
| `GET` | `/summary` | 日汇总列表（支持 `?date_from=&date_to=&sku_id=`） |
| `GET` | `/summary/stats` | 看板顶部汇总卡数据 |
| `POST` | `/sync` | 手动触发全量同步 |
| `GET` | `/sync/status` | 最近一次同步状态 |
| `GET` | `/health` | 健康检查 |

## 快速开始

### 1. 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量 .env
# DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
# OZON_CLIENT_ID / OZON_API_KEY

# 初始化数据库（首次）
python scripts/init_db.py

# 同步数据
python scripts/sync_data.py

# 启动 API 服务
uvicorn app.main:app --reload --port 8001
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 https://localhost:5173/dashboard

### 3. 重置数据库

```bash
python scripts/reset_db.py    # 删除所有 ozon 表并重建
python scripts/sync_data.py   # 重新同步
```

## 开发规范

参见 [CLAUDE.md](./CLAUDE.md)，主要原则：

1. **Think Before Coding** — 先想清楚再写
2. **Simplicity First** — 不多写一个不需要的功能
3. **Surgical Changes** — 只改必须改的地方
4. **Vue 3 规范** — Composition API + `<script setup lang="ts">` + Element Plus、不手写原生样式

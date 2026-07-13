# Ozon BI Dashboard — 架构设计与实施计划

> 为 Ozon 电商平台搭建 SKU 维度的 BI 看板，涵盖销售、商品、财务数据，每日自动刷新。
> 先本地开发测试，后续上线部署。

---

## 目录

1. [技术栈](#1-技术栈)
2. [项目结构](#2-项目结构)
3. [数据库设计](#3-数据库设计)
4. [Ozon API 集成](#4-ozon-api-集成)
5. [REST API 设计](#5-rest-api-设计)
6. [前端架构](#6-前端架构)
7. [实施阶段](#7-实施阶段)
8. [部署方案](#8-部署方案)

---

## 1. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端框架** | FastAPI (Python 3.12) | 异步高性能 Web 框架 |
| **数据库** | PostgreSQL (ozon schema) | 独立 schema 隔离 BI 数据 |
| **ORM** | SQLAlchemy 2.0 | 类型安全的数据访问层 |
| **Ozon 客户端** | httpx (AsyncClient) | 异步 HTTP 请求 + tenacity 重试 |
| **定时任务** | APScheduler | 每日凌晨自动同步数据 |
| **前端框架** | Vue 3 + Vite | 现代化前端工程 |
| **UI 组件库** | Element Plus | 表格、日期选择、卡片、分页等 |
| **图表库** | ECharts 5 | 折线图、饼图、堆叠图、双轴图 |
| **状态管理** | Pinia | Vue 3 官方推荐 |
| **HTTP 客户端** | Axios | 前端 API 请求 |

---

## 2. 项目结构

```
OzonSku/
│
├── .env                          # 数据库 + Ozon API 凭证（已存在）
├── .gitignore                    # 已配置
├── requirements.txt              # Python 依赖
├── run.py                        # FastAPI 启动入口
├── docker-compose.yml            # Docker 部署配置（后续）
│
├── app/                          # 后端主包
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用创建 + CORS + 路由注册
│   ├── config.py                 # pydantic-settings 配置读取
│   ├── database.py               # SQLAlchemy 引擎 + 会话工厂
│   │
│   ├── models/                   # 数据库模型
│   │   ├── __init__.py
│   │   ├── base.py               # DeclarativeBase (metadata.schema='ozon')
│   │   ├── product.py            # products 表
│   │   ├── daily_summary.py      # sku_daily_summary 表（核心）
│   │   ├── finance.py            # finance_transactions 表
│   │   └── sync_log.py           # sync_log 表
│   │
│   ├── schemas/                  # Pydantic 响应/请求模型
│   │   ├── __init__.py
│   │   ├── dashboard.py          # 看板相关 schema
│   │   ├── product.py            # 产品相关 schema
│   │   └── sync.py               # 同步相关 schema
│   │
│   ├── api/                      # REST API 路由
│   │   ├── __init__.py
│   │   ├── router.py             # 汇总所有路由
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── dashboard.py      # /api/v1/dashboard/*
│   │       ├── sku.py            # /api/v1/skus/*
│   │       └── sync.py           # /api/v1/sync/*
│   │
│   ├── clients/                  # 外部 API 客户端
│   │   ├── __init__.py
│   │   └── ozon.py               # Ozon Seller API 客户端
│   │
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── sync_service.py       # 同步编排
│   │   ├── product_sync.py       # 产品同步
│   │   ├── analytics_sync.py     # 销售分析同步
│   │   ├── finance_sync.py       # 财务数据同步
│   │   └── summary_service.py    # 汇总表构建
│   │
│   └── scheduler.py              # APScheduler 定时任务
│
├── frontend/                     # 前端（Vue 3 + Vite）
│   ├── package.json
│   ├── vite.config.js            # 开发代理到 :8000
│   ├── index.html
│   │
│   └── src/
│       ├── main.js               # Vue 入口
│       ├── App.vue                # 根组件（侧边栏 + 内容区布局）
│       │
│       ├── router/
│       │   └── index.js           # 路由配置
│       │
│       ├── stores/                # Pinia 状态
│       │   ├── dashboard.js       # 看板数据
│       │   ├── sku.js             # SKU 数据
│       │   └── sync.js            # 同步状态
│       │
│       ├── api/                   # Axios API 调用
│       │   ├── client.js          # Axios 实例
│       │   ├── dashboard.js       # 看板 API
│       │   ├── sku.js             # SKU API
│       │   └── sync.js            # 同步 API
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppHeader.vue   # 顶部导航（标题 + 同步状态 + 时间）
│       │   │   └── AppSidebar.vue  # 侧边栏导航
│       │   │
│       │   ├── dashboard/
│       │   │   ├── KpiCard.vue         # 单指标卡片
│       │   │   ├── KpiRow.vue          # KPI 卡片行
│       │   │   ├── SalesTrendChart.vue # 销售趋势图（折线+柱状）
│       │   │   ├── CategoryPieChart.vue# 品类分布图（环形图）
│       │   │   ├── TopProductsTable.vue# SKU 排名表
│       │   │   └── FinanceBreakdownChart.vue # 费用构成堆叠图
│       │   │
│       │   ├── sku/
│       │   │   └── SkuDailyChart.vue   # 单 SKU 日趋势
│       │   │
│       │   └── common/
│       │       ├── DateRangePicker.vue # 日期范围选择
│       │       ├── LoadingSpinner.vue
│       │       ├── EmptyState.vue
│       │       └── ErrorAlert.vue
│       │
│       ├── views/
│       │   ├── DashboardView.vue   # 主看板页
│       │   ├── SkuListView.vue     # SKU 列表页
│       │   ├── SkuDetailView.vue   # SKU 详情页
│       │   └── SyncSettingsView.vue# 同步管理页
│       │
│       ├── utils/
│       │   ├── formatters.js       # 数值格式化（货币/百分比/缩写）
│       │   └── date.js             # 日期工具
│       │
│       └── assets/styles/
│           ├── variables.css       # 设计变量
│           └── global.css          # 全局样式
│
└── plan/
    └── OzonBI-Architecture-Plan.md # 本文件
```

---

## 3. 数据库设计

所有表位于 **`ozon`** schema，与 `public` schema 下的其他表隔离。

### 3.1 `products` — 商品主数据

```sql
CREATE TABLE ozon.products (
    sku_id          BIGINT PRIMARY KEY,        -- Ozon SKU ID
    product_id      BIGINT NOT NULL,           -- Ozon 商品 ID
    name            TEXT,                      -- 商品名称
    offer_id        VARCHAR(255),              -- 商家 SKU 编码
    category_id     INTEGER,
    category_name   TEXT,
    barcode         VARCHAR(255),
    price           NUMERIC(12,2),             -- 当前售价
    old_price       NUMERIC(12,2),             -- 原价/划线价
    premium_price   NUMERIC(12,2),             -- Premium 价格
    vat             VARCHAR(20),               -- 增值税率
    commission_pct  NUMERIC(10,4),             -- 佣金比例
    fulfillment     VARCHAR(20),               -- 发货方式 (FBO/FBS)
    status          VARCHAR(50),               -- 商品状态
    visibility      VARCHAR(20),               -- 可见性
    images          JSONB,                     -- 图片 URL 列表
    primary_image   TEXT,                      -- 主图 URL
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_products_offer_id ON ozon.products(offer_id);
CREATE INDEX idx_products_category ON ozon.products(category_id);
```

### 3.2 `sku_daily_summary` — 核心聚合表 ⭐

**按 SKU × 日期聚合，是看板所有查询的中心。**

```sql
CREATE TABLE ozon.sku_daily_summary (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    sku_id          BIGINT NOT NULL,
    offer_id        VARCHAR(255),

    -- 销售指标
    orders          INTEGER DEFAULT 0,         -- 订单数
    units_sold      INTEGER DEFAULT 0,         -- 销量
    revenue         NUMERIC(12,2) DEFAULT 0,   -- 收入
    returns         INTEGER DEFAULT 0,         -- 退货数
    cancellations   INTEGER DEFAULT 0,         -- 取消数

    -- 财务指标
    commissions     NUMERIC(12,2) DEFAULT 0,   -- 佣金
    logistics_costs NUMERIC(12,2) DEFAULT 0,   -- 物流费
    storage_fees    NUMERIC(12,2) DEFAULT 0,   -- 仓储费
    net_profit      NUMERIC(12,2) DEFAULT 0,   -- 净利润
    profit_margin   NUMERIC(5,2) DEFAULT 0,    -- 利润率 (%)

    -- 流量指标
    impressions     INTEGER DEFAULT 0,         -- 曝光量
    visits          INTEGER DEFAULT 0,         -- 访客数
    conversion      NUMERIC(8,4) DEFAULT 0,    -- 转化率

    -- 元数据
    data_quality    VARCHAR(20) DEFAULT 'partial',
    synced_at       TIMESTAMP DEFAULT NOW(),

    UNIQUE(date, sku_id)
);

CREATE INDEX idx_summary_date ON ozon.sku_daily_summary(date);
CREATE INDEX idx_summary_sku ON ozon.sku_daily_summary(sku_id);
CREATE INDEX idx_summary_date_sku ON ozon.sku_daily_summary(date, sku_id);
```

### 3.3 `finance_transactions` — 财务流水

```sql
CREATE TABLE ozon.finance_transactions (
    id                  BIGSERIAL PRIMARY KEY,
    transaction_id      VARCHAR(255) UNIQUE,   -- Ozon 交易 ID
    date                DATE NOT NULL,
    sku_id              BIGINT,
    offer_id            VARCHAR(255),
    operation_type      VARCHAR(100),          -- sale/commission/logistics/return 等
    operation_type_name TEXT,
    amount              NUMERIC(12,2),
    currency            VARCHAR(10) DEFAULT 'RUB',
    posting_number      VARCHAR(255),
    description         TEXT,
    sync_batch_id       VARCHAR(100),
    synced_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_finance_date ON ozon.finance_transactions(date);
CREATE INDEX idx_finance_sku ON ozon.finance_transactions(sku_id);
CREATE INDEX idx_finance_type ON ozon.finance_transactions(operation_type);
```

### 3.4 `sync_log` — 同步审计日志

```sql
CREATE TABLE ozon.sync_log (
    id                  BIGSERIAL PRIMARY KEY,
    sync_type           VARCHAR(50) NOT NULL,  -- products/analytics/finance/summary
    status              VARCHAR(20) NOT NULL,  -- running/success/failed/partial
    started_at          TIMESTAMP NOT NULL,
    completed_at        TIMESTAMP,
    records_processed   INTEGER DEFAULT 0,
    date_from           DATE,
    date_to             DATE,
    error_message       TEXT,
    batch_id            VARCHAR(100)
);

CREATE INDEX idx_sync_type ON ozon.sync_log(sync_type, started_at);
```

### 3.5 ER 关系

```
┌─────────────┐       ┌──────────────────────┐       ┌───────────────────────┐
│   products   │       │  sku_daily_summary    │       │ finance_transactions  │
├─────────────┤       ├──────────────────────┤       ├───────────────────────┤
│ sku_id (PK) │──1:N──│ sku_id               │       │ sku_id                │
│ product_id  │       │ date                  │       │ transaction_id (PK)   │
│ name        │       │ orders, revenue       │       │ operation_type        │
│ price       │       │ net_profit            │       │ amount                │
│ category    │       │ impressions, conv     │       │ posting_number        │
└─────────────┘       └──────────────────────┘       └───────────────────────┘
```

---

## 4. Ozon API 集成

### 4.1 认证方式

- **Base URL**: `https://api-seller.ozon.ru`
- **Headers**: `Client-Id` + `Api-Key`（从 `.env` 读取）
- 所有请求均为 POST，JSON payload

### 4.2 使用到的 API 端点

| 数据 | 端点 | 说明 |
|------|------|------|
| 产品列表 | `POST /v3/product/list` | 分页获取所有商品 ID |
| 产品详情 | `POST /v3/product/info/list` | 批量获取价格/库存/分类（最多100个） |
| 销售分析 | `POST /v1/analytics/data` | **核心**，按 SKU 维度聚合销量/收入/曝光 |
| 财务流水 | `POST /v3/finance/transaction/list` | 按日期范围拉取交易明细 |
| 订单列表 | `POST /v2/posting/fbo/list` + `POST /v3/posting/fbs/list` | FBO/FBS 订单 |

### 4.3 客户端设计

```python
class OzonSellerAPI:
    def __init__(self, client_id: str, api_key: str):
        self.session = httpx.AsyncClient(
            base_url="https://api-seller.ozon.ru",
            headers={"Client-Id": client_id, "Api-Key": api_key}
        )
        self.rate_limiter = RateLimiter(rps=50)

    async def request(self, endpoint: str, payload: dict) -> dict:
        # 限流 → POST 请求 → tenacity 重试(429/5xx)
        ...

    async def get_analytics_data(self, date_from: str, date_to: str):
        # POST /v1/analytics/data
        # dimension: ["sku", "day"]
        # metrics: [ordered_units, revenue, returns, session_view, ...]

    async def get_products(self, limit=1000):
        # POST /v3/product/list (分页)

    async def get_product_info(self, product_ids: list[int]):
        # POST /v3/product/info/list (批量，最多100)

    async def get_finance_transactions(self, date_from: str, date_to: str, page=1):
        # POST /v3/finance/transaction/list (分页)

    async def get_postings(self, date_from: str, date_to: str, fulfillment: str):
        # POST /v2/posting/fbo/list 或 /v3/posting/fbs/list
```

### 4.4 错误处理策略

| 状态码 | 处理方式 |
|--------|----------|
| 429 Too Many Requests | 指数退避重试（解析 Retry-After） |
| 5xx Server Error | 重试最多 5 次 |
| 401/403 | 直接报错（凭证问题） |
| 400 Bad Request | 记录日志，人工排查 |

### 4.5 暂不接入的模块

- **广告数据**：需要 Performance API 独立密钥，后续再说
- **关键词数据**：需要 Premium Pro 订阅或 Performance API

---

## 5. REST API 设计

基础路径：`/api/v1`

### 5.1 看板端点

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/dashboard/summary` | date_from, date_to | KPI 汇总（总收入/订单/SKU数/利润率） |
| GET | `/dashboard/sales-trend` | date_from, date_to | 每日销售趋势（折线图数据） |
| GET | `/dashboard/category-breakdown` | date_from, date_to | 品类分布（饼图数据） |
| GET | `/dashboard/top-products` | date_from, date_to, limit, sort_by | SKU 排名 |
| GET | `/dashboard/finance-breakdown` | date_from, date_to | 费用构成（堆叠图数据） |

### 5.2 SKU 端点

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/skus` | search, category, page, size, sort_by | SKU 列表（搜索+分页） |
| GET | `/skus/{sku_id}` | - | SKU 详情 |
| GET | `/skus/{sku_id}/daily` | date_from, date_to | 单 SKU 日趋势 |
| GET | `/skus/{sku_id}/finance` | date_from, date_to | 单 SKU 财务明细 |

### 5.3 同步端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sync/status` | 各同步类型最近状态 |
| POST | `/sync/trigger` | 触发全量同步 |
| POST | `/sync/trigger/{sync_type}` | 触发指定类型同步 |
| GET | `/sync/logs` | 同步历史记录 |

---

## 6. 前端架构

### 6.1 页面路由

| 路径 | 视图 | 说明 |
|------|------|------|
| `/` | DashboardView | 主看板 |
| `/skus` | SkuListView | SKU 列表 |
| `/skus/:skuId` | SkuDetailView | SKU 详情 |
| `/sync` | SyncSettingsView | 同步管理 |

### 6.2 看板页面布局

```
┌──────────────────────────────────────────────────────────────┐
│  AppHeader: Ozon BI 看板 | 同步状态 | 日期                   │
├──────────┬───────────────────────────────────────────────────┤
│          │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐  │
│  Sidebar │  │ 总收入 │ │ 总订单 │ │动销SKU│ │ 利润率 │ │ 退款率 │  │
│  ─────── │  │ ¥1.2M │ │  856  │ │  124  │ │ 18.5% │ │ 3.2%  │  │
│  📊 看板  │  └──────┘ └──────┘ └──────┘ └──────┘ └────────┘  │
│  📦 SKU  │                                                   │
│  🔄 同步  │  ┌────────────────────┬────────────────────────┐  │
│          │  │  销售趋势折线图      │  品类分布环形图          │  │
│          │  │  (收入柱+订单折线)   │  (前5品类占比)         │  │
│          │  └────────────────────┴────────────────────────┘  │
│          │                                                   │
│          │  ┌────────────────────────────────────────────────┐│
│          │  │  费用构成堆叠面积图 (佣金+物流+仓储)            ││
│          │  └────────────────────────────────────────────────┘│
│          │                                                   │
│          │  ┌────────────────────────────────────────────────┐│
│          │  │  Top SKU 排名表 (排序|搜索|分页)               ││
│          │  │  排名 | SKU | 名称 | 收入 | 销量 | 利润率      ││
│          │  └────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────┘
```

### 6.3 SKU 详情页布局

```
┌──────────────────────────────────────────────────────────────┐
│  [商品图]  SKU 名称                          价格: ¥2,399   │
│           Offer ID: xyz-123                  总销量: 1,256  │
├──────────────────────────────────────────────────────────────┤
│  每日趋势图 (收入/订单/利润 三折线)                          │
├──────────────────────────────────────────────────────────────┤
│  财务明细表                                                  │
│  日期 | 收入 | 佣金 | 物流费 | 仓储费 | 实收 | 利润率       │
└──────────────────────────────────────────────────────────────┘
```

### 6.4 ECharts 图表方案

| 图表 | 类型 | 数据源 | 组件 |
|------|------|--------|------|
| 销售趋势 | 折线+柱状双轴 | `/dashboard/sales-trend` | SalesTrendChart.vue |
| 品类分布 | 环形图 | `/dashboard/category-breakdown` | CategoryPieChart.vue |
| SKU 排名 | el-table | `/dashboard/top-products` | TopProductsTable.vue |
| 费用构成 | 堆叠面积图 | `/dashboard/finance-breakdown` | FinanceBreakdownChart.vue |
| SKU 日趋势 | 多折线 | `/skus/{id}/daily` | SkuDailyChart.vue |

### 6.5 状态管理（Pinia）

```
useDashboardStore
  ├─ state: summary, salesTrend, categoryBreakdown, topProducts, financeBreakdown, dateRange, loading
  └─ actions: fetchSummary(), fetchSalesTrend(), fetchAll()

useSkuStore
  ├─ state: skuList, currentSku, skuDaily, skuFinance, pagination, filters
  └─ actions: fetchSkus(), fetchSkuDetail(), fetchDaily()

useSyncStore
  ├─ state: syncStatus, syncLogs, isRunning
  └─ actions: fetchStatus(), triggerSync()
```

---

## 7. 实施阶段

### 阶段 1：项目初始化 + 数据库模型（1-2 天）

**任务清单：**

1. **后端脚手架**
   - [ ] 创建 `app/` 包及所有子目录
   - [ ] `app/config.py` — pydantic-settings 配置
   - [ ] `app/database.py` — SQLAlchemy engine + session
   - [ ] `app/main.py` — FastAPI 应用 + CORS + 健康检查
   - [ ] `run.py` — uvicorn 启动
   - [ ] `requirements.txt` — 安装所有依赖

2. **数据库模型**
   - [ ] `app/models/base.py` — 声明式基类（schema='ozon'）
   - [ ] `app/models/product.py` — products 表
   - [ ] `app/models/daily_summary.py` — sku_daily_summary 表
   - [ ] `app/models/finance.py` — finance_transactions 表
   - [ ] `app/models/sync_log.py` — sync_log 表
   - [ ] 运行 `Base.metadata.create_all()` 建表

3. **前端初始化**
   - [ ] `npm create vite@latest frontend -- --template vue`
   - [ ] 安装依赖：element-plus, echarts, axios, pinia, vue-router, dayjs
   - [ ] 配置 `vite.config.js`（代理到 :8000）
   - [ ] Element Plus 全局注册
   - [ ] Vue Router 配置（4 个空视图）
   - [ ] Pinia 空 store 定义
   - [ ] 布局组件（AppHeader + AppSidebar）
   - [ ] 基础样式（variables.css + global.css）

**验证：**
- `python run.py` 启动 → `GET /health` → `{"status": "ok"}`
- 数据库 4 张表创建成功
- `npm run dev` → 侧边栏+空内容区布局

### 阶段 2：Ozon API 客户端 + 数据同步（3-4 天）

**任务清单：**

1. **Ozon API 客户端**
   - [ ] `app/clients/__init__.py`
   - [ ] `app/clients/ozon.py` — 认证 + 限流 + 重试 + 各端点方法
   - [ ] 测试各 API 方法（小批量数据验证）

2. **数据同步服务**
   - [ ] `app/services/product_sync.py` — 产品同步
   - [ ] `app/services/analytics_sync.py` — 销售分析同步
   - [ ] `app/services/finance_sync.py` — 财务流水同步
   - [ ] `app/services/summary_service.py` — 汇总表构建
   - [ ] `app/services/sync_service.py` — 同步编排

3. **定时任务**
   - [ ] `app/scheduler.py` — APScheduler 配置
   - [ ] 启动时首次全量同步
   - [ ] 每日定时同步

**验证：**
- 手动触发全量同步 → 数据库有数据
- `ozon.sync_log` 记录每次同步结果
- `ozon.sku_daily_summary` 有聚合数据

### 阶段 3：REST API（2 天）

**任务清单：**

1. **Pydantic schemas**
   - [ ] `app/schemas/dashboard.py`
   - [ ] `app/schemas/product.py`
   - [ ] `app/schemas/sync.py`

2. **API 路由**
   - [ ] `app/api/v1/dashboard.py`
   - [ ] `app/api/v1/sku.py`
   - [ ] `app/api/v1/sync.py`
   - [ ] `app/api/router.py` — 汇总注册

3. **测试**
   - [ ] Swagger UI (`/docs`) 测试所有端点
   - [ ] curl 验证响应速度和数据准确性

**验证：**
- `GET /api/v1/dashboard/summary` 返回正确的汇总数据
- `GET /api/v1/dashboard/sales-trend?date_from=2026-06-01&date_to=2026-07-13` 返回时间序列
- 所有端点响应 < 500ms

### 阶段 4：前端看板开发（3-4 天）

**任务清单：**

1. **基础设施**
   - [ ] `src/api/client.js` — Axios 实例 + 拦截器
   - [ ] `src/api/dashboard.js`, `sku.js`, `sync.js`
   - [ ] `src/stores/dashboard.js`, `sku.js`, `sync.js`
   - [ ] `src/utils/formatters.js`, `date.js`

2. **通用组件**
   - [ ] `DateRangePicker.vue` — 日期范围 + 快捷选项
   - [ ] `LoadingSpinner.vue` — 加载态
   - [ ] `EmptyState.vue` — 空数据
   - [ ] `ErrorAlert.vue` — 错误提示

3. **KPI 卡片**
   - [ ] `KpiCard.vue` — 图标 + 数值 + 趋势箭头
   - [ ] `KpiRow.vue` — 卡片行布局

4. **图表组件**
   - [ ] `SalesTrendChart.vue` — 折线+柱状双轴
   - [ ] `CategoryPieChart.vue` — 环形图
   - [ ] `FinanceBreakdownChart.vue` — 堆叠面积图
   - [ ] `SkuDailyChart.vue` — 多折线图

5. **页面**
   - [ ] `DashboardView.vue` — 主看板（KPI + 4 图表 + 排名表）
   - [ ] `SkuListView.vue` — SKU 搜索列表
   - [ ] `SkuDetailView.vue` — SKU 详情 + 趋势 + 财务
   - [ ] `SyncSettingsView.vue` — 同步状态 + 手动触发

**验证：**
- 看板页面加载完整，所有图表渲染
- 日期范围切换 → 数据刷新
- 搜索 SKU → 结果正确
- 点击 SKU → 详情页展示完整

### 阶段 5：定时调度 + 部署准备（1-2 天）

**任务清单：**

1. **调度完善**
   - [ ] APScheduler 每日 3:00 AM 定时
   - [ ] 启动检测（空数据时自动全量同步）
   - [ ] loguru 日志配置（按日轮转）

2. **性能优化**
   - [ ] SQLAlchemy 连接池配置
   - [ ] 前端代码分割 + 懒加载

3. **部署文档**
   - [ ] `docker-compose.yml`
   - [ ] 环境变量清单
   - [ ] Windows 启动脚本

---

## 8. 部署方案

### 本地开发

```bash
# 终端 1：后端
cd OzonSku
source venv/Scripts/activate
pip install -r requirements.txt
python run.py                # http://localhost:8000

# 终端 2：前端
cd OzonSku/frontend
npm install
npm run dev                  # http://localhost:5173
```

### 生产部署（Docker）

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db]

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [api]

  db:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]
```

---

## 附录

### 关键文件速查

| 文件 | 职责 | 优先级 |
|------|------|--------|
| `app/main.py` | FastAPI 应用入口 | ⭐⭐⭐ |
| `app/config.py` | 配置中心（DB/Ozon/调度） | ⭐⭐⭐ |
| `app/models/daily_summary.py` | 核心表模型 | ⭐⭐⭐ |
| `app/clients/ozon.py` | Ozon API 客户端 | ⭐⭐⭐ |
| `app/services/sync_service.py` | 同步编排 | ⭐⭐⭐ |
| `frontend/src/views/DashboardView.vue` | 看板主页面 | ⭐⭐⭐ |
| `frontend/src/components/dashboard/SalesTrendChart.vue` | 核心图表 | ⭐⭐ |
| `frontend/src/stores/dashboard.js` | 看板状态 | ⭐⭐ |

### 依赖清单

**Python (requirements.txt)：**
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic-settings==2.5.2
sqlalchemy==2.0.36
psycopg2-binary==2.9.12
httpx==0.27.2
tenacity==9.0.0
apscheduler==3.10.4
python-dotenv==1.0.1
python-dateutil==2.9.0
pytz==2024.2
loguru==0.7.3
```

**前端 (package.json)：**
```json
{
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "pinia": "^2.2.0",
    "echarts": "^5.6.0",
    "axios": "^1.7.0",
    "dayjs": "^1.11.0",
    "element-plus": "^2.8.0"
  }
}
```

---

> 计划版本：v1.0 | 最后更新：2026-07-13
> 欢迎提出修改意见，确认后按阶段开始实现

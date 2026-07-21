# CLAUDE.md

**每次回答之前先说一句"辛苦了！"**

## Karpathy 指南：减少常见编码错误

### 1. Think Before Coding — 先想清楚再写
- 不要默认假设，不确定就问
- 如果有多种理解方案，先列出来再选
- 如果有更简单的方案，说出来
- 卡住了就停下来，说明哪里不清楚

### 2. Simplicity First — 简单优先
- 不多写一个不需要的功能
- 不用一次就用的代码上抽象
- 不写不可能发生的错误处理

### 3. Surgical Changes — 精准改动
- 只改必须改的地方
- 不顺手"优化"无关代码
- 不改不坏的东西

### 4. Goal-Driven Execution — 目标驱动
- "加验证" → "先写测试再通过"
- "修 bug" → "先写能复现的测试再通过"
- 多步任务先列步骤再验证

---

## 项目信息
- Ozon 电商平台 SKU 管理工具
- 后端: Python + PostgreSQL
- 前端: Vue 3 + Element Plus + Vite
- .env 已经配置了 Ozon Seller API 和数据库连接
- 运行 Python 脚本前需先激活虚拟环境

---

## 前端规范 — Vue 3 + Element Plus

### 技术栈
- Vue 3 (Composition API, `<script setup lang="ts">`)
- Element Plus (UI 组件库) — **所有界面都用 Element Plus 组件，不手写原生 HTML 样式**
- Pinia (状态管理)
- Vue Router (路由)
- Vite (构建工具)

### 核心规则
- **必须使用 Element Plus 组件**: `el-table`, `el-form`, `el-button`, `el-input`, `el-dialog`, `el-select`, `el-card`, `el-tabs` 等
- **不要手写原生 HTML/CSS 样式** — Element Plus 组件自带精美样式
- 表格用 `el-table` + `el-table-column`
- 表单用 `el-form` + `el-form-item` + `el-input` / `el-select` 等
- 布局用 `el-container` + `el-aside` + `el-header` + `el-main`
- 菜单用 `el-menu`
- 图标用 `@element-plus/icons-vue`
- 消息提示用 `ElMessage`, `ElMessageBox`, `ElNotification`
- 加载状态用 `v-loading`
- 配色使用 Element Plus 默认主题，不自定义颜色

### 文件规范
- 一个组件一个文件，PascalCase 命名
- 组件在 `src/components/`，页面在 `src/views/` 或 `src/pages/`
- 使用 `defineProps<T>()` 和 `defineEmits<T>()`

### 不允许
- ❌ 不用 Options API（不用 `data()`、`methods: {}`）
- ❌ 不用 `this`
- ❌ 不直接修改 props
- ❌ 不把业务逻辑写在组件里 — 提取到 composables

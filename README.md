# AI Test Platform

这是一个能够从零到一将产品需求转化为测试用例的 AI 测试管理后台系统。平台分为前端展现页面和后端处理 API。 

## 特性

- **现代前端界面**: 基于 Vue 3, TailwindCSS 和 Element Plus。
- **数据看板**: 登录后默认进入后台数据统计仪表盘。
- **智能用例生成框架**: 支持通过飞书文档、钉钉文档以及本地上传解析需求，并能够对接 AI 进行测试设计、测试用例生成，及思维导图（Mindmap）转化。

---

## 技术栈

### 后端

- Python 3
- FastAPI（构建 REST API）
- Uvicorn（ASGI 服务启动与热重载）
- CORSMiddleware（处理跨域）
- Typer（命令行入口）
- 数据访问：SQLAlchemy（Async ORM）+ Repository（仓储）层
- 数据库与驱动：SQLite + aiosqlite（异步）
- 后端项目思想：分层/模块化组织
           - API 层在 `app/api/endpoints`，
           - 业务逻辑在 `app/services`
           - 数据操作在 `app/repositories`，
           - 领域/规则在 `app/modules/domain`，
           - 并用 `app/core` 统一数据库、日志、中间件等基础能力
         整体风格接近“分层架构 + 仓储/领域驱动”的组织方式）

### 前端

- Vue 3 + TypeScript（页面与状态管理）
- Vite（开发构建与热更新）
- TailwindCSS（样式）
- Element Plus（组件库）
- axios（HTTP 请求）
- vue-router（路由）
- simple-mind-map（思维导图）

---

## 快速安装与启动指南

### 1. 后端服务 (Backend - FastAPI)

后端系统采用 Python 3，并利用 FastAPI 构建高性能 API。

#### 环境准备

请确保您的系统中已安装 Python 3.13或以上版本。

#### 安装依赖

1. 进入后端目录：
  ```bash
   cd backend
  ```
2. 创建并激活虚拟环境（推荐）：
  ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # MacOS/Linux
   # 或者是 Windows系统: .venv\Scripts\activate
  ```
3. 安装依赖：
  ```bash
   pip install -r requirements.txt
  ```
4. 复制配置文件：
  ```bash
   cp .env.example .env
  ```

#### 启动服务

在 `backend` 目录下激活了虚拟环境后，执行以下命令：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

后端服务将在 `http://127.0.0.1:8001` 启动，接口文档可通过 `http://127.0.0.1:8001/docs` 访问。

---

### 2. 前端服务 (Frontend - Vue3)

前端利用 Vite 提供极速的构建和热更新体验。

#### 环境准备

请确保您的系统中已安装 Node.js (推荐 v22+)。

#### 安装依赖

1. 进入前端目录：
  ```bash
   cd frontend/
  ```
2. 安装 NPM 依赖：
  ```bash
   npm install
   # 如果在安装 tailwindcss 等核心包时遇到依赖冲突，可以执行:
   # npm install --legacy-peer-deps

   # npm 如果安装失败，采用cnpm install 可以
    npm install -g cnpm 
    cnpm install 
  ```

#### 启动服务

在安装完依赖后，执行以下命令启动开发服务器：

```bash
cp .env.example .env
npm run dev
```

前端服务默认将在 `http://localhost:5173/` 启动。

---

## 默认测试账号

系统已内置一套默认管理员账号：

- **账号**: `admin`
- **密码**: `123456`


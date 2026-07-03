# JiuWei CRM

面向成人AI职业教育机构的轻量级招生CRM系统。

## 项目简介

JiuWei CRM 是一款专为成人AI职业教育机构设计的轻量级客户关系管理系统（CRM）。系统支持潜在学员（Lead）信息管理、跟进记录（FollowUp）、简历解析与导入（Resume Import）、数据看板（Dashboard）、用户权限管理等功能，帮助招生团队高效管理招生线索全生命周期。

## 目录结构

```
JiuWei-CRM/
├── frontend/                # Next.js 前端应用
│   ├── app/                 # App Router 页面
│   │   ├── login/           # 登录页
│   │   ├── dashboard/       # 数据看板
│   │   ├── leads/           # 线索管理（列表/详情/新建）
│   │   └── settings/        # 设置（修改密码/用户管理）
│   ├── components/          # 可复用组件
│   ├── lib/                 # 工具函数（API 封装）
│   ├── types/               # TypeScript 类型定义
│   ├── public/              # 静态资源
│   └── Dockerfile           # 前端 Docker 构建文件
├── backend/                 # FastAPI 后端应用
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── database.py      # 数据库配置
│   │   ├── models/          # 数据模型（ORM）
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API 路由
│   │   ├── services/        # 业务逻辑
│   │   ├── core/            # 核心配置（安全/认证/配置）
│   │   └── utils/           # 工具函数
│   ├── data/                # SQLite 数据库文件
│   ├── uploads/             # 文件上传目录
│   ├── requirements.txt     # Python 依赖
│   └── Dockerfile           # 后端 Docker 构建文件
├── docs/                    # 项目文档
│   ├── 01-PRD/              # 产品需求文档
│   ├── 02-Prototype/        # 原型设计
│   ├── 03-Database/         # 数据库设计
│   ├── 04-API/              # API 设计
│   ├── 05-Development/      # 开发计划
│   ├── 06-Test/             # 测试文档
│   ├── 07-Deployment/       # 部署文档
│   ├── 08-Release/          # 发布说明
│   └── 09-Backlog/          # 需求积压
├── reports/                 # 开发报告
├── logo/                    # Logo 资源
├── docker-compose.yml       # Docker Compose 编排
└── README.md                # 项目说明
```

## 运行环境

| 层级 | 技术 |
|------|------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| Backend | Python 3.13, FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite（v0.1），后续迁移至 PostgreSQL |
| Infrastructure | Docker, Docker Compose |

## Docker 启动

### 前置要求

- [Docker](https://docs.docker.com/get-docker/) 已安装
- [Docker Compose](https://docs.docker.com/compose/install/) 已安装

### 启动服务

```bash
# 克隆项目
git clone <repo-url>
cd JiuWei-CRM

# 启动所有服务（首次需构建）
docker compose up --build

# 后台启动
docker compose up --build -d

# 停止服务
docker compose down
```

### 启动顺序

1. Backend（FastAPI）先启动
2. Frontend（Next.js）依赖 Backend，后启动

## ECS 部署环境变量

在 ECS 等远程环境部署时，需要将 `NEXT_PUBLIC_API_BASE_URL` 设置为后端 API 的公网地址：

```bash
# 方式 1：通过 shell 环境变量传入
NEXT_PUBLIC_API_BASE_URL=http://39.105.33.49:8100 docker compose build --no-cache frontend

# 方式 2：创建根目录 .env 文件
echo 'NEXT_PUBLIC_API_BASE_URL=http://39.105.33.49:8100' > .env

# 然后构建并启动
docker compose up --build -d
```

> ⚠️ **重要说明：**
> - `NEXT_PUBLIC_API_BASE_URL` 需要在 frontend **构建阶段**注入，修改该值后必须重新 `docker compose build --no-cache frontend`。
> - 仅 `docker compose restart frontend` 不会生效。
> - 变量名中的 `NEXT_PUBLIC_` 前缀是 Next.js 的约定，只有此前缀的变量才会暴露给浏览器端代码。
> - 本地开发默认使用 `http://localhost:8000`，无需额外配置。

## 服务访问地址

| 服务 | 地址 |
|------|------|
| **前端** | http://localhost:3000 |
| **后端 API** | http://localhost:8000 |
| **Swagger 文档** | http://localhost:8000/docs |
| **健康检查** | http://localhost:8000/api/v1/health |

## Production Initialization

Before deploying v0.1.0 to production for the first time, run the production initialization script to clean up test data, reset the admin password, and verify your security configuration.

```bash
# 1. Reset production data (set a strong admin password)
ADMIN_INITIAL_PASSWORD='YourStrongPassword123!' python scripts/reset_prod_data.py

# 2. Set a strong JWT_SECRET_KEY in backend/.env (at least 32 random characters)

# 3. Run security configuration check
python scripts/check_security.py
```

> ⚠️ Never commit `backend/.env` to Git. Use `.env.example` as the template.
>
> See [docs/07-Deployment/Production-Init-v0.1.md](docs/07-Deployment/Production-Init-v0.1.md) for full details.

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |

> 首次启动时系统自动创建默认管理员账号。登录后可在「设置 → 用户管理」中创建更多用户。

## 本地开发

### 前端

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
# 访问 http://localhost:3000
```

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs
```

## 主要功能

### v0.1.0

| 模块 | 功能 |
|------|------|
| **Auth** | 用户登录、JWT 认证、三角色权限模型（admin/manager/counselor） |
| **Dashboard** | 全部线索统计、今日新增、待跟进、已报名统计、今日待跟进、最近新增线索 |
| **Lead** | 新建/编辑/删除（软删除）线索、搜索、来源筛选、状态筛选、转已报名 |
| **FollowUp** | 新增/查看/删除跟进记录、时间轴展示 |
| **Resume Import** | Word/PDF 上传、文本解析、手机号/邮箱规则提取、AI 增强解析（可选）、LeadDraft 生成 |
| **LeadDraft** | 查看/修改/确认/丢弃简历解析草稿 |
| **Config** | 线索来源管理、意向课程管理、系统配置 |
| **User Management** | 用户创建/编辑/删除、角色分配、修改密码 |

## 开发状态

**Current Version：v0.1.1**

- [x] Auth 模块
- [x] Lead 管理
- [x] Lead 搜索与筛选
- [x] FollowUp 跟进
- [x] Resume Import 简历导入
- [x] LeadDraft 草稿管理
- [x] Dashboard 数据看板
- [x] Config 系统配置
- [x] Frontend 前端页面
- [x] Lead → Enrolled 转已报名
- [x] User Management 用户管理
- [x] Docker Compose 部署
- [x] ECS 生产部署验证

## Release History

### v0.1.1 (2026-07-03)

- **Deployment Compatibility** — Frontend Docker Build 支持 `NEXT_PUBLIC_API_BASE_URL` build args
- **Docker Build Improvement** — 移除 `libmupdf-dev` 系统依赖，采用 PyMuPDF wheel
- **Frontend Build Args** — `docker-compose.yml` 支持 `NEXT_PUBLIC_API_BASE_URL` 环境变量覆盖
- **ECS Deployment Verified** — 阿里云 ECS 生产环境部署验证通过
- **README** — 补充 ECS 部署说明

> 详见 [reports/deployment-ecs-v0.1.1.md](reports/deployment-ecs-v0.1.1.md)

### v0.1.0 (2026-07-02)

- 首个功能完整版本
- Auth / Lead / FollowUp / Resume Import / Dashboard / Config / User Management
- Docker Compose 部署支持

> 详见 [reports/release-v0.1.0.md](reports/release-v0.1.0.md)

## License

MIT

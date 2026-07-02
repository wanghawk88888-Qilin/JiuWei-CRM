# JiuWei CRM 部署文档

**版本：** v0.1 MVP
**状态：** Final
**更新时间：** 2026-07-02

---

# 1. 部署目标

JiuWei CRM v0.1 采用统一部署模式。

前端、后端统一部署至阿里云 ECS。

数据库使用 SQLite。

整个系统通过 Docker Compose 进行统一管理。

部署目标：

```text
GitHub
    ↓
git pull
    ↓
Docker Compose
    ↓
Container
    ↓
公网 IP 访问
```

本版本不使用 Vercel。

---

# 2. 部署架构

部署架构如下：

```text
阿里云 ECS
│
├── frontend（Next.js）
│
├── backend（FastAPI）
│
├── SQLite
│
└── uploads
```

统一由 Docker Compose 编排。

---

# 3. 最终目录结构

项目最终目录建议如下：

```text
JiuWei-CRM/
│
├── frontend/
│   ├── Dockerfile
│   ├── .env.example
│   └── ...
│
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── data/
│   │    └── jiuwei_crm.db
│   ├── uploads/
│   │    ├── temp/
│   │    └── parsed/
│   └── ...
│
├── docker/
│
├── docker-compose.yml
│
└── docs/
```

---

# 4. Docker Compose 要求

v0.1 必须提供：

```text
docker-compose.yml
```

负责统一启动：

* frontend
* backend

SQLite 使用 Volume 持久化。

uploads 使用 Volume 持久化。

容器重启不得丢失数据。

---

# 5. Dockerfile 要求

必须提供：

```text
frontend/Dockerfile

backend/Dockerfile
```

要求：

能够独立构建。

不得依赖本地开发环境。

---

# 6. 环境变量

## backend

提供：

```text
backend/.env.example
```

至少包含：

```text
DATABASE_URL

JWT_SECRET_KEY

UPLOAD_DIR

TEMP_FILE_RETENTION_DAYS

CORS_ORIGINS
```

---

## frontend

提供：

```text
frontend/.env.example
```

至少包含：

```text
NEXT_PUBLIC_API_BASE_URL
```

---

# 7. SQLite

数据库：

```text
backend/data/jiuwei_crm.db
```

要求：

Docker Volume 挂载。

容器删除后：

数据库仍保留。

---

# 8. 上传目录

上传目录：

```text
backend/uploads/temp/
```

解析完成后：

按照系统配置：

* 立即删除
* 保留 1 天
* 保留 3 天
* 保留 7 天
* 保留 15 天

后台自动清理。

---

# 9. 本地开发

开发环境：

```text
git clone

↓

docker compose up
```

即可启动。

不得依赖：

手工安装 Python。

手工安装 Node。

---

# 10. ECS 部署

部署流程：

```text
git pull

↓

docker compose build

↓

docker compose up -d
```

升级：

```text
git pull

↓

docker compose up -d --build
```

整个升级过程不得修改数据库。

---

# 11. 网络要求

默认开放：

```text
80

8000
```

v0.1 暂不配置：

HTTPS

域名

Nginx

后续版本再增加。

---

# 12. 数据安全

要求：

SQLite：

必须持久化。

Uploads：

必须持久化。

日志：

保留。

原始简历：

按照保留策略自动删除。

---

# 13. 发布流程

标准流程：

```text
本地开发

↓

本地测试

↓

Git Commit

↓

Push GitHub

↓

ECS

git pull

↓

docker compose up -d --build

↓

浏览器访问公网IP

↓

完成发布
```

---

# 14. v0.1 不部署内容

本版本不包含：

* Kubernetes
* Redis
* PostgreSQL
* RabbitMQ
* MinIO
* Nginx
* HTTPS
* 域名
* CI/CD 自动部署
* Vercel

上述能力统一放入后续版本。

---

# 15. 小克开发要求（必须执行）

在开发过程中，请提前准备并保证以下文件存在：

```text
docker-compose.yml

frontend/Dockerfile

backend/Dockerfile

frontend/.env.example

backend/.env.example
```

所有路径均采用相对路径。

不得写死：

* 数据库路径
* 上传目录
* API 地址

全部通过环境变量读取。

---

# 16. 验收标准

Deployment-v0.1 满足以下条件即通过：

* Docker Compose 可正常启动。
* Frontend 容器正常运行。
* Backend 容器正常运行。
* SQLite 数据持久化。
* Uploads 持久化。
* git pull 后可重新部署。
* docker compose up -d --build 可完成升级。
* 浏览器通过 ECS 公网 IP 正常访问系统。
* 满足 PRD、Prototype、Database、API、Development、Test 文档要求。

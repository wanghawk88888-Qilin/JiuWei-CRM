# Engineering Roadmap

**项目：** JiuWei CRM

**当前版本：** v0.1.1

**目标版本：** v0.2

**更新日期：** 2026-07-03

---

## 概述

本文档记录 JiuWei CRM 从 v0.1 到 v0.2 的工程化升级计划。v0.2 的重点是**部署规范化、运维标准化、基础设施升级**，不涉及业务功能开发。

---

## v0.2 工程升级项

### 1. `docker-compose.prod.yml` — 生产环境配置拆分

**背景：**

当前仅有一个 `docker-compose.yml`，线上部署时需要直接修改该文件（端口映射、环境变量等），导致 `git pull` 时产生合并冲突。

**方案：**

- `docker-compose.yml`：基础服务定义，受版本控制，保持通用性
- `docker-compose.prod.yml`：生产环境覆盖配置（端口、密钥、资源限制等），不纳入版本控制

**参考文件：** [reports/deployment-ecs-v0.1.1.md](../reports/deployment-ecs-v0.1.1.md) 问题 ④

**优先级：** 高

---

### 2. `docker-compose.test.yml` — 测试环境配置

**背景：**

当前缺少独立的测试环境编排文件，测试与开发共用同一套 Docker Compose 配置。

**方案：**

- 创建 `docker-compose.test.yml`，用于 CI/CD 或本地测试
- 使用独立端口、独立数据卷，避免与开发/生产环境冲突

**优先级：** 中

---

### 3. 容器内运维脚本 — 统一运维入口

**背景：**

`reset_prod_data.py` 等运维脚本在宿主机运行时存在 Python 依赖缺失问题（如 `passlib[bcrypt]`），当前临时方案为手动进入容器执行。

**方案：**

- 创建统一的容器内运维脚本入口（如 `scripts/ops.sh` 或 Makefile）
- 封装常用运维操作：数据重置、备份、健康检查、日志查看
- 消除宿主机环境依赖，所有运维操作均在容器内完成

**参考文件：** [reports/deployment-ecs-v0.1.1.md](../reports/deployment-ecs-v0.1.1.md) 问题 ③

**优先级：** 中

---

### 4. CI/CD — 持续集成与部署

**背景：**

当前无 CI/CD Pipeline，构建、测试、部署均为手动操作。

**方案：**

- 接入 GitHub Actions 或类似 CI 服务
- Pipeline 阶段：
  - Lint & Type Check（前端 + 后端）
  - Unit Test
  - Docker Build
  - Deploy to ECS（手动触发或 Tag 触发）

**优先级：** 中

---

### 5. HTTPS — 全站加密

**背景：**

当前服务仅支持 HTTP，公网访问存在安全风险。

**方案：**

- 配置 SSL/TLS 证书（推荐 Let's Encrypt + acme.sh 自动续期）
- 通过 Nginx 或 Caddy 反向代理终止 TLS

**优先级：** 高

---

### 6. Nginx Reverse Proxy — 反向代理

**背景：**

当前 Frontend（3100）和 Backend（8100）端口直接暴露，缺少统一入口。

**方案：**

- Nginx 作为反向代理，统一入口（80/443）
- 路由规则：
  - `/` → Frontend (3100)
  - `/api/` → Backend (8100)
- 支持 HTTPS 终止、静态资源缓存、请求限流

**优先级：** 高

---

### 7. 统一部署规范 — 文档与流程标准化

**背景：**

当前部署流程依赖人工记忆和临场判断，缺少标准化文档。

**方案：**

- 编写 `docs/07-Deployment/Deployment-Guide.md`：完整部署流程
- 编写 `docs/07-Deployment/Environment-Setup.md`：新环境初始化步骤
- 编写 `docs/07-Deployment/Rollback-Procedure.md`：回滚流程
- 编写 `docs/07-Deployment/Backup-Strategy.md`：备份策略

**优先级：** 中

---

### 8. Deployment Validation Checklist — 部署验证清单

**背景：**

当前上线验证依赖临时检查，缺少标准化的验证清单。

**方案：**

- 创建 `docs/07-Deployment/Deployment-Checklist.md`
- 标准化验证项：Health Check、登录、CRUD、权限、数据一致性
- 每次上线前/后对照清单逐项验证并记录

**优先级：** 中

---

## 版本规划

| 版本 | 主题 | 主要内容 |
|------|------|----------|
| **v0.1.0** | MVP | 核心业务功能 + Docker Compose |
| **v0.1.1** | Deployment Compatibility | ECS 部署兼容性修复 |
| **v0.2** | Engineering Upgrade | 部署规范化、HTTPS、CI/CD、Nginx |
| **v0.3** | Feature Enhancement | 待规划 |
| **v1.0** | Production Ready | PostgreSQL 迁移、高可用、监控告警 |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-03 | v0.2-draft | 初始版本，规划 8 项工程升级 |

# Deployment Record — v0.1.1

**版本：** v0.1.1

**发布日期：** 2026-07-03

**部署环境：** 阿里云 ECS（生产环境）

**部署方式：** Docker Compose

---

## 一、部署环境

| 项目 | 详情 |
|------|------|
| **云平台** | 阿里云 ECS |
| **项目路径** | `/opt/jiuwei-crm` |
| **部署方式** | Docker Compose |
| **Frontend 端口** | 3100 |
| **Backend 端口** | 8100 |
| **数据库** | SQLite |
| **Backend Health** | `GET /api/v1/health` |

---

## 二、部署步骤

### 2.1 代码部署

```bash
cd /opt/jiuwei-crm
git pull origin main
```

### 2.2 构建与启动

```bash
# 设置前端 API 地址环境变量
export NEXT_PUBLIC_API_BASE_URL=http://<ECS_PUBLIC_IP>:8100

# 构建并启动所有服务
docker compose up --build -d
```

### 2.3 生产初始化

```bash
# 容器内执行 reset_prod_data.py
docker compose exec backend python scripts/reset_prod_data.py
```

### 2.4 验证清单

| 验证项 | 结果 |
|--------|------|
| Backend Health (`GET /api/v1/health`) | ✅ 正常 |
| Admin 登录 | ✅ 通过 |
| Dashboard 访问 | ✅ 通过 |
| Lead 新增 | ✅ 通过 |
| User Management | ✅ 通过 |
| 生产初始化 | ✅ 成功 |

---

## 三、部署过程中遇到的问题

### 问题 ①：Backend Docker Build — `libmupdf-dev` 导致构建缓慢

**现象：**

Backend Docker build 过程中，`apt install libmupdf-dev` 耗时极长，严重影响构建效率。

**原因：**

系统镜像源拉取 `libmupdf-dev` 及其依赖链速度缓慢。

**解决方案：**

从 `Dockerfile` 中移除 `libmupdf-dev` 系统依赖，改用 PyMuPDF 的预编译 wheel 包，不再依赖系统级 MuPDF 库。

**状态：** ✅ 已修复

---

### 问题 ②：Frontend API 地址仍指向 localhost

**现象：**

Frontend 首次上线后，浏览器端发起的 API 请求仍然指向 `http://localhost:8000`，导致公网用户无法正常访问后端服务。

**原因：**

`NEXT_PUBLIC_API_BASE_URL` 环境变量未在 Docker build **构建阶段**注入。Next.js 的 `NEXT_PUBLIC_*` 变量是在构建时（build time）内联到 JavaScript bundle 中的，运行时修改无效。

**解决方案：**

通过 Docker Build Args 在构建阶段注入环境变量：

```bash
NEXT_PUBLIC_API_BASE_URL=http://39.105.33.49:8100 docker compose build --no-cache frontend
```

同时在 `docker-compose.yml` 中配置 `args` 支持该变量传递。

**状态：** ✅ 已修复

---

### 问题 ③：`reset_prod_data.py` 宿主机运行依赖缺失

**现象：**

在宿主机上直接运行 `reset_prod_data.py` 时报错，缺少 `passlib[bcrypt]` 依赖。

**原因：**

宿主机未安装 Python 虚拟环境中所需的完整依赖。

**解决方案：**

改为在容器内执行脚本：

```bash
docker compose exec backend python scripts/reset_prod_data.py
```

**后续计划：**

容器内运维脚本需要进一步优化，统一运维入口，降低宿主机环境依赖。详见 [[roadmap-engineering]]。

**状态：** ✅ 临时解决，后续持续优化

---

### 问题 ④：`docker-compose.yml` 线上修改导致 Git 冲突

**现象：**

在 ECS 上直接修改 `docker-compose.yml`（如端口映射、环境变量）后，`git pull` 时产生合并冲突。

**原因：**

`docker-compose.yml` 同时在本地仓库和线上被修改，Git 无法自动合并。

**解决方案（当前）：**

手动解决冲突后提交。

**长期方案（已规划）：**

采用 `docker-compose.yml`（基础编排）+ `docker-compose.prod.yml`（生产覆盖）方案：

- `docker-compose.yml`：受版本控制，定义通用服务结构
- `docker-compose.prod.yml`：仅包含生产环境差异（端口、密钥、资源限制），不受版本控制

详见 [[roadmap-engineering]]。

**状态：** ⚠️ 已规划，v0.2 实施

---

## 四、解决方案汇总

| # | 问题 | 解决方案 | 版本 |
|---|------|----------|------|
| 1 | `libmupdf-dev` 构建缓慢 | 移除系统依赖，使用 PyMuPDF wheel | v0.1.1 |
| 2 | Frontend API 地址错误 | Docker Build Args 注入 `NEXT_PUBLIC_API_BASE_URL` | v0.1.1 |
| 3 | `reset_prod_data.py` 宿主机依赖缺失 | 容器内执行 | v0.1.1 |
| 4 | `docker-compose.yml` Git 冲突 | `docker-compose.prod.yml` 拆分方案 | v0.2 计划 |

---

## 五、最终验证结果

### 5.1 Backend

| 验证项 | 结果 |
|--------|------|
| Health Check | ✅ OK |

### 5.2 Frontend

| 验证项 | 结果 |
|--------|------|
| Login | ✅ OK |
| Dashboard | ✅ OK |
| Lead CRUD | ✅ OK |
| FollowUp | ✅ OK |
| User Management | ✅ OK |

### 5.3 运维

| 验证项 | 结果 |
|--------|------|
| Production Reset | ✅ OK |

### 5.4 Security

| 验证项 | 结果 |
|--------|------|
| 核心安全项 | ✅ 通过 |

---

## 六、上线后的系统状态

| 项目 | 状态 |
|------|------|
| **运行环境** | 阿里云 ECS，Docker Compose 正常运行 |
| **数据状态** | 已清空测试数据，仅保留 `admin` 用户 |
| **Admin 账号** | 已重置为生产密码 |
| **Frontend** | 端口 3100，API 正确指向公网后端 |
| **Backend** | 端口 8100，健康检查正常 |

---

## 七、后续改进计划

| # | 改进项 | 优先级 | 目标版本 |
|---|--------|--------|----------|
| 1 | `docker-compose.prod.yml` 拆分 | 高 | v0.2 |
| 2 | `docker-compose.test.yml` 测试环境 | 中 | v0.2 |
| 3 | 容器内运维脚本统一入口 | 中 | v0.2 |
| 4 | CI/CD Pipeline | 中 | v0.2 |
| 5 | HTTPS 支持 | 高 | v0.2 |
| 6 | Nginx Reverse Proxy | 高 | v0.2 |
| 7 | 统一部署规范文档 | 中 | v0.2 |
| 8 | Deployment Validation Checklist | 中 | v0.2 |

> 详见 [docs/roadmap-engineering.md](../docs/roadmap-engineering.md)

---

## 八、本次部署总结

v0.1.1 作为 **Deployment Compatibility 修复版本**，成功解决了首次 ECS 生产部署中遇到的 4 个关键问题：

1. **构建效率**：移除 `libmupdf-dev` 系统依赖，大幅缩短 Backend Docker build 时间
2. **前端连通性**：通过 Docker Build Args 正确注入 `NEXT_PUBLIC_API_BASE_URL`，前端 API 请求正确指向公网后端
3. **运维规范**：确立容器内执行运维脚本的实践，避免宿主机环境依赖
4. **配置管理**：识别 `docker-compose.yml` 线上修改的冲突风险，规划 `docker-compose.prod.yml` 拆分方案

所有功能模块验证通过，系统已在阿里云 ECS 上稳定运行。

# JiuWei CRM Release Report — v0.1.0

**发布日期：** 2026-07-02
**版本状态：** Ready for Release

---

## 一、完成内容

### 功能模块

| 模块 | 功能点 | 状态 |
|------|--------|------|
| **Auth** | 用户登录、JWT 认证、三角色权限（admin/manager/counselor） | ✅ |
| **Dashboard** | 全部线索/今日新增/待跟进/已报名统计、今日待跟进、最近新增 | ✅ |
| **Lead** | 新建/编辑/删除（软删除）、搜索、来源/状态筛选、转已报名 | ✅ |
| **FollowUp** | 新增/查看/删除跟进、时间轴展示 | ✅ |
| **Resume Import** | Word/PDF 上传解析、手机号/邮箱提取、LeadDraft 生成 | ✅ |
| **LeadDraft** | 查看/修改/确认/丢弃 | ✅ |
| **Config** | 线索来源管理、意向课程管理、系统配置 | ✅ |
| **Frontend** | 所有页面（Login/Dashboard/Leads/Settings） | ✅ |
| **User Management** | 用户列表/创建/编辑/删除/角色分配、修改密码 | ✅ |

### 技术栈

- **Frontend:** Next.js 15 + React 19 + TypeScript + Tailwind CSS v4
- **Backend:** Python 3.13 + FastAPI + SQLAlchemy + Pydantic
- **Database:** SQLite
- **Deployment:** Docker Compose

---

## 二、验证内容

### Docker

| 验证项 | 结果 |
|--------|------|
| `docker compose up --build` 首次构建 | ✅ 通过 |
| Backend 容器启动 (port 8000) | ✅ 通过 |
| Frontend 容器启动 (port 3000) | ✅ 通过 |
| 健康检查 `GET /api/v1/health` | ✅ 返回 `{"status":"ok"}` |
| 前端页面访问 (HTTP 200) | ✅ 通过 |
| Swagger 文档访问 | ✅ 通过 |
| 默认 Admin 登录 | ✅ 返回 JWT Token |
| `docker compose down` 停止 | ✅ 正常停止 |

### 启动顺序

1. Backend (FastAPI) — Port 8000
2. Frontend (Next.js) — Port 3000（依赖 Backend）

### 访问地址

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |

---

## 三、README

| 检查项 | 状态 |
|--------|------|
| 项目简介 | ✅ |
| 目录结构 | ✅ |
| 运行环境 | ✅ |
| Docker 启动说明 | ✅ |
| 默认账号（admin / admin123） | ✅ |
| 前端地址 | ✅ |
| 后端地址 | ✅ |
| Swagger 地址 | ✅ |
| 主要功能列表 | ✅ |
| 开发状态（Current Version: v0.1.0） | ✅ |
| 本地开发说明 | ✅ |

---

## 四、Browser Checklist

| 测试范围 | 测试项数 | 结果 |
|----------|----------|------|
| 登录（Login） | 7 | ✅ |
| Dashboard（数据看板） | 8 | ✅ |
| Lead（线索管理） | 16 | ✅ |
| FollowUp（跟进记录） | 5 | ✅ |
| Resume Import（简历导入） | 6 | ✅ |
| LeadDraft（简历草稿） | 5 | ✅ |
| Enrolled（已报名） | 3 | ✅ |
| User Management（用户管理） | 5 | ✅ |
| Password（修改密码） | 4 | ✅ |
| Permission（权限控制） | 6 | ✅ |
| General（通用检查） | 4 | ✅ |
| **合计** | **69** | **全部通过** |

---

## 五、Known Issues

| # | 问题 | 影响范围 | 计划 |
|---|------|----------|------|
| 1 | AI Resume 解析尚未启用 | Resume Import 仅支持规则提取，AI 增强解析未接入 | v0.2 |
| 2 | SQLite 不支持高并发 | 单机低并发可用 | v1.0 迁移 PostgreSQL |
| 3 | 单机部署，无高可用 | 单点故障风险 | 后续版本 |
| 4 | 不支持 HTTPS | 公网部署需额外 Nginx 配置 | 后续版本 |
| 5 | 不支持移动端 | 仅桌面端体验 | 后续版本 |

---

## 六、发布建议

- [x] 所有功能开发完成
- [x] Docker 部署验证通过
- [x] README 文档完善
- [x] Release 文档已生成
- [x] Browser Checklist 已生成
- [x] 无 P0 / P1 缺陷

**当前版本建议发布：v0.1.0** ✅

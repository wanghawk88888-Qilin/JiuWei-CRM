# JiuWei CRM 发布说明

**Version：** v0.1.0
**发布日期：** 2026-07-02
**状态：** Released

---

## 1. 版本定位

JiuWei CRM v0.1.0 是项目的第一个正式可运行版本（MVP）。

本版本目标不是构建完整 ERP，而是交付一套能够支持招生老师真实工作的轻量级 CRM。

核心目标：

- 建立统一招生线索管理平台
- 替代 Excel 管理客户
- 建立咨询与跟进闭环
- 为后续 AI CRM 建立基础架构

---

## 2. 本版本功能

### Auth

- 用户登录
- JWT 身份认证
- 三角色权限模型（admin / manager / counselor）
- 当前用户信息
- 修改密码

### Dashboard

- 全部线索统计
- 今日新增
- 待跟进
- 已报名统计
- 今日待跟进
- 最近新增线索

### Lead

- 新建线索
- 编辑线索
- 删除线索（软删除）
- 查询线索
- 搜索
- 来源筛选
- 状态筛选
- 转已报名（Lead → Enrolled）

### FollowUp

- 新增跟进
- 查看跟进
- 删除跟进
- 时间轴展示

### Resume Import

- Word 上传
- PDF 上传
- 文本解析
- 手机号规则提取
- 邮箱规则提取
- AI 增强解析（可选）
- LeadDraft 生成
- LeadDraft 确认
- LeadDraft 丢弃

### User Management

- 用户列表
- 创建用户
- 编辑用户
- 删除用户
- 角色分配

### Config

- 线索来源管理
- 意向课程管理
- 系统配置

---

## 3. Known Issues

| # | 问题 | 影响 | 计划 |
|---|------|------|------|
| 1 | AI Resume 解析尚未启用 | Resume Import 仅支持规则提取，AI 增强解析功能预留但未接入大模型 | v0.2 集成 |
| 2 | SQLite 不适用于高并发场景 | 单机低并发场景可正常使用 | v1.0 迁移至 PostgreSQL |
| 3 | 单机部署，不支持多实例 | 无高可用能力 | 后续版本 |
| 4 | 不支持 HTTPS | 公网部署需额外配置 Nginx 反向代理 | 后续版本 |
| 5 | 不支持移动端适配 | 仅桌面端浏览器体验良好 | 后续版本 |
| 6 | 不支持域名访问 | 仅通过 IP:Port 访问 | 后续版本 |

---

## 4. 本版本不包含

以下功能明确不属于 v0.1.0：

- 报名管理
- 缴费管理
- 班级管理
- 学习管理
- 就业管理
- 多校区
- 多租户
- 微信通知
- 企业微信
- 官网自动 Lead
- AI 客服
- AI 销售助手
- 多模型管理
- BI 报表
- 移动端
- HTTPS / 域名
- CI/CD 自动部署

---

## 5. 技术栈

| 层级 | 技术 |
|------|------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| Backend | Python 3.13, FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| Deployment | Docker Compose |

---

## 6. 部署方式

```text
GitHub
    ↓
git pull
    ↓
docker compose up --build -d
```

通过浏览器访问 `http://<IP>:3000` 使用系统。

---

## 7. 已完成文档

```
docs/
├── 01-PRD/          # 产品需求文档
├── 02-Prototype/    # 原型设计
├── 03-Database/     # 数据库设计
├── 04-API/          # API 设计
├── 05-Development/  # 开发计划
├── 06-Test/         # 测试文档
├── 07-Deployment/   # 部署文档
├── 08-Release/      # 发布说明
└── 09-Backlog/      # 需求积压
```

---

## 8. 发布验收

- [x] PRD 验收
- [x] Prototype 验收
- [x] Database 验收
- [x] API 验收
- [x] Development 验收
- [x] Test 验收
- [x] Deployment 验收
- [x] Docker Compose 启动验证
- [x] 浏览器功能验证
- [x] 无 P0 / P1 缺陷

---

## 9. Next Version：v0.2

v0.2 计划包含：

- 报名管理
- Lead 分配优化
- Dashboard 增强
- AI Resume 解析集成
- 更多筛选与搜索能力

---

## 10. 后续版本规划

| 版本 | 主要内容 |
|------|----------|
| v0.2 | 报名管理、AI 简历解析、Lead 分配优化 |
| v0.3 | 班级管理、学员管理、报名流程完善 |
| v1.0 | 正式上线版本，完成招生业务闭环 |
| v1.1 | AI 自动跟进建议 |
| v1.2 | 微信通知 |
| v1.3 | 企业微信集成 |
| v2.0 | 官网 Lead 自动进入 CRM |
| v2.1 | AI 客服自动创建 Lead |
| v2.2 | AI 销售助手 |
| v3.0 | 招生运营平台 |

---

## 11. 版本发布记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1.0 | 2026-07-02 | MVP 首个正式可运行版本 |

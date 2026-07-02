# JiuWei CRM 开发计划文档

**版本：** v0.1 MVP
**状态：** Final
**更新时间：** 2026-07-02
**前端：** Next.js + React + Tailwind CSS
**后端：** FastAPI
**数据库：** SQLite

---

# 1. 开发目标

v0.1 的开发目标是在 1 周内完成一个可运行、可演示、可真实录入招生线索的 CRM MVP。

本版本重点实现：

* 用户登录
* Dashboard 首页
* 线索列表
* 新建线索
* 线索详情
* 跟进记录
* Word/PDF 简历上传
* 线索草稿确认
* 基础配置读取

---

# 2. 开发原则

## 原则1：先跑通主流程

优先完成：

```text
登录
  ↓
创建线索
  ↓
查看线索
  ↓
新增跟进
  ↓
上传简历
  ↓
确认草稿生成 Lead
```

## 原则2：AI 不阻塞主流程

v0.1 可以预留 AI 解析接口。

如果大模型暂时不可用，系统仍应支持：

* 手工录入线索
* 规则提取手机号、邮箱等基础字段
* 人工确认保存 Lead

## 原则3：页面先简洁可用

不追求复杂视觉效果。

优先保证：

* 页面能打开
* 表单能保存
* 列表能查询
* 详情能查看
* 跟进能记录

## 原则4：不做 ERP 化扩展

v0.1 不开发：

* 报名
* 缴费
* 班级
* 学习
* 就业
* 微信
* 企业微信
* 官网自动线索
* AI 销售助手

---

# 3. 项目目录结构

建议最终形成：

```text
JiuWei-CRM/
├── docs/
│   ├── 01-PRD/
│   ├── 02-Prototype/
│   ├── 03-Database/
│   ├── 04-API/
│   ├── 05-Development/
│   ├── 06-Test/
│   ├── 07-Deployment/
│   ├── 08-Release/
│   └── 09-Backlog/
│
├── frontend/
│
├── backend/
│
├── docker/
│
├── scripts/
│
├── .gitignore
├── README.md
└── LICENSE
```

---

# 4. 后端开发计划

## 4.1 后端初始化

在 `backend/` 中初始化 FastAPI 项目。

建议结构：

```text
backend/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   ├── core/
│   └── utils/
├── data/
├── uploads/
├── requirements.txt
└── README.md
```

---

## 4.2 后端模块划分

| 模块             | 说明           |
| -------------- | ------------ |
| auth           | 登录、JWT、当前用户  |
| users          | 用户查询与基础管理    |
| leads          | 线索 CRUD      |
| followups      | 跟进记录         |
| resume_imports | 简历上传、解析、草稿生成 |
| lead_drafts    | 草稿查询、确认、丢弃   |
| config         | 线索来源、课程、系统配置 |
| dashboard      | 首页统计         |

---

## 4.3 后端开发顺序

### Step 1：基础框架

完成：

* FastAPI 项目启动
* SQLite 连接
* 数据表创建脚本
* 初始数据插入
* CORS 配置

### Step 2：用户与认证

完成：

* 登录接口
* JWT Token 生成
* 当前用户接口
* 简化权限中间件

### Step 3：Lead 主流程

完成：

* 线索列表
* 创建线索
* 线索详情
* 更新线索
* 软删除线索

### Step 4：FollowUp

完成：

* 查询跟进记录
* 新增跟进记录
* 删除跟进记录

### Step 5：Resume Import

完成：

* Word/PDF 上传
* 临时文件保存
* 文本解析
* 手机号、邮箱规则提取
* LeadDraft 生成
* 草稿确认生成 Lead
* 草稿丢弃
* 原始文件按策略处理

### Step 6：Dashboard 与配置

完成：

* 首页统计
* 今日待跟进
* 最近新增线索
* 线索来源列表
* 课程列表
* 系统配置读取

---

# 5. 前端开发计划

## 5.1 前端初始化

在 `frontend/` 中初始化 Next.js 项目。

建议技术：

* Next.js
* React
* Tailwind CSS
* TypeScript

建议结构：

```text
frontend/
├── app/
│   ├── login/
│   ├── dashboard/
│   ├── leads/
│   ├── leads/new/
│   ├── leads/[id]/
│   └── settings/
├── components/
├── lib/
├── types/
└── README.md
```

---

## 5.2 页面开发顺序

### Step 1：登录页

实现：

* 用户名
* 密码
* 登录按钮
* 登录成功后进入 Dashboard

### Step 2：基础布局

实现：

* 左侧导航
* 顶部用户信息
* 主内容区域

导航：

```text
首页
线索管理
系统设置
```

### Step 3：Dashboard

实现：

* 全部线索
* 今日新增
* 待跟进
* 已报名
* 今日待跟进列表
* 最近新增线索
* 新建线索按钮
* 上传简历按钮

### Step 4：线索列表

实现：

* 搜索
* 来源筛选
* 状态筛选
* 负责人筛选
* 线索表格
* 点击进入详情

### Step 5：新建线索

实现两个 Tab：

* 手工录入
* 上传简历

手工录入：

* 基础字段表单
* 保存

上传简历：

* 文件选择
* 上传
* 解析结果预览
* 确认保存为 Lead

### Step 6：线索详情

实现：

* 客户基础信息
* 当前状态
* 负责人
* 跟进时间轴
* 新增跟进按钮
* 未来扩展区域占位

### Step 7：系统设置

实现：

* 线索来源展示
* 意向课程展示
* 简历保留策略展示

v0.1 可先只读。

---

# 6. 简历解析开发要求

## 6.1 文件类型

支持：

* `.docx`
* `.pdf`

暂不支持：

* 图片简历
* 扫描件 OCR
* 压缩包
* Excel

## 6.2 基础规则提取

必须实现：

* 手机号
* 邮箱

可选实现：

* 姓名
* 学历
* 学校
* 专业

## 6.3 单一大模型增强

v0.1 仅预留服务接口。

不得实现：

* 多模型切换
* 模型路由
* 模型效果评估

如实现默认模型调用，必须保证：

* 调用失败不影响草稿生成
* AI 字段可为空
* API 返回明确提示

---

# 7. 1周开发节奏

| 时间    | 任务                              |
| ----- | ------------------------------- |
| Day 1 | PRD、Prototype、Database、API 文档完成 |
| Day 2 | 后端初始化、数据库、认证、Lead API           |
| Day 3 | FollowUp、Config、Dashboard API   |
| Day 4 | Resume Import、LeadDraft 流程      |
| Day 5 | 前端初始化、登录、布局、Dashboard、线索列表      |
| Day 6 | 新建线索、上传简历、线索详情、跟进记录             |
| Day 7 | 联调、测试、修复、部署准备                   |

---

# 8. 最小演示路径

v0.1 必须能完成以下演示：

```text
登录系统
  ↓
查看 Dashboard
  ↓
新建一条手工线索
  ↓
在线索列表中看到该线索
  ↓
进入线索详情
  ↓
新增一条跟进记录
  ↓
上传一份 Word/PDF 简历
  ↓
生成 LeadDraft
  ↓
确认保存为正式 Lead
```

---

# 9. 开发边界

v0.1 不做：

* 复杂权限后台
* 用户注册
* 找回密码
* 多租户
* 多校区
* 支付
* 班级
* 课程排期
* 就业管理
* 微信/企业微信真实集成
* 官网自动接入
* AI销售助手
* 复杂报表
* 移动端适配

---

# 10. 开发质量保证流程

JiuWei CRM 所有功能模块均采用统一开发流程。

任何模块不得直接进入下一模块开发。

必须完成以下四个阶段。

## 1. 开发实现（Development）

依据：

- PRD
- Prototype
- Database
- API

完成模块编码。

不得超出当前版本需求范围。

---

## 2. 开发者自测（Developer Self Test）

开发完成后，必须完成：

- Docker Compose 启动验证
- Swagger 接口验证
- curl 接口验证
- 数据库验证
- 自检无异常

开发者不得提交未经验证的代码。

---

## 3. 模块开发报告（Development Report）

每完成一个模块，必须生成：

reports/

例如：

reports/
step-01-auth.md

step-02-lead.md

报告至少包含：

- 本次修改文件
- 新增接口
- 数据库变化
- 自测过程
- 自测结果
- 已知问题
- 下一步建议

---

## 4. 产品验收（Acceptance Test）

产品负责人依据模块验收清单进行验证。

至少包括：

- Swagger 验证
- API 验证
- 数据验证
- 页面验证（如适用）

只有通过产品验收，模块才允许进入下一阶段。

---

## 5. 架构 Review

模块验收通过后，由架构负责人完成最终 Review。

确认：

- 代码符合项目规范
- API 符合设计
- 数据结构符合设计
- 未引入新的技术债务

Review 通过后，模块状态变为：

PASS

方可开始下一模块开发。

---

## 开发原则（新增）

新增原则10：

原则10：任何模块必须经过"开发实现 → 开发者自测 → 产品验收 → 架构 Review"四个阶段，并最终达到 PASS 状态后，方可进入下一模块开发。

---

# 11. 验收标准

Development-v0.1 完成后，应满足：

* 前后端目录初始化完成。
* FastAPI 可启动。
* Next.js 可启动。
* SQLite 可建表。
* 登录接口可用。
* Lead 主流程可用。
* FollowUp 主流程可用。
* Resume Import 主流程可用。
* Dashboard 基础数据可用。
* 前端页面可访问并完成最小演示路径。
* 所有实现与 PRD、Prototype、Database、API 文档一致。

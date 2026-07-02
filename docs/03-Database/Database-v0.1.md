# JiuWei CRM 数据库设计文档

**版本：** v0.1 MVP  
**状态：** Final  
**更新时间：** 2026-07-02  
**数据库：** SQLite  
**后续升级目标：** PostgreSQL

---

# 1. 数据库设计目标

v0.1 数据库仅服务于 MVP 阶段功能，支持用户管理、线索管理、跟进记录、简历解析后的结构化信息保存、基础配置管理，并为未来 AI、微信、企业微信、官网线索、AI 销售助手等能力预留扩展空间。

数据库设计保持轻量，不引入传统 ERP 的复杂表结构。

---

# 2. 数据库设计原则

## 原则1：业务数据与临时数据分离

- `Lead` 是正式业务数据。
- `LeadDraft` 是简历解析后的临时确认数据。
- `ImportLog` 是系统日志。

三者职责不得混用。

## 原则2：业务数据库不依赖 AI

AI 仅负责信息提取、内容分析和建议生成。  
即使 AI 服务不可用，Lead 创建流程仍必须正常完成。

## 原则3：CRM 保存结构化数据

Word、PDF 简历属于信息采集媒介，默认不作为 CRM 长期业务资产保存。

管理员可配置：

- 立即删除
- 保留 1 天
- 保留 3 天
- 保留 7 天
- 保留 15 天

超过保留时间自动清理。

## 原则4：采用扩展式设计

未来新增 AI、微信、企业微信、官网 Lead、AI 客服等能力，优先通过新增表实现，不频繁修改 `leads` 主表。

---

# 3. 核心业务对象

| 对象 | 说明 |
|---|---|
| User | 系统用户 |
| Lead | 招生线索 |
| LeadFollowUp | 跟进记录 |
| LeadDraft | 简历解析后的线索草稿 |
| LeadSource | 线索来源 |
| Course | 意向课程 |
| ImportLog | 文件导入与解析日志 |
| SystemSetting | 系统配置 |

---

# 4. 数据表设计

## 4.1 users 用户表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    real_name TEXT NOT NULL,
    role TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

角色：

| role      | 名称    | 权限                    |
| --------- | ----- | --------------------- |
| admin     | 超级管理员 | 系统配置、用户管理、查看全部线索、分配线索 |
| manager   | 招生主管  | 查看团队线索、分配线索、查看团队统计    |
| counselor | 招生老师  | 管理本人负责线索、上传简历、记录跟进    |

v0.1 采用简化 RBAC。权限原则是：**数据权限优先于功能权限**。

---

## 4.2 leads 线索表

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    wechat TEXT,
    email TEXT,
    gender TEXT,
    age INTEGER,
    education TEXT,
    school TEXT,
    major TEXT,
    city TEXT,
    current_job TEXT,
    work_years TEXT,
    latest_company TEXT,
    latest_position TEXT,
    intended_course_id INTEGER,
    source_id INTEGER,
    status TEXT NOT NULL DEFAULT 'new',
    intention_level TEXT,
    owner_id INTEGER,
    remark TEXT,
    ai_summary TEXT,
    ai_course_suggestion TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (intended_course_id) REFERENCES courses(id),
    FOREIGN KEY (source_id) REFERENCES lead_sources(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

状态枚举：

* new：新线索
* consulted：已咨询
* following：跟进中
* high_intent：高意向
* enrolled：已报名
* invalid：无效

---

## 4.3 lead_followups 跟进记录表

```sql
CREATE TABLE lead_followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    followup_type TEXT NOT NULL,
    content TEXT NOT NULL,
    intention_level TEXT,
    next_followup_at TEXT,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

跟进方式：

* phone：电话
* wechat：微信
* offline：面谈
* other：其他

---

## 4.4 lead_drafts 线索草稿表

```sql
CREATE TABLE lead_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_log_id INTEGER,
    name TEXT,
    phone TEXT,
    wechat TEXT,
    email TEXT,
    gender TEXT,
    age INTEGER,
    education TEXT,
    school TEXT,
    major TEXT,
    graduation_time TEXT,
    city TEXT,
    work_years TEXT,
    latest_company TEXT,
    latest_position TEXT,
    skills TEXT,
    ai_summary TEXT,
    ai_course_suggestion TEXT,
    raw_text_excerpt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    confirmed_lead_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (import_log_id) REFERENCES import_logs(id),
    FOREIGN KEY (confirmed_lead_id) REFERENCES leads(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

LeadDraft 是临时数据。用户确认后生成 Lead；用户取消则废弃；系统可定时清理。

状态：

* pending：待确认
* confirmed：已生成正式线索
* discarded：已丢弃

---

## 4.5 import_logs 导入日志表

```sql
CREATE TABLE import_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    temp_file_path TEXT,
    parse_status TEXT NOT NULL DEFAULT 'pending',
    parse_error TEXT,
    extracted_text_length INTEGER,
    llm_used INTEGER NOT NULL DEFAULT 0,
    llm_provider TEXT,
    temp_file_expires_at TEXT,
    file_deleted_at TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

ImportLog 仅记录上传、解析、处理、删除状态，不作为业务数据表。

原始简历默认不长期保存，可按配置临时保留。

---

## 4.6 lead_sources 线索来源表

```sql
CREATE TABLE lead_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

默认来源：

* 手工录入
* 简历上传
* 微信
* 官网
* 其他

---

## 4.7 courses 意向课程表

```sql
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

默认课程：

* AI智能应用开发工程师
* AI测试开发工程师
* 待确认

---

## 4.8 system_settings 系统配置表

```sql
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

默认配置：

* resume_temp_retention_enabled
* resume_temp_retention_days
* default_llm_enabled

---

# 5. 索引设计

```sql
CREATE INDEX idx_leads_phone ON leads(phone);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_owner_id ON leads(owner_id);
CREATE INDEX idx_leads_source_id ON leads(source_id);
CREATE INDEX idx_leads_created_at ON leads(created_at);

CREATE INDEX idx_lead_followups_lead_id ON lead_followups(lead_id);
CREATE INDEX idx_lead_followups_next_followup_at ON lead_followups(next_followup_at);

CREATE INDEX idx_lead_drafts_status ON lead_drafts(status);
CREATE INDEX idx_import_logs_parse_status ON import_logs(parse_status);
```

---

# 6. 数据生命周期

## 6.1 Lead 生命周期

```text
new
  ↓
consulted
  ↓
following
  ↓
high_intent
  ↓
enrolled
```

也可进入：

```text
invalid
```

## 6.2 LeadDraft 生命周期

```text
pending
  ↓
confirmed / discarded
```

## 6.3 简历文件生命周期

```text
上传文件
  ↓
临时保存
  ↓
文本解析
  ↓
结构化提取
  ↓
生成 LeadDraft
  ↓
人工确认
  ↓
生成 Lead
  ↓
按配置删除原始文件
```

---

# 7. 后续扩展设计

未来能力通过新增表扩展。

## 7.1 AI 自动跟进建议

后续可新增：

```text
ai_followup_suggestions
```

## 7.2 微信通知

后续可新增：

```text
wechat_notifications
```

## 7.3 企业微信

后续可新增：

```text
wecom_contacts
wecom_messages
```

## 7.4 官网 Lead

后续可新增：

```text
web_form_submissions
```

## 7.5 AI 客服

后续可新增：

```text
ai_chat_sessions
ai_chat_messages
```

---

# 8. v0.1 不设计内容

以下内容不在 v0.1 建表：

* 报名
* 缴费
* 班级
* 学习
* 就业
* 企业微信消息
* 官网行为分析
* AI销售助手上下文
* 多模型管理

---

# 9. 验收标准

数据库设计应满足：

* SQLite 可直接建库。
* 后续可迁移 PostgreSQL。
* 满足 PRD-v0.1。
* 满足 Prototype-v0.1。
* 支持用户、线索、跟进、简历解析草稿、导入日志和基础配置。
* 支持未来 AI CRM 扩展。

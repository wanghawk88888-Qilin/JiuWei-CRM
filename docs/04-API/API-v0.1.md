# JiuWei CRM API 设计文档

**版本：** v0.1 MVP
**状态：** Final
**更新时间：** 2026-07-02
**后端框架：** FastAPI
**数据格式：** JSON
**认证方式：** JWT Token

---

# 1. API 设计目标

API-v0.1 服务于 JiuWei CRM MVP，重点支持：

* 用户登录与当前用户信息
* 线索创建、查询、更新、删除
* 跟进记录创建与查询
* Word/PDF 简历上传与解析
* LeadDraft 确认生成正式 Lead
* 基础配置读取
* 简化权限控制

API 设计应保持轻量、清晰、可直接指导 FastAPI 开发。

---

# 2. 通用约定

## 2.1 Base URL

```text
/api/v1
```

## 2.2 请求格式

除文件上传接口外，统一使用：

```http
Content-Type: application/json
```

文件上传使用：

```http
Content-Type: multipart/form-data
```

## 2.3 返回格式

统一返回：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

错误返回：

```json
{
  "success": false,
  "error_code": "LEAD_NOT_FOUND",
  "message": "线索不存在"
}
```

---

# 3. 认证与权限

## 3.1 登录认证

v0.1 使用 JWT Token。

登录成功后，前端在请求头中携带：

```http
Authorization: Bearer <token>
```

## 3.2 用户角色

v0.1 支持三个角色：

| role      | 名称    |
| --------- | ----- |
| admin     | 超级管理员 |
| manager   | 招生主管  |
| counselor | 招生老师  |

## 3.3 数据权限原则

权限原则：

> 数据权限优先于功能权限。

规则：

* admin：可访问全部数据。
* manager：可访问团队数据。
* counselor：仅可访问本人负责数据。

v0.1 可简化实现：

* admin 查看全部线索。
* manager 查看全部线索，后续再细化团队。
* counselor 仅查看 `owner_id = 当前用户ID` 的线索。

---

# 4. Auth API

## 4.1 用户登录

```http
POST /api/v1/auth/login
```

### Request

```json
{
  "username": "admin",
  "password": "123456"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "real_name": "管理员",
      "role": "admin"
    }
  },
  "message": "登录成功"
}
```

---

## 4.2 获取当前用户信息

```http
GET /api/v1/auth/me
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin",
    "real_name": "管理员",
    "role": "admin",
    "phone": "",
    "email": ""
  },
  "message": "ok"
}
```

---

# 5. Lead API

## 5.1 查询线索列表

```http
GET /api/v1/leads
```

### Query 参数

| 参数        | 说明          |
| --------- | ----------- |
| keyword   | 搜索姓名、手机号、微信 |
| status    | 线索状态        |
| source_id | 线索来源        |
| owner_id  | 负责人         |
| page      | 页码，默认 1     |
| page_size | 每页数量，默认 20  |

### Response

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "张三",
        "phone": "13800000000",
        "wechat": "zhangsan",
        "source": "简历上传",
        "intended_course": "AI测试开发工程师",
        "status": "new",
        "intention_level": "medium",
        "owner": "李老师",
        "last_followup_at": "2026-07-02 10:00:00",
        "next_followup_at": "2026-07-03 10:00:00",
        "updated_at": "2026-07-02 10:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "message": "ok"
}
```

---

## 5.2 创建线索

```http
POST /api/v1/leads
```

### Request

```json
{
  "name": "张三",
  "phone": "13800000000",
  "wechat": "zhangsan",
  "email": "zhangsan@example.com",
  "gender": "male",
  "age": 25,
  "education": "本科",
  "school": "某某大学",
  "major": "计算机科学与技术",
  "city": "北京",
  "current_job": "测试工程师",
  "work_years": "3年",
  "latest_company": "某科技公司",
  "latest_position": "测试工程师",
  "intended_course_id": 2,
  "source_id": 1,
  "status": "new",
  "intention_level": "medium",
  "owner_id": 3,
  "remark": "对AI测试方向感兴趣"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 1
  },
  "message": "线索创建成功"
}
```

---

## 5.3 获取线索详情

```http
GET /api/v1/leads/{lead_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "张三",
    "phone": "13800000000",
    "wechat": "zhangsan",
    "email": "zhangsan@example.com",
    "gender": "male",
    "age": 25,
    "education": "本科",
    "school": "某某大学",
    "major": "计算机科学与技术",
    "city": "北京",
    "current_job": "测试工程师",
    "work_years": "3年",
    "latest_company": "某科技公司",
    "latest_position": "测试工程师",
    "intended_course": {
      "id": 2,
      "name": "AI测试开发工程师"
    },
    "source": {
      "id": 1,
      "name": "手工录入"
    },
    "status": "new",
    "intention_level": "medium",
    "owner": {
      "id": 3,
      "real_name": "李老师"
    },
    "remark": "对AI测试方向感兴趣",
    "ai_summary": "",
    "ai_course_suggestion": "",
    "tags": "",
    "created_at": "2026-07-02 10:00:00",
    "updated_at": "2026-07-02 10:00:00"
  },
  "message": "ok"
}
```

---

## 5.4 更新线索

```http
PUT /api/v1/leads/{lead_id}
```

### Request

字段同创建线索，可部分更新。

### Response

```json
{
  "success": true,
  "data": {
    "id": 1
  },
  "message": "线索更新成功"
}
```

---

## 5.5 删除线索

```http
DELETE /api/v1/leads/{lead_id}
```

v0.1 采用软删除，写入 `deleted_at`。

### Response

```json
{
  "success": true,
  "data": null,
  "message": "线索已删除"
}
```

---

# 6. FollowUp API

## 6.1 查询某线索的跟进记录

```http
GET /api/v1/leads/{lead_id}/followups
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "followup_type": "phone",
      "content": "电话沟通，客户对AI测试课程感兴趣。",
      "intention_level": "high",
      "next_followup_at": "2026-07-03 10:00:00",
      "created_by": {
        "id": 3,
        "real_name": "李老师"
      },
      "created_at": "2026-07-02 10:00:00"
    }
  ],
  "message": "ok"
}
```

---

## 6.2 新增跟进记录

```http
POST /api/v1/leads/{lead_id}/followups
```

### Request

```json
{
  "followup_type": "phone",
  "content": "电话沟通，客户对AI测试课程感兴趣。",
  "intention_level": "high",
  "next_followup_at": "2026-07-03 10:00:00"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 1
  },
  "message": "跟进记录已保存"
}
```

---

## 6.3 删除跟进记录

```http
DELETE /api/v1/followups/{followup_id}
```

v0.1 采用软删除。

### Response

```json
{
  "success": true,
  "data": null,
  "message": "跟进记录已删除"
}
```

---

# 7. Resume Import API

## 7.1 上传简历并解析

```http
POST /api/v1/resume-imports
```

### Request

```http
multipart/form-data
file: Word/PDF
```

### 处理流程

```text
上传文件
  ↓
临时保存
  ↓
文本解析
  ↓
规则提取确定性字段
  ↓
单一大模型可选增强识别
  ↓
生成 LeadDraft
  ↓
返回草稿ID
```

### Response

```json
{
  "success": true,
  "data": {
    "import_log_id": 1,
    "lead_draft_id": 1,
    "parse_status": "parsed",
    "draft": {
      "name": "张三",
      "phone": "13800000000",
      "email": "zhangsan@example.com",
      "education": "本科",
      "school": "某某大学",
      "major": "计算机科学与技术",
      "skills": "Python, 测试, 自动化",
      "ai_summary": "候选人具备测试基础，适合AI测试开发方向。",
      "ai_course_suggestion": "AI测试开发工程师"
    }
  },
  "message": "简历解析完成"
}
```

---

## 7.2 获取线索草稿详情

```http
GET /api/v1/lead-drafts/{draft_id}
```

### Response

返回 LeadDraft 全部字段。

---

## 7.3 确认草稿生成正式线索

```http
POST /api/v1/lead-drafts/{draft_id}/confirm
```

### Request

可传入用户修正后的字段。

```json
{
  "name": "张三",
  "phone": "13800000000",
  "wechat": "zhangsan",
  "email": "zhangsan@example.com",
  "gender": "male",
  "age": 25,
  "education": "本科",
  "school": "某某大学",
  "major": "计算机科学与技术",
  "city": "北京",
  "work_years": "3年",
  "latest_company": "某科技公司",
  "latest_position": "测试工程师",
  "intended_course_id": 2,
  "source_id": 2,
  "owner_id": 3,
  "remark": "由简历导入生成"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "lead_id": 1
  },
  "message": "已生成正式线索"
}
```

确认后：

* 创建 Lead
* 更新 LeadDraft 状态为 confirmed
* 写入 confirmed_lead_id
* 按系统配置处理原始简历文件

---

## 7.4 丢弃线索草稿

```http
POST /api/v1/lead-drafts/{draft_id}/discard
```

### Response

```json
{
  "success": true,
  "data": null,
  "message": "线索草稿已丢弃"
}
```

---

# 8. Config API

## 8.1 获取线索来源

```http
GET /api/v1/config/lead-sources
```

## 8.2 获取课程列表

```http
GET /api/v1/config/courses
```

## 8.3 获取系统配置

```http
GET /api/v1/config/system-settings
```

仅 admin 可访问系统配置。

---

# 9. Dashboard API

## 9.1 获取首页统计

```http
GET /api/v1/dashboard/summary
```

### Response

```json
{
  "success": true,
  "data": {
    "total_leads": 100,
    "today_new_leads": 5,
    "pending_followups": 12,
    "enrolled_leads": 3
  },
  "message": "ok"
}
```

---

## 9.2 获取今日待跟进

```http
GET /api/v1/dashboard/today-followups
```

---

## 9.3 获取最近新增线索

```http
GET /api/v1/dashboard/recent-leads
```

---

# 10. 错误码设计

| 错误码                  | 说明            |
| -------------------- | ------------- |
| UNAUTHORIZED         | 未登录或 Token 无效 |
| FORBIDDEN            | 无权限访问         |
| USER_NOT_FOUND       | 用户不存在         |
| LEAD_NOT_FOUND       | 线索不存在         |
| FOLLOWUP_NOT_FOUND   | 跟进记录不存在       |
| LEAD_DRAFT_NOT_FOUND | 线索草稿不存在       |
| INVALID_FILE_TYPE    | 文件类型不支持       |
| FILE_TOO_LARGE       | 文件过大          |
| RESUME_PARSE_FAILED  | 简历解析失败        |
| VALIDATION_ERROR     | 请求参数错误        |
| INTERNAL_ERROR       | 系统内部错误        |

---

# 11. v0.1 不设计接口

以下接口不在 v0.1 范围：

* 报名接口
* 缴费接口
* 班级接口
* 学习记录接口
* 就业接口
* 微信消息接口
* 企业微信接口
* 官网自动建 Lead 接口
* AI 销售助手接口
* 多模型管理接口

---

# 12. 验收标准

API-v0.1 满足以下条件即通过：

* 支持登录并获取当前用户信息。
* 支持线索增删改查。
* 支持按权限查询线索。
* 支持跟进记录创建和查询。
* 支持 Word/PDF 简历上传。
* 支持生成 LeadDraft。
* 支持确认 LeadDraft 生成 Lead。
* 支持丢弃 LeadDraft。
* 支持基础配置读取。
* 支持 Dashboard 基础数据。
* AI 服务不可用时，不影响手工创建 Lead。

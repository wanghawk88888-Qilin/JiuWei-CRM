# Coding Step 2A：Lead Core 开发报告

**日期：** 2026-07-02
**状态：** PASS

---

## 1. 本次修改文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/models/lead.py` | 新增 | Lead SQLAlchemy 模型，映射 leads 表 |
| `backend/app/models/__init__.py` | 修改 | 导入 Lead 模型，确保表自动创建 |
| `backend/app/schemas/lead.py` | 新增 | Pydantic Schema：LeadCreate、LeadUpdate、LeadResponse、LeadListResponse |
| `backend/app/services/lead_service.py` | 新增 | Lead 业务服务层：CRUD + 软删除 + 权限过滤 |
| `backend/app/routers/leads.py` | 新增 | Lead 路由：5 个 RESTful 接口 |
| `backend/app/main.py` | 修改 | 注册 leads router |
| `reports/step-02A-lead-core.md` | 新增 | 本开发报告 |

---

## 2. 本次实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/leads` | 查询线索列表（分页） |
| POST | `/api/v1/leads` | 创建线索 |
| GET | `/api/v1/leads/{lead_id}` | 查询线索详情 |
| PUT | `/api/v1/leads/{lead_id}` | 更新线索（部分更新） |
| DELETE | `/api/v1/leads/{lead_id}` | 删除线索（软删除） |

---

## 3. 数据库变化

### 3.1 新增 leads 表

应用启动时自动创建 `leads` 表，包含以下字段：

- `id` — INTEGER PRIMARY KEY AUTOINCREMENT
- `name` — TEXT NOT NULL（必填）
- `phone`, `wechat`, `email` — 联系方式字段
- `gender`, `age`, `education`, `school`, `major`, `city` — 人口统计字段
- `current_job`, `work_years`, `latest_company`, `latest_position` — 职业信息字段
- `intended_course_id` — INTEGER NULLABLE（外键预留，本轮不强制约束）
- `source_id` — INTEGER NULLABLE（外键预留，本轮不强制约束）
- `status` — TEXT NOT NULL DEFAULT 'new'（线索状态）
- `intention_level` — TEXT NULLABLE（意向等级）
- `owner_id` — INTEGER NULLABLE（负责人 ID）
- `remark` — TEXT NULLABLE（备注）
- `ai_summary` — TEXT NULLABLE（AI 摘要）
- `ai_course_suggestion` — TEXT NULLABLE（AI 课程建议）
- `tags` — TEXT NULLABLE（标签）
- `created_at` — TEXT NOT NULL（创建时间）
- `updated_at` — TEXT NOT NULL（更新时间）
- `deleted_at` — TEXT NULLABLE（软删除时间）

### 3.2 未修改 users 表

`users` 表结构和默认 admin 初始化逻辑保持不变。Auth 模块不受任何影响。

---

## 4. 权限规则

| 角色 | 查看 | 创建 | 更新 | 删除 |
|---|---|---|---|---|
| **admin** | 全部 Lead | 可创建 | 可更新全部 | 可删除全部 |
| **manager** | 全部 Lead（v0.1 暂不限制团队） | 可创建 | 可更新全部 | 可删除（本轮允许） |
| **counselor** | 仅 `owner_id = 当前用户ID` | 自动设置 `owner_id` 为当前用户；不允许传入别人 ID | 仅自己负责的 Lead | 仅自己负责的 Lead |

---

## 5. 自测命令

### 5.1 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 5.2 创建 Lead

```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
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
    "intended_course_id": null,
    "source_id": null,
    "status": "new",
    "intention_level": "medium",
    "owner_id": 1,
    "remark": "对AI测试方向感兴趣"
  }'
```

### 5.3 获取 Lead 列表

```bash
curl http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer <token>"
```

### 5.4 获取 Lead 详情

```bash
curl http://localhost:8000/api/v1/leads/1 \
  -H "Authorization: Bearer <token>"
```

### 5.5 更新 Lead

```bash
curl -X PUT http://localhost:8000/api/v1/leads/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "status": "following",
    "intention_level": "high",
    "remark": "客户意向提升，准备继续跟进"
  }'
```

### 5.6 删除 Lead

```bash
curl -X DELETE http://localhost:8000/api/v1/leads/1 \
  -H "Authorization: Bearer <token>"
```

### 5.7 再次获取已删除 Lead

```bash
curl http://localhost:8000/api/v1/leads/1 \
  -H "Authorization: Bearer <token>"
```

---

## 6. 自测结果

| 测试项 | 结果 | 说明 |
|---|---|---|
| 登录获取 Token | ✅ PASS | 返回 access_token 和用户信息 |
| 创建 Lead | ✅ PASS | 返回 `{"success": true, "data": {"id": 1}}` |
| 获取 Lead 列表 | ✅ PASS | items 包含已创建的 Lead，total=1 |
| 获取 Lead 详情 | ✅ PASS | 返回所有字段 |
| 更新 Lead | ✅ PASS | status/remark 部分更新成功 |
| 删除 Lead | ✅ PASS | 软删除成功，deleted_at 写入 |
| 获取已删除 Lead | ✅ PASS | 返回 `LEAD_NOT_FOUND` |
| 删除后列表 | ✅ PASS | items 为空，total=0（已删除数据不出现在列表中） |
| Swagger 文档 | ✅ PASS | `/docs` 可访问，返回 200 |
| Auth 模块 | ✅ PASS | 不受影响，登录和 /me 接口正常 |

---

## 7. 已知问题

无。

---

## 8. 下一步建议

**Coding Step 2B：Lead Search & Filter。**

建议实现：
- `keyword` 搜索（姓名、手机号、微信）
- `status` 筛选
- `source_id` 筛选
- `owner_id` 筛选
- 可选：高级排序（按创建时间、更新时间、意向等级）

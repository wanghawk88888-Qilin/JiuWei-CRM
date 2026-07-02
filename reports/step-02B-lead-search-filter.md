# Coding Step 2B：Lead Search & Filter 开发报告

**日期：** 2026-07-02
**状态：** PASS

---

## 1. 本次修改文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/schemas/lead.py` | 修改 | `LeadListItem` 精简为轻量字段；新增 `last_followup_at` / `next_followup_at` 占位 |
| `backend/app/services/lead_service.py` | 修改 | `list_leads` 新增 keyword/status/source_id/owner_id 参数 |
| `backend/app/routers/leads.py` | 修改 | `GET /api/v1/leads` 新增 Query 参数接收与校验 |
| `reports/step-02B-lead-search-filter.md` | 新增 | 本开发报告 |

---

## 2. 本次优化接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/leads` | 查询线索列表（新增搜索、筛选、分页优化） |

**未修改接口：**
- POST `/api/v1/leads` — 不受影响
- GET `/api/v1/leads/{lead_id}` — 不受影响
- PUT `/api/v1/leads/{lead_id}` — 不受影响
- DELETE `/api/v1/leads/{lead_id}` — 不受影响
- POST `/api/v1/auth/login` — 不受影响
- GET `/api/v1/auth/me` — 不受影响

---

## 3. 新增查询参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `keyword` | string | 无 | 模糊搜索姓名(name)、手机号(phone)、微信(wechat) |
| `status` | string | 无 | 按线索状态精确筛选 |
| `source_id` | int | 无 | 按来源 ID 精确筛选 |
| `owner_id` | int | 无 | 按负责人 ID 筛选（受权限约束） |
| `page` | int | 1 | 页码，最小 1 |
| `page_size` | int | 20 | 每页数量，最大 100 |

### 3.1 keyword 搜索实现

```python
like_pattern = f"%{keyword}%"
query = query.filter(
    Lead.name.like(like_pattern)
    | Lead.phone.like(like_pattern)
    | Lead.wechat.like(like_pattern)
)
```

使用 SQL LIKE 实现模糊搜索，匹配 name、phone、wechat 三列中任意一列包含关键词的记录。

### 3.2 参数校验

- `status` 不在枚举范围时，返回 `VALIDATION_ERROR`
- `page` 通过 FastAPI `Query(ge=1)` 自动校验
- `page_size` 通过 FastAPI `Query(le=100)` 自动校验

---

## 4. 列表返回字段优化

### 4.1 列表接口（轻量）

`GET /api/v1/leads` 的 items 每项仅返回：

| 字段 | 说明 |
|---|---|
| `id` | ID |
| `name` | 姓名 |
| `phone` | 手机号 |
| `wechat` | 微信 |
| `source_id` | 来源 ID |
| `intended_course_id` | 意向课程 ID |
| `status` | 状态 |
| `intention_level` | 意向等级 |
| `owner_id` | 负责人 ID |
| `last_followup_at` | 最近跟进时间（暂为 null） |
| `next_followup_at` | 下次跟进时间（暂为 null） |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### 4.2 不在列表返回的字段

以下字段仅出现在 `GET /api/v1/leads/{lead_id}` 详情接口：

- `email`, `gender`, `age`, `education`, `school`, `major`, `city`
- `current_job`, `work_years`, `latest_company`, `latest_position`
- `remark`, `ai_summary`, `ai_course_suggestion`, `tags`

### 4.3 Schema 设计

- **LeadListItem** — 列表轻量 Schema
- **LeadResponse** — 详情完整 Schema
- **LeadCreate / LeadUpdate** — 不受影响

---

## 5. 权限规则

| 角色 | 查询权限 |
|---|---|
| **admin** | 可查看全部 Lead；可按任意 `owner_id` 筛选 |
| **manager** | v0.1 暂可查看全部 Lead；可按任意 `owner_id` 筛选 |
| **counselor** | 仅能查看 `owner_id = 当前用户ID` 的 Lead；**无论是否传入 `owner_id` 参数**，都不能查看他人 Lead |

### 5.1 实现逻辑

```python
# Owner filter — counselors are forced to their own data regardless of param
if current_user.role == "counselor":
    query = query.filter(Lead.owner_id == current_user.id)
elif owner_id is not None:
    query = query.filter(Lead.owner_id == owner_id)
```

关键点：counselor 分支优先级最高，在 `owner_id` 参数之前执行，确保参数无法绕过权限。

---

## 6. 自测命令

### 6.1 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 6.2 创建 2 条 Lead

```bash
# Lead 1
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"张三","phone":"13800001111","wechat":"zhangsan_wx","status":"new","intention_level":"medium","owner_id":1}'

# Lead 2
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"李四","phone":"13900002222","wechat":"lisi_wx","status":"following","intention_level":"high","owner_id":2}'
```

### 6.3 查询 Lead 列表

```bash
curl "http://localhost:8000/api/v1/leads?page=1&page_size=20" \
  -H "Authorization: Bearer <token>"
```

### 6.4 keyword 搜索

```bash
# 按姓名
curl --get "http://localhost:8000/api/v1/leads" \
  --data-urlencode "keyword=张三" \
  -H "Authorization: Bearer <token>"

# 按手机号
curl --get "http://localhost:8000/api/v1/leads" \
  --data-urlencode "keyword=1390000" \
  -H "Authorization: Bearer <token>"

# 按微信
curl --get "http://localhost:8000/api/v1/leads" \
  --data-urlencode "keyword=lisi_wx" \
  -H "Authorization: Bearer <token>"
```

### 6.5 status 筛选

```bash
curl --get "http://localhost:8000/api/v1/leads" \
  --data-urlencode "status=new" \
  -H "Authorization: Bearer <token>"
```

### 6.6 owner_id 筛选

```bash
curl "http://localhost:8000/api/v1/leads?owner_id=1" \
  -H "Authorization: Bearer <token>"
```

### 6.7 page/page_size 分页

```bash
curl "http://localhost:8000/api/v1/leads?page=1&page_size=1" \
  -H "Authorization: Bearer <token>"
```

### 6.8 验证已删除 Lead 不出现在列表

```bash
# 删除
curl -X DELETE http://localhost:8000/api/v1/leads/4 \
  -H "Authorization: Bearer <token>"

# 列表不再包含已删除 Lead
curl "http://localhost:8000/api/v1/leads" \
  -H "Authorization: Bearer <token>"

# 详情返回 LEAD_NOT_FOUND
curl "http://localhost:8000/api/v1/leads/4" \
  -H "Authorization: Bearer <token>"
```

### 6.9 无效 status 参数校验

```bash
curl --get "http://localhost:8000/api/v1/leads" \
  --data-urlencode "status=invalid_status" \
  -H "Authorization: Bearer <token>"
```

---

## 7. 自测结果

| 测试项 | 结果 | 说明 |
|---|---|---|
| 登录获取 Token | ✅ PASS | 返回 access_token 和用户信息 |
| 创建 Lead 1（张三） | ✅ PASS | 返回 `{"success": true, "data": {"id": 4}}` |
| 创建 Lead 2（李四） | ✅ PASS | 返回 `{"success": true, "data": {"id": 5}}` |
| 查询 Lead 列表 | ✅ PASS | items 包含已创建的 Lead，total=3 |
| keyword 搜索（姓名） | ✅ PASS | keyword=张三 → 返回 1 条，name 包含"张三" |
| keyword 搜索（手机号） | ✅ PASS | keyword=1390000 → 返回 2 条（模糊匹配） |
| keyword 搜索（微信） | ✅ PASS | keyword=lisi_wx → 返回 1 条 |
| status 筛选 | ✅ PASS | status=new → 仅返回 status=new 的 Lead |
| owner_id 筛选 | ✅ PASS | owner_id=1 → 仅返回 owner_id=1 的 Lead |
| 分页（page=1, page_size=1） | ✅ PASS | items 最多 1 条，total=3 |
| 分页（page=2, page_size=1） | ✅ PASS | 返回第 2 页数据 |
| 无效 status 校验 | ✅ PASS | 返回 VALIDATION_ERROR + 有效值列表 |
| 列表轻量字段检查 | ✅ PASS | 不含 email/gender/age/education/school/major/city/current_job/work_years/latest_company/latest_position/remark/ai_summary/ai_course_suggestion/tags |
| 详情接口完整字段 | ✅ PASS | 包含所有字段 |
| 软删除后列表排除 | ✅ PASS | 删除后列表不再出现，total 减 1 |
| 软删除后详情 404 | ✅ PASS | 返回 LEAD_NOT_FOUND |
| Auth 模块 | ✅ PASS | 登录和 /me 接口正常 |
| Lead 其他 CRUD | ✅ PASS | POST / PUT / DELETE 正常 |
| Swagger 文档 | ✅ PASS | `/docs` 可访问，返回 200 |

---

## 8. 已知问题

无。

---

## 9. 下一步建议

**Coding Step 3：FollowUp 模块。**

建议实现：
- `GET /api/v1/leads/{lead_id}/followups` — 查询某线索的跟进记录
- `POST /api/v1/leads/{lead_id}/followups` — 新增跟进记录
- `DELETE /api/v1/followups/{followup_id}` — 删除跟进记录（软删除）
- 跟进记录创建后更新 Lead 的 `last_followup_at`
- 权限过滤（counselor 只能操作自己负责的 Lead 的跟进记录）

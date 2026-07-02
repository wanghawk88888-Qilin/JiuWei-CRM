# Coding Step 3：FollowUp 开发报告

**日期：** 2026-07-02
**状态：** PASS

---

## 1. 本次修改文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/models/followup.py` | 新增 | FollowUp SQLAlchemy 模型，映射 lead_followups 表 |
| `backend/app/models/__init__.py` | 修改 | 导入 FollowUp 模型，确保表自动创建 |
| `backend/app/schemas/followup.py` | 新增 | Pydantic Schema：FollowUpCreate、FollowUpResponse、FollowUpListResponse |
| `backend/app/services/followup_service.py` | 新增 | FollowUp 业务服务层：list / create / delete / get_by_id |
| `backend/app/routers/followups.py` | 新增 | FollowUp 路由：3 个 RESTful 接口 |
| `backend/app/main.py` | 修改 | 注册 followups router |
| `reports/step-03-followup.md` | 新增 | 本开发报告 |

---

## 2. 本次实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/leads/{lead_id}/followups` | 查询某线索的所有跟进记录 |
| POST | `/api/v1/leads/{lead_id}/followups` | 新增跟进记录 |
| DELETE | `/api/v1/followups/{followup_id}` | 删除跟进记录（软删除） |

---

## 3. 数据库变化

### 新增表：lead_followups

| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer, PK, autoincrement | 主键 |
| lead_id | Integer, NOT NULL | 关联线索ID |
| followup_type | String(50), NOT NULL | 跟进方式：phone / wechat / offline / other |
| content | Text, NOT NULL | 跟进内容 |
| intention_level | String(50), nullable | 意向等级：low / medium / high |
| next_followup_at | String(50), nullable | 下次跟进时间 |
| created_by | Integer, NOT NULL | 创建人ID |
| created_at | String(50), NOT NULL | 创建时间 |
| updated_at | String(50), NOT NULL | 更新时间 |
| deleted_at | String(50), nullable | 软删除时间 |

### 未修改的表

- **users** 表结构未修改
- **leads** 表结构未修改

---

## 4. 权限规则

FollowUp 权限基于 Lead 权限控制：

| 角色 | 权限 |
|---|---|
| admin | 可查看、创建、删除所有 Lead 的 FollowUp |
| manager | 可查看、创建、删除所有 Lead 的 FollowUp |
| counselor | 只能操作本人负责的 Lead 的 FollowUp（lead.owner_id == current_user.id） |

无权限时返回：
```json
{
  "success": false,
  "error_code": "FORBIDDEN",
  "message": "无权限访问该线索"
}
```

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
    "name": "王五",
    "phone": "13700000000",
    "status": "new",
    "intention_level": "medium",
    "owner_id": 1,
    "remark": "FollowUp 测试线索"
  }'
```

### 5.3 新增 FollowUp

```bash
curl -X POST http://localhost:8000/api/v1/leads/<lead_id>/followups \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "followup_type": "phone",
    "content": "电话沟通，客户对AI测试课程感兴趣。",
    "intention_level": "high",
    "next_followup_at": "2026-07-03 10:00:00"
  }'
```

预期响应：
```json
{
  "success": true,
  "data": {"id": 1},
  "message": "跟进记录已保存"
}
```

### 5.4 查询 FollowUp

```bash
curl http://localhost:8000/api/v1/leads/<lead_id>/followups \
  -H "Authorization: Bearer <token>"
```

预期响应：返回刚新增的跟进记录数组。

### 5.5 删除 FollowUp

```bash
curl -X DELETE http://localhost:8000/api/v1/followups/<followup_id> \
  -H "Authorization: Bearer <token>"
```

预期响应：
```json
{
  "success": true,
  "data": null,
  "message": "跟进记录已删除"
}
```

### 5.6 再次查询确认软删除

```bash
curl http://localhost:8000/api/v1/leads/<lead_id>/followups \
  -H "Authorization: Bearer <token>"
```

预期响应：已删除记录不再出现在列表中。

### 5.7 不存在 Lead 的 FollowUp 操作

```bash
curl http://localhost:8000/api/v1/leads/999999/followups \
  -H "Authorization: Bearer <token>"
```

预期响应：
```json
{
  "success": false,
  "error_code": "LEAD_NOT_FOUND",
  "message": "线索不存在"
}
```

---

## 6. 自测结果

### 6.1 启动服务

```
docker compose up --build
```
backend 和 frontend 均正常启动。

### 6.2 登录成功

返回 token 和用户信息。

### 6.3 创建 Lead 成功

返回 `{"success": true, "data": {"id": N}, "message": "线索创建成功"}`。

### 6.4 新增 FollowUp 成功

返回 `{"success": true, "data": {"id": 1}, "message": "跟进记录已保存"}`。

### 6.5 查询 FollowUp 成功

返回包含跟进记录的数组，字段完整。

### 6.6 删除 FollowUp 成功

返回 `{"success": true, "data": null, "message": "跟进记录已删除"}`。

### 6.7 再次查询确认软删除

已删除记录不再出现在查询结果中。

### 6.8 不存在 Lead 测试

返回 `{"success": false, "error_code": "LEAD_NOT_FOUND", "message": "线索不存在"}`。

---

## 7. 已知问题

无。

---

## 8. 下一步建议

Coding Step 4：Resume Import / LeadDraft。

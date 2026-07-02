# Coding Step 5：Dashboard / Config 开发报告

**版本：** v0.1 MVP  
**完成日期：** 2026-07-02  
**状态：** PASS

---

## 1. 本次修改文件

### 新增文件（9 files）

| 文件 | 说明 |
|---|---|
| `backend/app/models/lead_source.py` | LeadSource 线索来源模型 |
| `backend/app/models/course.py` | Course 课程模型 |
| `backend/app/models/system_setting.py` | SystemSetting 系统配置模型 |
| `backend/app/schemas/config.py` | LeadSourceResponse / CourseResponse / SystemSettingResponse Schema |
| `backend/app/schemas/dashboard.py` | DashboardSummaryResponse / TodayFollowUpItem / RecentLeadItem Schema |
| `backend/app/services/config_service.py` | 配置查询服务 + 默认数据初始化 |
| `backend/app/services/dashboard_service.py` | Dashboard 统计 / 今日待跟进 / 最近新增线索服务 |
| `backend/app/routers/config.py` | Config API 路由 |
| `backend/app/routers/dashboard.py` | Dashboard API 路由 |

### 修改文件（2 files）

| 文件 | 变更说明 |
|---|---|
| `backend/app/models/__init__.py` | 新增 Course、LeadSource、SystemSetting 引用 |
| `backend/app/main.py` | 注册 config、dashboard 路由；启动时调用 `init_default_configs` |

---

## 2. 本次实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/config/lead-sources` | 查询活跃线索来源列表 |
| GET | `/api/v1/config/courses` | 查询活跃课程列表 |
| GET | `/api/v1/config/system-settings` | 查询系统配置（仅 admin） |
| GET | `/api/v1/dashboard/summary` | Dashboard 首页统计摘要 |
| GET | `/api/v1/dashboard/today-followups` | 今日及逾期待跟进列表 |
| GET | `/api/v1/dashboard/recent-leads` | 最近新增线索列表 |

---

## 3. 数据库变化

### 新增表

**lead_sources 表** — 线索来源配置表

字段：id, name, description, is_active, created_at, updated_at

默认数据（5条）：手工录入、简历上传、微信、官网、其他

**courses 表** — 课程配置表

字段：id, name, description, is_active, created_at, updated_at

默认数据（3条）：AI智能应用开发工程师、AI测试开发工程师、待确认

**system_settings 表** — 系统配置表

字段：id, setting_key, setting_value, description, created_at, updated_at

默认数据（3条）：
- `resume_temp_retention_enabled` = "false"
- `resume_temp_retention_days` = "0"
- `default_llm_enabled` = "false"

### 默认数据初始化逻辑

- 应用启动时在 `lifespan` 中调用 `init_default_configs(db)`
- 每个表检查 `count() == 0`，仅在表为空时插入默认数据
- 可重复执行（幂等），重启不会产生重复数据
- 不影响已有数据

### 未修改表结构

- `users` 表结构未修改
- `leads` 表结构未修改
- `lead_followups` 表结构未修改
- `import_logs` 表结构未修改
- `lead_drafts` 表结构未修改

---

## 4. Dashboard 统计规则

### total_leads（总潜在客户数）

```
COUNT(leads) WHERE deleted_at IS NULL
```

### today_new_leads（今日新增线索）

```
COUNT(leads) WHERE created_at LIKE 'YYYY-MM-DD%' AND deleted_at IS NULL
```

### pending_followups（待跟进数）

```
COUNT(DISTINCT lead_id) FROM lead_followups
JOIN leads ON lead_followups.lead_id = leads.id
WHERE lead_followups.deleted_at IS NULL
  AND lead_followups.next_followup_at IS NOT NULL
  AND lead_followups.next_followup_at <= 'YYYY-MM-DD 23:59:59'
  AND leads.deleted_at IS NULL
```

统计存在未删除 followup 且 `next_followup_at <= 今天结束` 的去重 Lead 数量。

### enrolled_leads（已注册线索）

```
COUNT(leads) WHERE status = 'enrolled' AND deleted_at IS NULL
```

### 今日待跟进

- 返回 lead_followups 中 `next_followup_at <= 今天结束` 且未删除的记录
- JOIN leads 获取名称、电话等信息
- 按 `next_followup_at` 升序排列
- 最多返回 20 条

### 最近新增线索

- 返回 `deleted_at IS NULL` 的 Lead
- 按 `created_at DESC` 排序
- 最多返回 10 条

---

## 5. 权限规则

### Config API 权限

| 接口 | admin | manager | counselor |
|---|---|---|---|
| GET /api/v1/config/lead-sources | ✅ | ✅ | ✅ |
| GET /api/v1/config/courses | ✅ | ✅ | ✅ |
| GET /api/v1/config/system-settings | ✅ | ❌ | ❌ |

非 admin 访问 system-settings 返回：

```json
{
  "success": false,
  "error_code": "FORBIDDEN",
  "message": "无权限访问系统配置"
}
```

### Dashboard API 权限

| 角色 | 可见数据范围 |
|---|---|
| admin | 全部 Lead 统计 |
| manager | v0.1 暂查看全部 Lead 统计 |
| counselor | 仅统计 `owner_id = 当前用户ID` 的 Lead |

---

## 6. 自测命令

### 6.1 登录获取 token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 6.2 查询线索来源

```bash
curl http://localhost:8000/api/v1/config/lead-sources \
  -H "Authorization: Bearer <token>"
```

### 6.3 查询课程

```bash
curl http://localhost:8000/api/v1/config/courses \
  -H "Authorization: Bearer <token>"
```

### 6.4 admin 查询系统配置

```bash
curl http://localhost:8000/api/v1/config/system-settings \
  -H "Authorization: Bearer <token>"
```

### 6.5 查询 Dashboard Summary

```bash
curl http://localhost:8000/api/v1/dashboard/summary \
  -H "Authorization: Bearer <token>"
```

### 6.6 查询今日待跟进

```bash
curl http://localhost:8000/api/v1/dashboard/today-followups \
  -H "Authorization: Bearer <token>"
```

### 6.7 查询最近新增线索

```bash
curl http://localhost:8000/api/v1/dashboard/recent-leads \
  -H "Authorization: Bearer <token>"
```

### 6.8 非 admin 查询 system-settings（拒绝验证）

```bash
# 使用 counselor 用户登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"counselor1","password":"test123"}'

# 访问 system-settings
curl http://localhost:8000/api/v1/config/system-settings \
  -H "Authorization: Bearer <counselor_token>"
```

---

## 7. 自测结果

### 7.1 查询线索来源 — PASS ✅

返回 5 条数据：手工录入、简历上传、微信、官网、其他

```json
{
  "success": true,
  "data": [
    {"id": 1, "name": "手工录入", "description": "手动创建线索", "is_active": 1},
    {"id": 2, "name": "简历上传", "description": "简历文件导入", "is_active": 1},
    {"id": 3, "name": "微信", "description": "微信渠道", "is_active": 1},
    {"id": 4, "name": "官网", "description": "官方网站", "is_active": 1},
    {"id": 5, "name": "其他", "description": "其他渠道", "is_active": 1}
  ],
  "message": "ok"
}
```

### 7.2 查询课程 — PASS ✅

返回 3 条数据：AI智能应用开发工程师、AI测试开发工程师、待确认

```json
{
  "success": true,
  "data": [
    {"id": 1, "name": "AI智能应用开发工程师", ...},
    {"id": 2, "name": "AI测试开发工程师", ...},
    {"id": 3, "name": "待确认", ...}
  ],
  "message": "ok"
}
```

### 7.3 admin 查询系统配置 — PASS ✅

返回 3 条数据：resume_temp_retention_enabled、resume_temp_retention_days、default_llm_enabled

```json
{
  "success": true,
  "data": [
    {"id": 1, "setting_key": "resume_temp_retention_enabled", "setting_value": "false", ...},
    {"id": 2, "setting_key": "resume_temp_retention_days", "setting_value": "0", ...},
    {"id": 3, "setting_key": "default_llm_enabled", "setting_value": "false", ...}
  ],
  "message": "ok"
}
```

### 7.4 Dashboard Summary — PASS ✅

```json
{
  "success": true,
  "data": {
    "total_leads": 7,
    "today_new_leads": 7,
    "pending_followups": 0,
    "enrolled_leads": 0
  },
  "message": "ok"
}
```

数值根据实际数据库数据动态变化。

### 7.5 今日待跟进 — PASS ✅

返回空数组 `[]`（当前无待跟进数据）。

### 7.6 最近新增线索 — PASS ✅

返回 7 条最近 Lead（当前数据库共 7 条），最多 10 条。

### 7.7 非 admin 查询 system-settings — PASS ✅

```json
{
  "success": false,
  "error_code": "FORBIDDEN",
  "message": "无权限访问系统配置"
}
```

### 7.8 幂等性验证 — PASS ✅

重启 backend 后，默认数据不重复：
- lead_sources 仍为 5 条
- courses 仍为 3 条
- system_settings 仍为 3 条

### 7.9 已有模块不受影响 — PASS ✅

- Auth 模块正常
- Lead 模块正常
- FollowUp 模块正常
- Resume Import / LeadDraft 模块正常

---

## 8. 已知问题

无。

---

## 9. 下一步建议

Coding Step 6：Frontend Basic Integration — 实现前端基础集成，对接 Dashboard 和 Config API。

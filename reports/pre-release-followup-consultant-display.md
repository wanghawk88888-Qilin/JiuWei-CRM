# Pre-Release P1 Fix Report：跟进记录显示咨询师姓名

**日期**: 2026-07-02  
**版本**: v0.1.0 发布前收口  
**修复类型**: P1 小修  

---

## 一、问题描述

`lead_followups.created_by` 字段已记录跟进人 user_id，但前端页面未展示对应咨询师姓名，导致：

- 线索详情中无法判断是谁跟进过客户
- 线索列表中无法快速看到最近一次跟进人
- 多咨询师协作时责任不清晰

---

## 二、修复方案

### 2.1 后端

- **FollowUp 查询接口** (`GET /api/v1/leads/{lead_id}/followups`)：LEFT JOIN `users` 表，新增 `created_by_name` 字段
- **Lead 列表接口** (`GET /api/v1/leads`)：子查询批量获取每个线索的最新跟进记录及跟进人姓名，新增 `last_followup_by`、`last_followup_by_name` 字段

### 2.2 前端

- **线索详情页**（跟进时间轴）：每条跟进记录新增"跟进人：{created_by_name}"
- **线索列表页**（表格）：新增"最近跟进人"、"最近跟进时间"、"下次跟进时间"三列

---

## 三、修改文件

| 序号 | 文件 | 修改内容 |
|------|------|----------|
| 1 | `backend/app/schemas/followup.py` | `FollowUpResponse` 新增 `created_by_name: str` 字段 |
| 2 | `backend/app/schemas/lead.py` | `LeadListItem` 新增 `last_followup_by`、`last_followup_by_name` 字段 |
| 3 | `backend/app/services/followup_service.py` | `list_followups_by_lead()` 改为 LEFT JOIN `users` 表，返回包含 `created_by_name` 的字典列表 |
| 4 | `backend/app/services/lead_service.py` | 新增 `_enrich_lead_items_with_followup()` 函数，批量查询最新跟进记录及用户姓名，附加到 Lead 对象 |
| 5 | `backend/app/routers/followups.py` | 列表接口适配新的字典返回格式 |
| 6 | `frontend/types/index.ts` | `FollowUpItem` 新增 `created_by_name`；`LeadListItem` 新增 `last_followup_by`、`last_followup_by_name` |
| 7 | `frontend/app/leads/[id]/page.tsx` | 跟进时间轴每条记录新增"跟进人"显示 |
| 8 | `frontend/app/leads/page.tsx` | 表格新增"最近跟进人"、"最近跟进时间"、"下次跟进时间"三列 |

---

## 四、后端返回字段变化

### 4.1 FollowUp 查询接口

**接口**: `GET /api/v1/leads/{lead_id}/followups`

**新增字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `created_by_name` | `string` | 跟进人真实姓名，来源 `users.real_name`；用户不存在时返回 `"未知用户"` |

**示例响应**:
```json
{
  "id": 8,
  "lead_id": 18,
  "followup_type": "phone",
  "content": "...",
  "intention_level": "medium",
  "next_followup_at": "2026-07-06T09:00:00",
  "created_by": 1,
  "created_by_name": "系统管理员",
  "created_at": "2026-07-02 19:02:14",
  "updated_at": "2026-07-02 19:02:14"
}
```

### 4.2 Lead 列表接口

**接口**: `GET /api/v1/leads`

**新增字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `last_followup_by` | `int \| null` | 最近一条跟进记录的 `created_by` |
| `last_followup_by_name` | `string \| null` | 对应 `users.real_name`；无跟进记录时为 `null` |

**无跟进记录时**:
```json
{
  "last_followup_by": null,
  "last_followup_by_name": null,
  "last_followup_at": null,
  "next_followup_at": null
}
```

---

## 五、前端展示变化

### 5.1 线索详情页 — 跟进时间轴

每条跟进记录新增显示：

```text
跟进人：系统管理员
跟进方式：电话
跟进时间：2026-07-02 19:02:14
下次跟进：2026-07-06 09:00
意向：中
内容：跟进人展示测试
```

### 5.2 线索列表页 — 表格

新增三列：**最近跟进人**、**最近跟进时间**、**下次跟进时间**

无跟进记录时显示 `-`。

---

## 六、浏览器验证结果

| 验证项 | 结果 | 说明 |
|--------|------|------|
| 线索详情显示跟进人 | ✅ 通过 | 显示"跟进人：系统管理员" |
| 线索列表显示最近跟进人 | ✅ 通过 | 显示"最近跟进人：系统管理员" |
| 线索列表显示最近跟进时间 | ✅ 通过 | 显示跟进记录创建时间 |
| 线索列表显示下次跟进时间 | ✅ 通过 | 显示最近跟进的下次跟进时间 |
| 无跟进记录时显示 `-` | ✅ 通过 | null 值正确渲染为 `-` |

---

## 七、API 验证结果

| 接口 | 验证项 | 结果 |
|------|--------|------|
| `GET /api/v1/leads` | 返回 `last_followup_by` | ✅ 通过 |
| `GET /api/v1/leads` | 返回 `last_followup_by_name` | ✅ 通过 |
| `GET /api/v1/leads` | 返回 `last_followup_at` | ✅ 通过 |
| `GET /api/v1/leads` | 返回 `next_followup_at` | ✅ 通过 |
| `GET /api/v1/leads/{id}/followups` | 返回 `created_by_name` | ✅ 通过 |
| `GET /api/v1/leads/{id}/followups` | 无跟进记录时正常 | ✅ 通过 |
| 无跟进记录 lead | 各字段为 `null` | ✅ 通过 |

---

## 八、权限影响评估

- **未改变权限逻辑**：`_check_lead_access` 函数未修改
- counselor 仍只能看到本人负责的 Lead 及其 FollowUp
- admin / manager 数据范围不变

---

## 九、是否影响现有功能

| 影响项 | 评估 |
|--------|------|
| 数据库表结构 | ❌ 未修改 |
| Auth | ❌ 未修改 |
| User Management | ❌ 未修改 |
| Resume Import | ❌ 未修改 |
| LeadDraft | ❌ 未修改 |
| Dashboard 统计规则 | ❌ 未修改 |
| Docker 配置 | ❌ 未修改 |
| docs 目录 | ❌ 未修改 |
| 已有 API 响应字段 | ❌ 仅新增字段，未删除或修改已有字段 |

---

## 十、结论

本次 P1 修复在两个关键位置（线索详情跟进时间轴 + 线索列表页）补充了跟进咨询师姓名的展示，后端通过 JOIN `users` 表直接返回姓名，前端无需额外查询。所有新增字段均为兼容性增加，不影响现有功能。

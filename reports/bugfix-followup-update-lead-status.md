# Bugfix: FollowUp 创建后 Lead 状态未更新

## 问题描述

在 Lead 详情页新增 FollowUp 后，FollowUp 保存成功，但 Lead 状态仍显示为"新线索"（`new`），未自动更新为"跟进中"（`following`）。

### 影响范围

- Lead 详情页顶部状态
- Lead 列表状态
- Dashboard 统计
- 招生老师对客户阶段的判断

### 缺陷级别

P1

---

## 根因分析

`backend/app/services/followup_service.py` 的 `create_followup` 函数在创建 FollowUp 时，只同步了 Lead 的 `updated_at` 和 `intention_level`（可选），**缺少对 Lead `status` 的自动转换逻辑**。

```python
# 修复前 (第 51-56 行)
lead = db.query(Lead).filter(Lead.id == lead_id, Lead.deleted_at.is_(None)).first()
if lead:
    lead.updated_at = now
    if followup_data.get("intention_level") is not None:
        lead.intention_level = followup_data["intention_level"]
```

`lead.status == "new"` → `"following"` 的状态转换规则未被实现。

---

## 修复方案

在 `create_followup` 函数中增加一条规则：若 Lead 当前状态为 `new`，则自动更新为 `following`。

```python
# 修复后 (第 51-60 行)
lead = db.query(Lead).filter(Lead.id == lead_id, Lead.deleted_at.is_(None)).first()
if lead:
    lead.updated_at = now
    # Rule 1: auto-transition "new" → "following" on first follow-up
    if lead.status == "new":
        lead.status = "following"
    # Rule 2: sync intention_level if provided
    if followup_data.get("intention_level") is not None:
        lead.intention_level = followup_data["intention_level"]
```

### 三条规则对照

| 规则 | 描述 | 状态 |
|------|------|------|
| 规则1 | `new` → `following` 自动转换 | ✅ 新增 |
| 规则2 | `intention_level` 同步更新 | ✅ 已有 |
| 规则3 | `updated_at` 始终更新 | ✅ 已有 |

---

## 修改文件

| 文件 | 修改内容 | 行数 |
|------|---------|------|
| `backend/app/services/followup_service.py` | 新增 `new` → `following` 状态转换逻辑；更新 docstring | +3 行 |

**未修改的文件：**
- `backend/app/routers/followups.py` — 无需修改
- 数据库表结构 — 未修改
- API 路径 — 未修改
- 前端页面结构 — 未修改
- FollowUp 返回格式 — 未修改
- Lead 状态枚举 — 未修改

---

## 验证结果

### 主流程验证

| 步骤 | 操作 | 预期 | 实际 | 结果 |
|------|------|------|------|------|
| 1 | `POST /api/v1/leads` 创建 Lead | `status: "new"` | `status: "new"` | ✅ |
| 2 | `POST /api/v1/leads/{id}/followups` 创建 FollowUp（含 `intention_level: "high"`） | FollowUp 创建成功 | `id: 7`, success | ✅ |
| 3 | `GET /api/v1/leads/{id}` 查详情 | `status: "following"`, `intention_level: "high"` | `status: "following"`, `intention_level: "high"` | ✅ |
| 4 | `GET /api/v1/leads` 查列表 | Lead 在列表中显示 `following` | `status: "following"` | ✅ |

### 回归验证

| 模块 | 操作 | 结果 |
|------|------|------|
| FollowUp 新增 | `POST /api/v1/leads/{id}/followups` | ✅ 正常 |
| FollowUp 查询 | `GET /api/v1/leads/{id}/followups` | ✅ 正常 |
| FollowUp 删除 | `DELETE /api/v1/followups/{id}` | ✅ 正常 |
| Lead 更新 | `PUT /api/v1/leads/{id}` | ✅ 正常 |
| Lead 列表 | `GET /api/v1/leads` | ✅ 正常 |
| Dashboard Summary | `GET /api/v1/dashboard/summary` | ✅ 正常 |

---

## 结论

修复完成后，所有功能正常运行，不影响已有模块。Lead 在创建第一条 FollowUp 后，状态会从 `new` 自动变为 `following`，`intention_level` 和 `updated_at` 也会同步更新。

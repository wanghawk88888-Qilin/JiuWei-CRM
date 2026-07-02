# Step P1: Lead 转报名（业务闭环）

## 概述

新增"标记为已报名"功能，实现 Lead 生命周期从 `new/following/high_intent` 到 `enrolled` 的业务闭环。

## 修改文件

### 前端（仅 1 个文件）

| 文件 | 修改内容 |
|------|---------|
| `frontend/app/leads/[id]/page.tsx` | 新增"标记为已报名"按钮及处理逻辑 |

### 后端

**无修改。** 后端已完全支持该功能：

- `PUT /api/v1/leads/{id}` 已支持 `status` 字段的部分更新
- `VALID_LEAD_STATUSES` 已包含 `"enrolled"`
- `update_lead()` 已自动更新 `updated_at`

## 实现方式

### 1. 新增状态变量

```tsx
const [enrolling, setEnrolling] = useState(false);
```

### 2. 新增处理函数 `handleEnroll`

- 弹出确认对话框
- 调用 `leadApi.update(leadId, { status: "enrolled" })`
- 成功后刷新 Lead Detail 数据（Badge 立即变为绿色"已报名"）
- 成功/失败均显示 Toast 提示

### 3. 新增绿色按钮

- 位置：Lead Detail 页头右侧，与"上传简历"按钮并列
- 颜色：绿色 (`bg-green-600`)
- 隐藏条件：`lead.status === "enrolled"` 时自动隐藏
- 加载态：`enrolling` 时显示 spinner

## 验证过程

### ① 新建 Lead
- 创建新线索，默认 status=`new`

### ② 进入 Detail
- 点击线索进入详情页
- 页面头显示蓝色"新线索"Badge
- 右侧显示绿色"标记为已报名"按钮

### ③ 点击"标记为已报名"
- 弹出确认对话框 → 确认
- API 调用 `PUT /api/v1/leads/{id}` with `{status: "enrolled"}`
- 成功 Toast："已标记为已报名"

### ④ Detail 显示已报名
- Badge 立即变为绿色"已报名"
- "标记为已报名"按钮自动隐藏

### ⑤ 返回 List 显示已报名
- 列表页状态列显示绿色"已报名"Badge（`statusBadgeVariant` 已支持 enrolled → green）

### ⑥ Dashboard Enrolled 数量 +1
- Dashboard 的"已报名"统计卡显示更新后的数量（后端 `dashboard_service` 实时查询 `status='enrolled'` 计数）

### ⑦ FollowUp 不受影响
- 跟进记录功能无任何代码变更
- 已报名线索仍可正常添加/查看跟进记录

## 影响范围

- **前端**：仅 `LeadDetailPage` 组件，1 个文件，约 20 行新增代码
- **后端**：无修改
- **数据库**：无修改
- **其他页面**：Lead List、Dashboard 自动联动，无需额外修改（均已使用 `statusBadgeVariant` 和 `STATUS_LABELS`）

## 技术要点

- 复用已有 `PUT /api/v1/leads/{id}` 接口，仅传 `{status: "enrolled"}`（最小更新）
- `updated_at` 由后端 `lead_service.update_lead()` 自动更新
- 按钮在 `status === "enrolled"` 时通过条件渲染隐藏
- TypeScript 编译通过，无类型错误

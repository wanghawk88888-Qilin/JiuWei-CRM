# Coding Step 6：Frontend Basic Integration 开发报告

**版本：** v0.1 MVP  
**完成日期：** 2026-07-02  
**状态：** PASS

---

## 1. 本次修改文件

### 新增文件（14 files）

| 文件 | 说明 |
|---|---|
| `frontend/types/index.ts` | 统一 TypeScript 类型定义（与 backend schema 一致） |
| `frontend/lib/api.ts` | 统一 API 客户端（fetch + JWT + 错误处理 + BaseURL） |
| `frontend/components/Button.tsx` | 通用按钮组件（4 variants × 3 sizes + loading） |
| `frontend/components/Card.tsx` | 通用卡片容器组件 |
| `frontend/components/Input.tsx` | Input / Textarea / Select 表单组件 |
| `frontend/components/Badge.tsx` | 状态/意向标签组件 |
| `frontend/components/Modal.tsx` | 通用弹窗组件 |
| `frontend/components/Toast.tsx` | Toast 通知组件（Provider + Context） |
| `frontend/components/Loading.tsx` | 加载状态组件 |
| `frontend/components/Empty.tsx` | 空状态组件 |
| `frontend/app/login/page.tsx` | 登录页面 |
| `frontend/app/dashboard/page.tsx` | Dashboard 首页 |
| `frontend/app/leads/page.tsx` | 线索列表页 |
| `frontend/app/leads/new/page.tsx` | 新建线索页（含简历上传） |
| `frontend/app/leads/[id]/page.tsx` | 线索详情页（含跟进记录） |

### 修改文件（2 files）

| 文件 | 变更说明 |
|---|---|
| `frontend/app/layout.tsx` | 集成 ToastProvider |
| `frontend/app/page.tsx` | 改为自动跳转（有 token → dashboard，无 → login） |

### 新增配置文件（1 file）

| 文件 | 说明 |
|---|---|
| `frontend/.env.local` | 本地环境变量 `NEXT_PUBLIC_API_BASE_URL` |

---

## 2. 页面完成情况

### 2.1 /login — 登录页 ✅

- JWT 登录表单
- 登录成功：保存 Token 到 localStorage，跳转 /dashboard
- 登录失败：Toast 提示错误信息
- 空输入校验

### 2.2 /dashboard — Dashboard ✅

**四张统计卡：**
- 全部线索（Total Leads）
- 今日新增（Today's Leads）
- 待跟进（Pending FollowUps）
- 已报名（Enrolled）

**今日待跟进表格：**
- 字段：姓名、手机号、状态、下次跟进时间
- 点击行进入线索详情
- 空状态提示

**最近新增线索表格：**
- 字段：姓名、手机号、状态、创建时间
- 点击行进入线索详情
- 空状态提示

**快捷操作：**
- 新建线索按钮
- 上传简历按钮

**退出登录：**
- 清除 localStorage，跳转 /login

### 2.3 /leads — 线索列表 ✅

- keyword 模糊搜索（姓名、手机号、微信）
- status 下拉筛选
- 分页（上一页/下一页）
- 表格字段：姓名、手机号、状态、意向等级、创建时间
- 点击行进入 /leads/[id]
- 空状态：提示新建线索
- 总数/页码显示

### 2.4 /leads/new — 新建线索 ✅

**手工录入：**
- 基本信息：姓名*、手机号、微信、邮箱、性别、年龄
- 教育/职业信息：学历、学校、专业、城市、当前职业
- 业务信息：意向课程、线索来源、状态、意向等级、备注
- 保存成功 → 跳转 /leads
- 保存失败 → Toast

**简历上传：**
- 支持 .docx / .pdf
- 上传 → 解析 → 弹窗显示解析结果
- AI 分析摘要展示
- 确认生成线索 → 调用 lead-draft confirm → 跳转详情
- 继续编辑 → 关闭弹窗，表单保留解析数据

### 2.5 /leads/[id] — 线索详情 ✅

**左侧详情区域：**
- 基本信息：姓名、手机号、微信、邮箱、性别、年龄
- 教育/职业信息：学历、学校、专业、城市、当前职业、工作年限、最近公司、最近岗位
- 业务信息：意向课程、线索来源、意向等级、状态、创建时间、更新时间、备注、AI 摘要
- 上传简历按钮（复用简历导入流程）

**右侧跟进记录：**
- 新增跟进表单：跟进方式、跟进内容*、客户意向、下次跟进时间
- 跟进时间轴：显示全部跟进记录
- 每条记录：类型标签、内容、意向、下次跟进时间、创建时间
- 删除按钮：确认后删除

---

## 3. API 对接情况

| 接口 | 方法 | 前端调用位置 | 状态 |
|---|---|---|---|
| `/api/v1/auth/login` | POST | login/page.tsx | ✅ |
| `/api/v1/auth/me` | GET | lib/api.ts (已封装) | ✅ |
| `/api/v1/dashboard/summary` | GET | dashboard/page.tsx | ✅ |
| `/api/v1/dashboard/today-followups` | GET | dashboard/page.tsx | ✅ |
| `/api/v1/dashboard/recent-leads` | GET | dashboard/page.tsx | ✅ |
| `/api/v1/leads` | GET | leads/page.tsx | ✅ |
| `/api/v1/leads` | POST | leads/new/page.tsx | ✅ |
| `/api/v1/leads/{id}` | GET | leads/[id]/page.tsx | ✅ |
| `/api/v1/leads/{id}/followups` | GET | leads/[id]/page.tsx | ✅ |
| `/api/v1/leads/{id}/followups` | POST | leads/[id]/page.tsx | ✅ |
| `/api/v1/followups/{id}` | DELETE | leads/[id]/page.tsx | ✅ |
| `/api/v1/resume-imports` | POST | leads/new/page.tsx, leads/[id]/page.tsx | ✅ |
| `/api/v1/lead-drafts/{id}` | GET | leads/new/page.tsx | ✅ |
| `/api/v1/lead-drafts/{id}/confirm` | POST | leads/new/page.tsx, leads/[id]/page.tsx | ✅ |
| `/api/v1/config/lead-sources` | GET | leads/new/page.tsx, leads/[id]/page.tsx | ✅ |
| `/api/v1/config/courses` | GET | leads/new/page.tsx, leads/[id]/page.tsx | ✅ |

**共 16 个接口，全部对接完成。**

---

## 4. 统一 API 封装

`frontend/lib/api.ts` 核心特性：

- 统一 `BaseURL` 配置（`NEXT_PUBLIC_API_BASE_URL`）
- 自动携带 JWT Token（`Authorization: Bearer`）
- 401 自动清除 Token 并跳转登录页
- 统一错误处理（`ApiError` class）
- 统一响应解析（`ApiResponse<T>` envelope）
- FormData 上传不设置 Content-Type（让浏览器自动设置 boundary）
- 按模块分组：`authApi` / `leadApi` / `followUpApi` / `resumeImportApi` / `leadDraftApi` / `dashboardApi` / `configApi`

---

## 5. 统一类型

`frontend/types/index.ts` 包括：

- `ApiResponse<T>` — 通用响应信封
- Auth: `LoginRequest`, `LoginResponseData`, `CurrentUser`
- Lead: `LeadCreate`, `LeadUpdate`, `LeadListItem`, `LeadDetail`, `LeadListData`
- FollowUp: `FollowUpCreate`, `FollowUpItem`
- Dashboard: `DashboardSummary`, `TodayFollowUpItem`, `RecentLeadItem`
- Resume: `ResumeImportResult`
- LeadDraft: `LeadDraft`, `LeadDraftConfirm`
- Config: `LeadSource`, `Course`
- Constants: `LEAD_STATUSES`, `INTENTION_LEVELS`, `FOLLOWUP_TYPES`
- Labels: `STATUS_LABELS`, `INTENTION_LABELS`, `FOLLOWUP_TYPE_LABELS`, `GENDER_LABELS`

---

## 6. 统一组件

| 组件 | 文件 | 说明 |
|---|---|---|
| Button | `components/Button.tsx` | 4 variants (primary/secondary/danger/ghost) × 3 sizes (sm/md/lg) + loading |
| Card | `components/Card.tsx` | 4 padding presets |
| Input | `components/Input.tsx` | Input + Textarea + Select，带 label/error |
| Badge | `components/Badge.tsx` | 7 colors + status/intention helpers |
| Modal | `components/Modal.tsx` | 3 sizes + ESC close + overlay click close |
| Toast | `components/Toast.tsx` | Context + Provider + 3 types + auto-dismiss |
| Loading | `components/Loading.tsx` | spinner + 可选 fullPage |
| Empty | `components/Empty.tsx` | icon + title + description + action slot |

---

## 7. 异常处理

所有 API 调用通过 `lib/api.ts` 统一处理：

- **401** `UNAUTHORIZED` — 清除 Token，跳转 /login
- **403** `FORBIDDEN` — Toast 提示"无权限"
- **404** `*_NOT_FOUND` — 页面跳转或 Toast 提示
- **422/400** `VALIDATION_ERROR` — Toast 提示具体错误
- **500** `INTERNAL_ERROR` — Toast 提示"服务器错误"
- **网络错误** `NETWORK_ERROR` — Toast 提示"网络连接失败"

---

## 8. 联调结果

### 8.1 自动化验证（全部通过 ✅）

| # | 场景 | 结果 |
|---|---|---|
| ① | 登录 | ✅ Token 获取成功 |
| ② | Dashboard Summary | ✅ 返回统计数据 |
| ③ | Today Followups | ✅ 返回待跟进列表 |
| ④ | Recent Leads | ✅ 返回最近线索 |
| ⑤ | 新建 Lead | ✅ 创建成功 (lead_id=12) |
| ⑥ | Lead 列表 | ✅ 分页 + 搜索正常 |
| ⑦ | Lead 详情 | ✅ 完整字段返回 |
| ⑧ | 新增 FollowUp | ✅ 创建成功 (followup_id=3) |
| ⑨ | 查询 FollowUps | ✅ 返回跟进列表 |
| ⑩ | 删除 FollowUp | ✅ 删除成功 |
| ⑪ | 上传 docx | ✅ 解析成功 (draft_id=6) |
| ⑫ | 获取 LeadDraft | ✅ 草稿字段完整 |
| ⑬ | Confirm LeadDraft | ✅ 生成正式线索 (lead_id=13) |

### 8.2 页面渲染验证（全部通过 ✅）

| 页面 | URL | 状态 |
|---|---|---|
| 登录页 | `/login` | ✅ 正常渲染 |
| Dashboard | `/dashboard` | ✅ 正常渲染 |
| 线索列表 | `/leads` | ✅ 正常渲染 |
| 新建线索 | `/leads/new` | ✅ 正常渲染 |
| 线索详情 | `/leads/[id]` | ✅ 正常渲染 |

---

## 9. 已知问题

1. **AI 增强识别未启用** — 简历解析使用规则提取，解析出的 `name` 字段可能带 "姓名：" 前缀。大模型增强识别（`default_llm_enabled` 配置项为 false）默认关闭，需要时管理员在系统设置中启用。
2. **编辑线索** — 详情页暂未实现编辑功能（`PUT /leads/{id}` 已在 API 中封装，后续迭代可增加编辑按钮）。
3. **短信/微信通知** — v0.1 不实现。

---

## 10. 下一步建议

- **Step 7：编辑与优化** — 增加线索编辑功能、完善详情页 UI
- **Step 8：部署配置** — Docker 部署、nginx 配置、生产环境优化
- **Step 9：v1.0 发布准备** — 测试覆盖、文档补充、发布检查清单

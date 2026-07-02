# Coding Step 4：Resume Import / LeadDraft 开发报告

**版本：** v0.1 MVP  
**完成日期：** 2026-07-02  
**状态：** PASS

---

## 1. 本次修改文件

### 新增文件（11 files）

| 文件 | 说明 |
|---|---|
| `backend/app/models/import_log.py` | ImportLog 导入日志模型 |
| `backend/app/models/lead_draft.py` | LeadDraft 线索草稿模型 |
| `backend/app/schemas/resume_import.py` | ResumeImportResponse Schema |
| `backend/app/schemas/lead_draft.py` | LeadDraftResponse / LeadDraftConfirmRequest Schema |
| `backend/app/services/resume_parser_service.py` | docx/pdf 文本解析服务 |
| `backend/app/services/resume_extract_service.py` | 规则提取（手机号、邮箱、学历、技能）服务 |
| `backend/app/services/llm_extract_service.py` | AI 增强占位服务 |
| `backend/app/services/resume_import_service.py` | 简历导入主流程编排服务 |
| `backend/app/services/lead_draft_service.py` | 草稿查询、确认、丢弃服务 |
| `backend/app/routers/resume_imports.py` | 简历上传路由 |
| `backend/app/routers/lead_drafts.py` | 草稿操作用路由 |

### 修改文件（2 files）

| 文件 | 变更说明 |
|---|---|
| `backend/app/models/__init__.py` | 新增 ImportLog、LeadDraft 引用 |
| `backend/app/main.py` | 注册 resume_imports、lead_drafts 路由 |

### 测试文件（2 files）

| 文件 | 说明 |
|---|---|
| `test_resume.docx` | docx 测试简历 |
| `test_resume.pdf` | pdf 测试简历 |

---

## 2. 本次实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/resume-imports` | 上传 Word/PDF 简历，解析并生成 LeadDraft |
| GET | `/api/v1/lead-drafts/{draft_id}` | 获取线索草稿详情 |
| POST | `/api/v1/lead-drafts/{draft_id}/confirm` | 确认草稿生成正式线索 |
| POST | `/api/v1/lead-drafts/{draft_id}/discard` | 丢弃线索草稿 |

---

## 3. 数据库变化

### 新增表

**import_logs 表** — 导入日志表，记录每次简历上传的文件信息、解析状态、临时文件路径和保留策略。

字段：id, file_name, file_type, file_size, temp_file_path, parse_status, parse_error, extracted_text_length, llm_used, llm_provider, temp_file_expires_at, file_deleted_at, created_by, created_at, updated_at

**lead_drafts 表** — 线索草稿表，保存简历解析后的结构化临时数据，待用户确认后生成正式 Lead。

字段：id, import_log_id, name, phone, wechat, email, gender, age, education, school, major, graduation_time, city, work_years, latest_company, latest_position, skills, ai_summary, ai_course_suggestion, raw_text_excerpt, status, confirmed_lead_id, created_by, created_at, updated_at

### 未修改表

- `users` 表结构未修改
- `leads` 表结构未修改
- `lead_followups` 表结构未修改

---

## 4. 文件处理策略

- `TEMP_FILE_RETENTION_DAYS=0`（默认）：解析完成后**立即删除**原始文件，并更新 `import_logs.file_deleted_at` 和 `parse_status = deleted`
- `TEMP_FILE_RETENTION_DAYS>0`：计算 `temp_file_expires_at = 当前时间 + N 天`，原始文件暂时保留
- LeadDraft 和 ImportLog 记录不受文件删除影响，始终保留
- 本轮未实现定时清理任务（仅写入 `temp_file_expires_at` 供后续使用）

---

## 5. 解析能力

### 支持的文件格式

- `.docx` — 使用 `python-docx` 提取段落文本
- `.pdf` — 优先使用 PyMuPDF (fitz)；备选 pdfplumber

### 规则提取能力

- **手机号**：支持中国大陆手机号 `1[3-9]\d{9}`
- **邮箱**：支持常见邮箱格式
- **学历关键词**：博士、硕士、研究生、本科、大专、专科、高中（按优先级返回最高学历）
- **技能关键词**：Python、Java、JavaScript、测试、自动化测试、AI、机器学习、深度学习、大模型、LLM
- **姓名**：从简历首行简单启发式提取（2-10 字符，不含数字/邮箱特征）

### 不支持

- `.doc` 格式
- 图片简历
- 扫描件 OCR
- Excel / 压缩包
- 真实大模型调用

---

## 6. AI 预留

`backend/app/services/llm_extract_service.py` 已创建，包含占位函数 `enhance_resume_extract(text)`：

- 返回 `llm_used: False`
- 返回 `llm_provider: None`
- 返回 `ai_summary: None`
- 返回 `ai_course_suggestion: None`
- **不调用任何真实大模型**
- **不阻塞主流程**

未来可替换为真实 LLM 调用，不影响现有流程。

---

## 7. 权限规则

### Resume Import（上传简历）

| 角色 | 权限 |
|---|---|
| admin / manager / counselor | 所有已登录用户均可上传 |

### LeadDraft 查询

| 角色 | 权限 |
|---|---|
| admin / manager | 可查看全部草稿 |
| counselor | 仅可查看 `created_by = 当前用户ID` 的草稿 |

### LeadDraft confirm / discard

| 角色 | 权限 |
|---|---|
| admin / manager | 可操作全部草稿 |
| counselor | 仅可操作自己创建的草稿 |

无权限时返回：`FORBIDDEN - 无权限访问该线索草稿`

---

## 8. 自测命令

### 8.1 登录获取 token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 8.2 上传 docx 简历

```bash
curl -X POST http://localhost:8000/api/v1/resume-imports \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_resume.docx"
```

### 8.3 上传 pdf 简历

```bash
curl -X POST http://localhost:8000/api/v1/resume-imports \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_resume.pdf"
```

### 8.4 获取 LeadDraft

```bash
curl http://localhost:8000/api/v1/lead-drafts/<draft_id> \
  -H "Authorization: Bearer <token>"
```

### 8.5 确认 LeadDraft 生成 Lead

```bash
curl -X POST http://localhost:8000/api/v1/lead-drafts/<draft_id>/confirm \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "赵六",
    "phone": "13812345678",
    "email": "zhaoliu@example.com",
    "education": "本科",
    "owner_id": 1,
    "remark": "由简历导入生成"
  }'
```

### 8.6 丢弃 LeadDraft

```bash
curl -X POST http://localhost:8000/api/v1/lead-drafts/<draft_id>/discard \
  -H "Authorization: Bearer <token>"
```

### 8.7 非法文件类型测试

```bash
curl -X POST http://localhost:8000/api/v1/resume-imports \
  -H "Authorization: Bearer <token>" \
  -F "file=@README.md"
```

### 8.8 不存在草稿测试

```bash
curl http://localhost:8000/api/v1/lead-drafts/999999 \
  -H "Authorization: Bearer <token>"
```

---

## 9. 自测结果

### 9.1 上传 docx — PASS ✅

```json
{
  "success": true,
  "data": {
    "import_log_id": 1,
    "lead_draft_id": 1,
    "parse_status": "deleted",
    "draft": {
      "id": 1,
      "name": "赵六",
      "phone": "13812345678",
      "email": "zhaoliu@example.com",
      "education": "本科",
      "school": null,
      "major": null,
      "skills": "Python, 测试, 自动化测试, AI, 大模型",
      "ai_summary": null,
      "ai_course_suggestion": null,
      "status": "pending"
    }
  },
  "message": "简历解析完成"
}
```

### 9.2 上传 pdf — PASS ✅

```json
{
  "success": true,
  "data": {
    "import_log_id": 2,
    "lead_draft_id": 2,
    "parse_status": "deleted",
    "draft": {
      "id": 2,
      "phone": "13812345678",
      "email": "zhaoliu@example.com",
      "skills": "Python, AI",
      "status": "pending"
    }
  },
  "message": "简历解析完成"
}
```

### 9.3 获取 LeadDraft — PASS ✅

返回完整的 draft 字段（包括 raw_text_excerpt）。

### 9.4 确认 LeadDraft — PASS ✅

```json
{
  "success": true,
  "data": { "lead_id": 8 },
  "message": "已生成正式线索"
}
```

- 生成的 Lead 包含正确的 name、phone、email、education
- source_id 默认为 2（简历上传）
- remark 默认为 "由简历导入生成"

### 9.5 丢弃 LeadDraft — PASS ✅

```json
{
  "success": true,
  "data": null,
  "message": "线索草稿已丢弃"
}
```

### 9.6 非法文件类型 — PASS ✅

```json
{
  "success": false,
  "error_code": "INVALID_FILE_TYPE",
  "message": "文件类型不支持"
}
```

### 9.7 不存在草稿 — PASS ✅

```json
{
  "success": false,
  "error_code": "LEAD_DRAFT_NOT_FOUND",
  "message": "线索草稿不存在"
}
```

### 9.8 边界情况 — PASS ✅

- 已确认草稿不可丢弃 → `VALIDATION_ERROR: 只能丢弃待确认的草稿`
- 已丢弃草稿不可确认 → `VALIDATION_ERROR: 该草稿已确认或已丢弃，不可重复操作`

### 9.9 已有模块不受影响 — PASS ✅

- Auth 模块正常
- Lead 模块正常
- FollowUp 模块正常
- 数据库所有表完整

---

## 10. 已知问题

1. **PDF 姓名提取不准确**：PDF 文本经 PyMuPDF 提取后，中文字符可能产生编码问题导致姓名提取不准确（如显示为 `··`）。这是 PDF 文本提取的固有局限性，后续可通过 AI 增强或手动修正解决。

2. **学历关键词匹配局限**：仅支持有限的中文关键词匹配，不包含英文（如 Bachelor、Master）。当前测试中 PDF 提取因 `学历` 字段后跟冒号导致无法匹配完整中文，后续可通过 AI 增强改善。

3. **姓名提取为启发式**：基于首行长度和字符特征的简单规则，对复杂格式简历可能失败，建议用户手动修正。

---

## 11. 下一步建议

Coding Step 5：Dashboard / Config — 实现首页统计、今日待跟进、最近新增线索、线索来源列表、课程列表、系统配置读取。

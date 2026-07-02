# JiuWei CRM 测试计划文档

**版本：** v0.1 MVP
**状态：** Final
**更新时间：** 2026-07-02

---

# 1. 测试目标

Test-v0.1 用于验证 JiuWei CRM MVP 是否满足 PRD、Prototype、Database、API、Development 文档要求。

重点验证：

* 核心业务流程是否可用
* 前后端联调是否正常
* 数据是否正确保存
* 权限是否符合设计
* 简历上传流程是否完整
* AI 服务异常是否不会影响主流程

---

# 2. 测试原则

## 原则1：优先验证主流程

重点验证：

```text
登录
  ↓
创建 Lead
  ↓
查看 Lead
  ↓
新增 FollowUp
  ↓
上传简历
  ↓
生成 LeadDraft
  ↓
确认生成 Lead
```

该流程必须全部通过。

---

## 原则2：先验证业务，再验证界面

优先保证：

* 数据正确
* 流程正确
* 权限正确

页面样式问题可放在后续版本优化。

---

## 原则3：AI 不影响系统可用性

即使：

* 大模型不可用
* AI 返回异常
* AI 超时

系统仍应支持：

* 手工创建 Lead
* 上传简历
* 保存 LeadDraft
* 人工确认生成 Lead

---

# 3. 测试范围

## 包含

* 登录
* Dashboard
* Lead
* FollowUp
* Resume Import
* LeadDraft
* Config
* 权限控制

## 不包含

* 微信
* 企业微信
* 官网 Lead
* AI 销售助手
* 报名
* 缴费
* 班级
* 学习
* 就业

---

# 4. 功能测试

## 4.1 登录

验证：

* 正确用户名密码登录成功
* 错误密码登录失败
* Token 返回正确
* Token 失效处理正确

---

## 4.2 Dashboard

验证：

* 四个统计数据正常显示
* 今日待跟进正确
* 最近新增正确
* 快捷按钮跳转正确

---

## 4.3 Lead

验证：

* 新建 Lead
* 编辑 Lead
* 查看详情
* 删除 Lead（软删除）
* 搜索
* 来源筛选
* 状态筛选

---

## 4.4 FollowUp

验证：

* 新增跟进
* 查询跟进
* 删除跟进
* 时间轴展示

---

## 4.5 Resume Import

验证：

* 上传 Word
* 上传 PDF
* 文件类型校验
* 文本解析
* 手机号规则提取
* 邮箱规则提取
* AI 增强解析（如启用）
* 生成 LeadDraft

---

## 4.6 LeadDraft

验证：

* 查看草稿
* 修改草稿
* 确认生成 Lead
* 丢弃草稿

---

## 4.7 Config

验证：

* 获取线索来源
* 获取课程
* 获取系统配置

---

# 5. API 测试

验证所有 API：

* HTTP 方法正确
* 返回码正确
* JSON 格式正确
* 参数校验正确
* 错误码正确

重点验证：

* 登录
* Lead CRUD
* FollowUp
* Resume Import
* LeadDraft
* Dashboard

---

# 6. 权限测试

验证：

## Admin

应能：

* 查看全部 Lead
* 创建 Lead
* 删除 Lead
* 查看系统配置

---

## Manager

应能：

* 查看团队 Lead
* 创建 Lead
* 修改 Lead

v0.1 可暂按查看全部 Lead 验证。

---

## Counselor

应只能：

* 查看本人 Lead
* 创建本人 Lead
* 修改本人 Lead

不得访问其他老师负责的数据。

---

# 7. 数据验证

重点验证：

Lead 创建后：

* 数据正确写入 leads

新增跟进后：

* 数据正确写入 lead_followups

上传简历后：

* 数据正确写入 lead_drafts

确认后：

* LeadDraft 状态变为 confirmed
* Lead 成功生成

ImportLog：

* 日志生成
* 文件状态正确

---

# 8. 简历处理验证

验证：

默认：

* 解析完成后按配置删除原始文件

管理员配置：

* 保留 1 天
* 保留 3 天
* 保留 7 天
* 保留 15 天

验证：

* 到期自动删除
* Lead 数据不受影响
* ImportLog 保留

---

# 9. AI 容错测试

模拟：

* AI 接口不可用
* AI 超时
* AI 返回异常

验证：

* LeadDraft 正常生成
* 用户可手工修改
* Lead 可正常创建

系统不得崩溃。

---

# 10. 页面测试

验证：

* 登录页
* Dashboard
* Lead List
* Lead Detail
* New Lead
* Settings

检查：

* 页面正常打开
* 无明显布局错误
* 无控制台报错
* 页面跳转正确

---

# 11. 最小验收流程

必须完整执行：

```text
登录
  ↓
创建 Lead
  ↓
查看 Lead
  ↓
新增 FollowUp
  ↓
上传 PDF
  ↓
生成 LeadDraft
  ↓
确认生成 Lead
  ↓
Dashboard 数据更新
```

全部通过后：

v0.1 MVP 验收通过。

---

# 12. 缺陷等级

| 等级 | 说明                           |
| -- | ---------------------------- |
| P0 | 系统无法使用、数据丢失、无法登录             |
| P1 | 核心流程失败（Lead、FollowUp、Resume） |
| P2 | 功能异常但存在替代方案                  |
| P3 | UI、文案、样式问题                   |

原则：

P0、P1 必须修复后才能发布。

---

# 13. v0.1 不测试内容

以下内容不属于本版本：

* 微信通知
* 企业微信
* 官网自动 Lead
* AI 销售助手
* 多模型切换
* 班级
* 学习
* 就业
* 报名
* 缴费

---

# 14. 验收标准

Test-v0.1 完成后，应满足：

* 核心业务流程全部通过。
* API 全部通过。
* 前端页面全部可访问。
* 权限符合设计。
* SQLite 数据正确。
* 简历解析流程正常。
* AI 异常不影响主流程。
* 无 P0、P1 缺陷。
* 满足 PRD、Prototype、Database、API、Development 文档要求。

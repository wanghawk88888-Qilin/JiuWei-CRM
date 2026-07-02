# UI Fix Report: Header Logo 与系统名称调整

**日期**: 2026-07-02  
**范围**: 前端 Header 组件

---

## 修改文件

| # | 文件 | 操作 | 说明 |
|---|---|---|---|
| 1 | `frontend/public/logo-light.png` | 新增 | 从 `logo/logo-light.png` 复制到 public 目录 |
| 2 | `frontend/components/HeaderLogo.tsx` | 新增 | 共享组件：Logo + "CRM系统" 文字 |
| 3 | `frontend/app/layout.tsx` | 修改 | `metadata.title` 改为 "CRM系统" |
| 4 | `frontend/app/dashboard/page.tsx` | 修改 | 替换品牌按钮为 `<HeaderLogo />` |
| 5 | `frontend/app/leads/page.tsx` | 修改 | 替换品牌按钮为 `<HeaderLogo />` |
| 6 | `frontend/app/leads/new/page.tsx` | 修改 | 替换品牌按钮为 `<HeaderLogo />` |
| 7 | `frontend/app/leads/[id]/page.tsx` | 修改 | 替换品牌按钮为 `<HeaderLogo />` |

---

## Logo 文件处理方式

- 源文件: `logo/logo-light.png` (1.6 MB)
- 目标位置: `frontend/public/logo-light.png`
- 页面引用: `/logo-light.png`（public 目录下的静态资源）
- 未使用外链，未生成新图片

---

## 共享组件

创建 `frontend/components/HeaderLogo.tsx`：

- 类型: Client Component (`"use client"`)
- 包含: `<img>` + `<span>CRM系统</span>` 包裹在 `<button>` 中
- 点击行为: 跳转到 `/dashboard`
- 样式: `flex items-center gap-3`, Logo 32x32px, 文字 `text-lg font-bold`
- 4 个页面共用同一组件，避免重复代码

---

## 页面验证结果

### Next.js 构建

```
✓ npm run build — 编译通过，无错误
```

所有路由编译成功:

| 路由 | 大小 | 状态 |
|---|---|---|
| `/dashboard` | 5.09 kB | ✓ |
| `/leads` | 5.06 kB | ✓ |
| `/leads/[id]` | 4.04 kB | ✓ |
| `/leads/new` | 3.2 kB | ✓ |
| `/login` | 3.3 kB | ✓ |

### Docker

Docker daemon 未运行，无法验证 `docker compose up --build`。代码变更不涉及 Dockerfile 或 docker-compose.yml 修改，预期不影响容器启动。

---

## 是否影响其他功能

- **右侧导航**: 未修改
- **Dashboard 数据**: 未修改
- **Lead 页面功能**: 未修改
- **FollowUp 功能**: 未修改
- **Resume Import 功能**: 未修改
- **API 封装**: 未修改
- **后端代码**: 未修改
- **docs 目录**: 未修改
- **docker-compose.yml**: 未修改

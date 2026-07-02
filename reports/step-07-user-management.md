# Step 7: User Management — Report

## 概述

完成 JiuWei CRM V0.1 最后一项能力：用户管理。支持 Admin 进行用户 CRUD、启用/禁用、重置密码，以及所有用户自助修改密码。

## 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/schemas/user.py` | Pydantic schemas: UserCreate, UserUpdate, UserResponse, ChangePasswordRequest |
| `backend/app/services/user_service.py` | Business logic: list_users, create_user, update_user, reset_password, change_password |
| `backend/app/routers/users.py` | API endpoints (5 routes) |
| `frontend/components/TopNav.tsx` | Reusable top navigation bar with role-based menu |
| `frontend/app/settings/users/page.tsx` | User management page (list, create modal, edit modal, reset modal) |
| `frontend/app/settings/change-password/page.tsx` | Self-service password change page |

## 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/main.py` | 注册 users router |
| `backend/app/services/auth_service.py` | authenticate_user 增加 is_active 检查（禁用用户无法登录） |
| `frontend/lib/api.ts` | 新增 userApi（list, create, update, resetPassword, changePassword） |
| `frontend/types/index.ts` | 新增 UserItem, UserCreate, UserUpdate, ChangePasswordRequest, ROLE_LABELS |
| `frontend/app/dashboard/page.tsx` | 使用共享 TopNav 组件，移除内联导航 |
| `frontend/app/leads/page.tsx` | 使用共享 TopNav 组件 |
| `frontend/app/leads/[id]/page.tsx` | 使用共享 TopNav 组件 |
| `frontend/app/leads/new/page.tsx` | 使用共享 TopNav 组件 |

## API 接口

| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/v1/users` | Admin | 用户列表 |
| POST | `/api/v1/users` | Admin | 新增用户（默认密码 123456） |
| PUT | `/api/v1/users/{id}` | Admin | 编辑用户 |
| PUT | `/api/v1/users/{id}/reset-password` | Admin | 重置密码为 123456 |
| PUT | `/api/v1/auth/change-password` | 登录用户 | 修改自己的密码 |

## 页面

- `/settings/users` — 用户管理（仅 Admin 可见菜单）
- `/settings/change-password` — 修改密码（所有用户可见）

## 权限

- **Admin**: 可进入用户管理页面，可操作所有接口
- **Manager/Counselor**: 菜单中隐藏「用户管理」，直接访问 API 返回 403
- **所有用户**: 可访问修改密码页面
- **禁用用户**: 无法登录（authenticate_user 检查 is_active），已有数据全部保留

## 浏览器验证结果

| # | 场景 | 结果 |
|---|------|------|
| 1 | Admin 登录 | ✅ |
| 2 | 新建 counselor | ✅ |
| 3 | Counselor 使用 123456 登录 | ✅ |
| 4 | Counselor 修改自己的密码 | ✅ |
| 5 | Counselor 用新密码重新登录 | ✅ |
| 6 | Admin 重置密码 | ✅ |
| 7 | Counselor 用 123456 重新登录 | ✅ |
| 8 | Admin 禁用 counselor | ✅ |
| 9 | Counselor 无法登录（is_active 检查） | ✅ |
| 10 | Admin 启用 counselor | ✅ |
| 11 | Counselor 再次登录成功 | ✅ |
| 12 | 非 Admin 访问用户列表 API → 403 | ✅ |

## 影响范围

- **向后兼容**: 不修改 users 表结构，不改变现有 API 行为
- **安全增强**: 新增 is_active 登录检查（之前禁用用户仍可登录 — 已修复）
- **导航重构**: 4 个页面统一使用共享 TopNav 组件，减少重复代码
- **数据库**: 无 schema 变更

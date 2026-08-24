"use client";

import { useCallback, useEffect, useState } from "react";
import { userApi } from "@/lib/api";
import { formatSystemTime } from "@/lib/datetime";
import { useToast } from "@/components/Toast";
import TopNav from "@/components/TopNav";
import Card from "@/components/Card";
import Button from "@/components/Button";
import { Input, Select } from "@/components/Input";
import Badge from "@/components/Badge";
import Modal from "@/components/Modal";
import Loading from "@/components/Loading";
import Empty from "@/components/Empty";
import { ROLE_LABELS, type UserItem } from "@/types";

export default function UserManagementPage() {
  const { toast } = useToast();

  // -- Role-based access control -------------------------------------------
  const [roleChecked, setRoleChecked] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);

  // -- Create modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [createUsername, setCreateUsername] = useState("");
  const [createRealName, setCreateRealName] = useState("");
  const [createRole, setCreateRole] = useState("counselor");
  const [createPhone, setCreatePhone] = useState("");
  const [createEmail, setCreateEmail] = useState("");
  const [createSaving, setCreateSaving] = useState(false);

  // -- Edit modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editUser, setEditUser] = useState<UserItem | null>(null);
  const [editRealName, setEditRealName] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editIsActive, setEditIsActive] = useState(1);
  const [editSaving, setEditSaving] = useState(false);

  // -- Reset password modal state
  const [resetOpen, setResetOpen] = useState(false);
  const [resetUser, setResetUser] = useState<UserItem | null>(null);
  const [resetSaving, setResetSaving] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      const data = await userApi.list();
      setUsers(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "加载失败";
      toast(message, "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // Check user role on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        setIsAdmin(u.role === "admin");
      }
    } catch {
      // ignore
    }
    setRoleChecked(true);
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    }
  }, [fetchUsers, isAdmin]);

  // -- Create user -----------------------------------------------------------

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createUsername.trim() || !createRealName.trim()) {
      toast("请填写用户名和真实姓名", "error");
      return;
    }
    setCreateSaving(true);
    try {
      await userApi.create({
        username: createUsername.trim(),
        real_name: createRealName.trim(),
        role: createRole,
        phone: createPhone.trim() || undefined,
        email: createEmail.trim() || undefined,
      });
      toast("用户创建成功，默认密码: 123456", "success");
      setCreateOpen(false);
      resetCreateForm();
      fetchUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "创建失败";
      toast(message, "error");
    } finally {
      setCreateSaving(false);
    }
  };

  const resetCreateForm = () => {
    setCreateUsername("");
    setCreateRealName("");
    setCreateRole("counselor");
    setCreatePhone("");
    setCreateEmail("");
  };

  // -- Edit user -------------------------------------------------------------

  const openEdit = (user: UserItem) => {
    setEditUser(user);
    setEditRealName(user.real_name);
    setEditRole(user.role);
    setEditPhone(user.phone || "");
    setEditEmail(user.email || "");
    setEditIsActive(user.is_active);
    setEditOpen(true);
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editUser) return;
    setEditSaving(true);
    try {
      await userApi.update(editUser.id, {
        real_name: editRealName.trim(),
        role: editRole,
        phone: editPhone.trim() || undefined,
        email: editEmail.trim() || undefined,
        is_active: editIsActive,
      });
      toast("用户更新成功", "success");
      setEditOpen(false);
      fetchUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "更新失败";
      toast(message, "error");
    } finally {
      setEditSaving(false);
    }
  };

  // -- Reset password --------------------------------------------------------

  const openReset = (user: UserItem) => {
    setResetUser(user);
    setResetOpen(true);
  };

  const handleReset = async () => {
    if (!resetUser) return;
    setResetSaving(true);
    try {
      await userApi.resetPassword(resetUser.id);
      toast("密码已重置为 123456", "success");
      setResetOpen(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "重置失败";
      toast(message, "error");
    } finally {
      setResetSaving(false);
    }
  };

  // -- Toggle active ---------------------------------------------------------

  const handleToggleActive = async (user: UserItem) => {
    const newActive = user.is_active === 1 ? 0 : 1;
    const actionLabel = newActive === 0 ? "禁用" : "启用";
    try {
      await userApi.update(user.id, { is_active: newActive });
      toast(`用户已${actionLabel}`, "success");
      fetchUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "操作失败";
      toast(message, "error");
    }
  };

  // -- Render ----------------------------------------------------------------

  // Loading while checking role
  if (!roleChecked) {
    return (
      <div className="min-h-screen bg-gray-50">
        <TopNav currentPath="/settings/users" />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <Loading text="加载中..." />
        </main>
      </div>
    );
  }

  // Non-admin users cannot access this page
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gray-50">
        <TopNav currentPath="/settings/users" />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <Card>
            <div className="py-16 text-center">
              <h2 className="text-lg font-semibold text-gray-900">
                无权限访问
              </h2>
              <p className="mt-2 text-sm text-gray-500">
                您没有权限访问此页面，请联系管理员
              </p>
            </div>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav currentPath="/settings/users" />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">用户管理</h1>
            <p className="mt-1 text-sm text-gray-500">
              管理系统用户账号与权限
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>新增用户</Button>
        </div>

        {/* Table */}
        <Card padding="none" className="overflow-hidden">
          {loading ? (
            <Loading text="加载中..." />
          ) : users.length === 0 ? (
            <Empty
              title="暂无用户"
              description="点击右上角「新增用户」创建第一个用户"
              action={
                <Button size="sm" onClick={() => setCreateOpen(true)}>
                  新增用户
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
                    <th className="px-4 py-3">用户名</th>
                    <th className="px-4 py-3">真实姓名</th>
                    <th className="px-4 py-3">角色</th>
                    <th className="px-4 py-3">手机号</th>
                    <th className="px-4 py-3">邮箱</th>
                    <th className="px-4 py-3">状态</th>
                    <th className="px-4 py-3">创建时间</th>
                    <th className="px-4 py-3">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {users.map((user) => (
                    <tr
                      key={user.id}
                      className="transition-colors hover:bg-gray-50"
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {user.username}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {user.real_name}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            user.role === "admin"
                              ? "purple"
                              : user.role === "manager"
                                ? "blue"
                                : "green"
                          }
                        >
                          {ROLE_LABELS[user.role] || user.role}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {user.phone || "-"}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {user.email || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={user.is_active === 1 ? "green" : "gray"}
                        >
                          {user.is_active === 1 ? "启用" : "禁用"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {formatSystemTime(user.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEdit(user)}
                          >
                            编辑
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActive(user)}
                          >
                            {user.is_active === 1 ? "禁用" : "启用"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openReset(user)}
                          >
                            重置密码
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Create Modal */}
        <Modal
          open={createOpen}
          onClose={() => {
            setCreateOpen(false);
            resetCreateForm();
          }}
          title="新增用户"
          size="md"
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <Input
              label="用户名"
              value={createUsername}
              onChange={(e) => setCreateUsername(e.target.value)}
              placeholder="请输入用户名"
              required
            />
            <Input
              label="真实姓名"
              value={createRealName}
              onChange={(e) => setCreateRealName(e.target.value)}
              placeholder="请输入真实姓名"
              required
            />
            <Select
              label="角色"
              value={createRole}
              onChange={(e) => setCreateRole(e.target.value)}
              options={[
                { value: "counselor", label: "咨询师" },
                { value: "manager", label: "主管" },
                { value: "admin", label: "管理员" },
              ]}
            />
            <Input
              label="手机号（可选）"
              value={createPhone}
              onChange={(e) => setCreatePhone(e.target.value)}
              placeholder="请输入手机号"
            />
            <Input
              label="邮箱（可选）"
              value={createEmail}
              onChange={(e) => setCreateEmail(e.target.value)}
              placeholder="请输入邮箱"
            />
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                type="button"
                onClick={() => {
                  setCreateOpen(false);
                  resetCreateForm();
                }}
              >
                取消
              </Button>
              <Button type="submit" loading={createSaving}>
                保存
              </Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        <Modal
          open={editOpen}
          onClose={() => setEditOpen(false)}
          title="编辑用户"
          size="md"
        >
          {editUser && (
            <form onSubmit={handleEdit} className="space-y-4">
              <Input
                label="用户名"
                value={editUser.username}
                onChange={() => {}}
                disabled
              />
              <Input
                label="真实姓名"
                value={editRealName}
                onChange={(e) => setEditRealName(e.target.value)}
                required
              />
              <Select
                label="角色"
                value={editRole}
                onChange={(e) => setEditRole(e.target.value)}
                options={[
                  { value: "counselor", label: "咨询师" },
                  { value: "manager", label: "主管" },
                  { value: "admin", label: "管理员" },
                ]}
              />
              <Input
                label="手机号"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
              />
              <Input
                label="邮箱"
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
              />
              <Select
                label="状态"
                value={String(editIsActive)}
                onChange={(e) => setEditIsActive(Number(e.target.value))}
                options={[
                  { value: "1", label: "启用" },
                  { value: "0", label: "禁用" },
                ]}
              />
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => setEditOpen(false)}
                >
                  取消
                </Button>
                <Button type="submit" loading={editSaving}>
                  保存
                </Button>
              </div>
            </form>
          )}
        </Modal>

        {/* Reset Password Modal */}
        <Modal
          open={resetOpen}
          onClose={() => setResetOpen(false)}
          title="重置密码"
          size="sm"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              确认将用户{" "}
              <span className="font-medium text-gray-900">
                {resetUser?.real_name || resetUser?.username}
              </span>{" "}
              的密码重置为默认密码{" "}
              <span className="font-medium text-gray-900">123456</span>？
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setResetOpen(false)}
              >
                取消
              </Button>
              <Button onClick={handleReset} loading={resetSaving}>
                确认重置
              </Button>
            </div>
          </div>
        </Modal>
      </main>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { userApi } from "@/lib/api";
import { useToast } from "@/components/Toast";
import TopNav from "@/components/TopNav";
import Card from "@/components/Card";
import Button from "@/components/Button";
import { Input } from "@/components/Input";

export default function ChangePasswordPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!oldPassword || !newPassword || !confirmPassword) {
      toast("请填写所有字段", "error");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast("两次输入的新密码不一致", "error");
      return;
    }

    if (newPassword.length < 6) {
      toast("密码长度不能少于6位", "error");
      return;
    }

    setSaving(true);
    try {
      await userApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast("密码修改成功", "success");
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "修改失败";
      toast(message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav currentPath="/settings/change-password" />

      <main className="mx-auto max-w-lg px-4 py-16 sm:px-6">
        <Card>
          <h1 className="text-xl font-bold text-gray-900">修改密码</h1>
          <p className="mt-1 text-sm text-gray-500">修改当前登录账号的密码</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Input
              label="旧密码"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="请输入旧密码"
              required
            />
            <Input
              label="新密码"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="请输入新密码（至少6位）"
              required
            />
            <Input
              label="确认新密码"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="请再次输入新密码"
              required
            />
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                type="button"
                onClick={() => router.back()}
              >
                返回
              </Button>
              <Button type="submit" loading={saving}>
                确认修改
              </Button>
            </div>
          </form>
        </Card>
      </main>
    </div>
  );
}

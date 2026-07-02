"use client";

import { useRouter } from "next/navigation";
import HeaderLogo from "./HeaderLogo";

interface TopNavProps {
  /** Current active page path, e.g. "/dashboard", "/leads", "/settings/users" */
  currentPath: string;
}

export default function TopNav({ currentPath }: TopNavProps) {
  const router = useRouter();

  // Read user info from localStorage for display and role check
  let userName = "";
  let userRole = "";
  try {
    const stored = localStorage.getItem("user");
    if (stored) {
      const u = JSON.parse(stored);
      userName = u.real_name || u.username || "";
      userRole = u.role || "";
    }
  } catch {
    // ignore
  }

  const isAdmin = userRole === "admin";

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    router.push("/login");
  };

  const navItems = [
    { path: "/dashboard", label: "首页" },
    { path: "/leads", label: "线索管理" },
  ];

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <HeaderLogo />
          <nav className="hidden sm:flex items-center gap-4">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => router.push(item.path)}
                className={`text-sm font-medium transition-colors ${
                  currentPath.startsWith(item.path)
                    ? "text-blue-600"
                    : "text-gray-600 hover:text-blue-600"
                }`}
              >
                {item.label}
              </button>
            ))}
            {isAdmin && (
              <button
                onClick={() => router.push("/settings/users")}
                className={`text-sm font-medium transition-colors ${
                  currentPath.startsWith("/settings/users")
                    ? "text-blue-600"
                    : "text-gray-600 hover:text-blue-600"
                }`}
              >
                系统设置
              </button>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{userName}</span>
          <button
            onClick={() => router.push("/settings/change-password")}
            className="text-sm text-gray-400 hover:text-blue-600 transition-colors"
          >
            修改密码
          </button>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            退出
          </button>
        </div>
      </div>
    </header>
  );
}

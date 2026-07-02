"use client";

import { useRouter } from "next/navigation";

export default function HeaderLogo() {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push("/dashboard")}
      className="flex items-center gap-3 text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors"
    >
      <img
        src="/logo-light.png"
        alt="JiuWei CRM Logo"
        className="h-8 w-8 object-contain"
      />
      <span>CRM系统</span>
    </button>
  );
}

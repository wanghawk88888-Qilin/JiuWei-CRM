"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { dashboardApi } from "@/lib/api";
import { isAdminRole } from "@/lib/auth";
import { formatSystemTime, formatNextFollowup } from "@/lib/datetime";
import { useToast } from "@/components/Toast";
import Card from "@/components/Card";
import Button from "@/components/Button";
import Badge, { statusBadgeVariant } from "@/components/Badge";
import Loading from "@/components/Loading";
import Empty from "@/components/Empty";
import TopNav from "@/components/TopNav";
import {
  STATUS_LABELS,
  type DashboardSummary,
  type TodayFollowUpItem,
  type RecentLeadItem,
} from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const { toast } = useToast();
  const isAdmin = isAdminRole();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [todayFollowups, setTodayFollowups] = useState<TodayFollowUpItem[]>([]);
  const [recentLeads, setRecentLeads] = useState<RecentLeadItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [s, f, r] = await Promise.all([
        dashboardApi.summary(),
        dashboardApi.todayFollowups(),
        dashboardApi.recentLeads(),
      ]);
      setSummary(s);
      setTodayFollowups(f);
      setRecentLeads(r);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "加载失败";
      toast(message, "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (loading) {
    return (
      <DashboardShell>
        <Loading text="加载中..." />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell>
      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="全部线索"
          value={summary?.total_leads ?? 0}
          color="blue"
          href="/leads"
        />
        <StatCard
          label="今日新增"
          value={summary?.today_new_leads ?? 0}
          color="green"
          href="/leads?created=today"
        />
        <StatCard
          label="待跟进"
          value={summary?.pending_followups ?? 0}
          color="yellow"
          href="/leads?followup=pending"
        />
        <StatCard
          label="已报名"
          value={summary?.enrolled_leads ?? 0}
          color="purple"
          href="/leads?status=enrolled"
        />
      </div>

      {/* Quick actions */}
      <div className="mt-6 flex gap-3">
        <Button onClick={() => router.push("/leads/new")}>新建线索</Button>
        <Button
          variant="secondary"
          onClick={() => router.push("/leads/new?upload=1")}
        >
          上传简历
        </Button>
      </div>

      {/* Today's followups */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900">今日待跟进</h2>
        <Card padding="none" className="mt-3 overflow-hidden">
          {todayFollowups.length === 0 ? (
            <Empty
              title="暂无待跟进"
              description="今天没有需要跟进的线索"
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
                  <th className="px-4 py-3">姓名</th>
                  <th className="px-4 py-3">手机号</th>
                  {isAdmin && <th className="px-4 py-3">咨询师</th>}
                  <th className="px-4 py-3">意向课程</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">最近跟进</th>
                  <th className="px-4 py-3">下次跟进</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {todayFollowups.map((item) => {
                  const isOverdue = item.followup_priority === "overdue";
                  const isUpcoming = item.followup_priority === "upcoming";

                  return (
                    <tr
                      key={item.lead_id}
                      className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                        isOverdue
                          ? "border-l-2 border-l-red-400 bg-red-50/30"
                          : isUpcoming
                            ? "text-gray-500"
                            : ""
                      }`}
                      onClick={() => router.push(`/leads/${item.lead_id}`)}
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">
                        <span className="flex items-center gap-2">
                          {item.lead_name}
                          {isOverdue && (
                            <span className="inline-flex items-center rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
                              已逾期
                            </span>
                          )}
                          {item.followup_priority === "today" && (
                            <span className="inline-flex items-center rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-700">
                              今天
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {item.phone || "-"}
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3 text-gray-500">
                          {item.owner_name || "未分配"}
                        </td>
                      )}
                      <td className="px-4 py-3 text-gray-500">
                        {item.intended_course_name || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={statusBadgeVariant(item.status)}>
                          {STATUS_LABELS[item.status] || item.status}
                        </Badge>
                      </td>
                      <td className="max-w-48 px-4 py-3 text-gray-500 truncate">
                        {item.latest_followup_content || "尚未跟进"}
                      </td>
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                        {formatNextFollowup(item.next_followup_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {/* Recent leads */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900">最近新增线索</h2>
        <Card padding="none" className="mt-3 overflow-hidden">
          {recentLeads.length === 0 ? (
            <Empty
              title="暂无数据"
              description="还没有创建任何线索"
              action={
                <Button
                  size="sm"
                  onClick={() => router.push("/leads/new")}
                >
                  新建线索
                </Button>
              }
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
                  <th className="px-4 py-3">姓名</th>
                  <th className="px-4 py-3">手机号</th>
                  {isAdmin && <th className="px-4 py-3">咨询师</th>}
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">创建时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentLeads.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer transition-colors hover:bg-gray-50"
                    onClick={() => router.push(`/leads/${item.id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {item.name}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.phone || "-"}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-gray-500">
                        {item.owner_name || "未分配"}
                      </td>
                    )}
                    <td className="px-4 py-3">
                      <Badge variant={statusBadgeVariant(item.status)}>
                        {STATUS_LABELS[item.status] || item.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {formatSystemTime(item.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {/* All leads link */}
      <div className="mt-6 text-center">
        <Button
          variant="ghost"
          onClick={() => router.push("/leads")}
        >
          查看全部线索 →
        </Button>
      </div>
    </DashboardShell>
  );
}

// -- Shell ------------------------------------------------------------------

function DashboardShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <TopNav currentPath="/dashboard" />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}

// -- Stat card --------------------------------------------------------------

function StatCard({
  label,
  value,
  color,
  href,
}: {
  label: string;
  value: number;
  color: "blue" | "green" | "yellow" | "purple";
  href: string;
}) {
  const router = useRouter();

  const colorMap = {
    blue: "border-l-blue-500 bg-blue-50/50 hover:border-blue-400",
    green: "border-l-green-500 bg-green-50/50 hover:border-green-400",
    yellow: "border-l-yellow-500 bg-yellow-50/50 hover:border-yellow-400",
    purple: "border-l-purple-500 bg-purple-50/50 hover:border-purple-400",
  };

  const textColorMap = {
    blue: "text-blue-700",
    green: "text-green-700",
    yellow: "text-yellow-700",
    purple: "text-purple-700",
  };

  return (
    <button
      type="button"
      onClick={() => router.push(href)}
      className={`group w-full rounded-xl border border-gray-200 border-l-4 px-5 py-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 ${colorMap[color]}`}
    >
      <p className="text-sm font-medium text-gray-600">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${textColorMap[color]}`}>
        {value}
      </p>
    </button>
  );
}

"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { leadApi } from "@/lib/api";
import { isAdminRole } from "@/lib/auth";
import { formatSystemTime, formatNextFollowup } from "@/lib/datetime";
import { useToast } from "@/components/Toast";
import Card from "@/components/Card";
import Button from "@/components/Button";
import Badge, { statusBadgeVariant, intentionBadgeVariant } from "@/components/Badge";
import Loading from "@/components/Loading";
import Empty from "@/components/Empty";
import TopNav from "@/components/TopNav";
import {
  STATUS_LABELS,
  INTENTION_LABELS,
  type LeadListItem,
} from "@/types";

function LeadsPageInner() {
  const router = useRouter();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const isAdmin = isAdminRole();

  // Card-driven filters live in the URL so they survive a refresh.
  const statusParam = searchParams.get("status") ?? "";
  const createdParam = searchParams.get("created") ?? "";
  const followupParam = searchParams.get("followup") ?? "";

  const [items, setItems] = useState<LeadListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState(statusParam);

  const pageSize = 20;

  // Keep the status select in sync when the URL changes (e.g. re-clicking a card).
  useEffect(() => {
    setStatusFilter(statusParam);
  }, [statusParam]);

  const fetchLeads = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const data = await leadApi.list({
          keyword: keyword || undefined,
          status: statusFilter || undefined,
          created: createdParam || undefined,
          followup: followupParam || undefined,
          page: p,
          page_size: pageSize,
        });
        setItems(data.items);
        setTotal(data.total);
        setPage(data.page);
        setTotalPages(Math.ceil(data.total / data.page_size) || 1);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "加载失败";
        toast(message, "error");
      } finally {
        setLoading(false);
      }
    },
    [keyword, statusFilter, createdParam, followupParam, toast],
  );

  useEffect(() => {
    fetchLeads(1);
  }, [fetchLeads]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLeads(1);
  };

  // Update the URL-backed status filter (preserves created/followup params).
  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set("status", value);
    } else {
      params.delete("status");
    }
    const qs = params.toString();
    router.replace(qs ? `/leads?${qs}` : "/leads");
  };

  const clearFilters = () => {
    setStatusFilter("");
    router.replace("/leads");
  };

  const activeFilterLabels: string[] = [];
  if (followupParam === "pending") activeFilterLabels.push("待跟进");
  if (createdParam === "today") activeFilterLabels.push("今日新增");
  if (statusFilter) {
    activeFilterLabels.push(STATUS_LABELS[statusFilter] || statusFilter);
  }
  const hasActiveFilter = activeFilterLabels.length > 0;

  return (
    <div className="min-h-screen">
      <TopNav currentPath="/leads" />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">线索管理</h1>
          <div className="flex gap-2">
            <Button onClick={() => router.push("/leads/new")}>
              新建线索
            </Button>
            <Button
              variant="secondary"
              onClick={() => router.push("/leads/new?upload=1")}
            >
              上传简历
            </Button>
            <Button
              variant="secondary"
              onClick={() => router.push("/leads/import-batch")}
            >
              批量导入简历
            </Button>
          </div>
        </div>

        {/* Active filter banner */}
        {hasActiveFilter && (
          <div className="mt-3 flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50 px-4 py-2">
            <span className="text-sm text-blue-700">
              当前筛选：{activeFilterLabels.join("、")}
            </span>
            <button
              type="button"
              onClick={clearFilters}
              className="text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              清除筛选
            </button>
          </div>
        )}

        {/* Search and filter */}
        <Card className="mt-4">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-3">
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="搜索姓名、手机号、微信..."
              className="min-w-[240px] flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <select
              value={statusFilter}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">全部状态</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <Button type="submit" variant="secondary" size="sm">
              搜索
            </Button>
          </form>
        </Card>

        {/* Lead table */}
        <Card padding="none" className="mt-4 overflow-hidden">
          {loading ? (
            <Loading text="加载中..." />
          ) : items.length === 0 ? (
            <Empty
              title="暂无线索"
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
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
                      <th className="px-4 py-3">姓名</th>
                      <th className="px-4 py-3">手机号</th>
                      {isAdmin && <th className="px-4 py-3">咨询师</th>}
                      <th className="px-4 py-3">状态</th>
                      <th className="px-4 py-3">意向等级</th>
                      <th className="px-4 py-3">最近跟进</th>
                      <th className="px-4 py-3">最近跟进时间</th>
                      <th className="px-4 py-3">下次跟进时间</th>
                      <th className="px-4 py-3">创建时间</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {items.map((item) => (
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
                        <td className="px-4 py-3">
                          {item.intention_level ? (
                            <Badge
                              variant={intentionBadgeVariant(item.intention_level)}
                            >
                              {INTENTION_LABELS[item.intention_level] ||
                                item.intention_level}
                            </Badge>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="max-w-48 px-4 py-3 text-gray-500 truncate">
                          {item.last_followup_content || "尚未跟进"}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {formatSystemTime(item.last_followup_at)}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {formatNextFollowup(item.next_followup_at)}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {formatSystemTime(item.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
                <span className="text-sm text-gray-500">
                  共 {total} 条，第 {page} / {totalPages} 页
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => fetchLeads(page - 1)}
                  >
                    上一页
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => fetchLeads(page + 1)}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </main>
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        </div>
      }
    >
      <LeadsPageInner />
    </Suspense>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  configApi,
  followUpApi,
  leadApi,
  leadDraftApi,
  resumeImportApi,
} from "@/lib/api";
import { useToast } from "@/components/Toast";
import Card from "@/components/Card";
import Button from "@/components/Button";
import { Input, Select, Textarea } from "@/components/Input";
import TopNav from "@/components/TopNav";
import Badge, {
  statusBadgeVariant,
  intentionBadgeVariant,
} from "@/components/Badge";
import Modal from "@/components/Modal";
import Loading from "@/components/Loading";
import Empty from "@/components/Empty";
import {
  FOLLOWUP_TYPE_LABELS,
  INTENTION_LABELS,
  STATUS_LABELS,
  GENDER_LABELS,
  type Course,
  type FollowUpItem,
  type LeadDetail,
  type LeadSource,
} from "@/types";

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const leadId = Number(params.id);

  // -- Data --------------------------------------------------------------
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [followups, setFollowups] = useState<FollowUpItem[]>([]);
  const [sources, setSources] = useState<LeadSource[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  // -- FollowUp form -----------------------------------------------------
  const [fuType, setFuType] = useState("phone");
  const [fuContent, setFuContent] = useState("");
  const [fuIntention, setFuIntention] = useState("");
  const [fuNextTime, setFuNextTime] = useState("");
  const [fuSaving, setFuSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // -- Enroll ------------------------------------------------------------
  const [enrolling, setEnrolling] = useState(false);

  // -- Resume upload -----------------------------------------------------
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [draftModalOpen, setDraftModalOpen] = useState(false);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null);
  const [confirming, setConfirming] = useState(false);

  // -- Fetch -------------------------------------------------------------

  const fetchLead = useCallback(async () => {
    try {
      const data = await leadApi.get(leadId);
      setLead(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "加载失败";
      toast(message, "error");
      router.push("/leads");
    }
  }, [leadId, router, toast]);

  const fetchFollowups = useCallback(async () => {
    try {
      const data = await followUpApi.list(leadId);
      setFollowups(data);
    } catch {
      // Non-blocking
    }
  }, [leadId]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [src, crs] = await Promise.all([
        configApi.leadSources().catch(() => []),
        configApi.courses().catch(() => []),
      ]);
      setSources(src);
      setCourses(crs);
      await Promise.all([fetchLead(), fetchFollowups()]);
      setLoading(false);
    };
    init();
  }, [fetchLead, fetchFollowups]);

  // -- Enroll handler ----------------------------------------------------

  const handleEnroll = async () => {
    if (!confirm("确定要将该线索标记为已报名吗？")) return;

    setEnrolling(true);
    try {
      await leadApi.update(leadId, { status: "enrolled" });
      toast("已标记为已报名", "success");
      await fetchLead();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "操作失败";
      toast(message, "error");
    } finally {
      setEnrolling(false);
    }
  };

  // -- FollowUp handlers -------------------------------------------------

  const handleAddFollowUp = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!fuContent.trim()) {
      toast("请输入跟进内容", "error");
      return;
    }

    setFuSaving(true);
    try {
      await followUpApi.create(leadId, {
        followup_type: fuType,
        content: fuContent.trim(),
        intention_level: fuIntention || null,
        next_followup_at: fuNextTime || null,
      });
      toast("跟进记录已保存", "success");
      setFuContent("");
      setFuIntention("");
      setFuNextTime("");
      await fetchFollowups();
      await fetchLead(); // Refresh lead status if changed
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "保存失败";
      toast(message, "error");
    } finally {
      setFuSaving(false);
    }
  };

  const handleDeleteFollowUp = async (followupId: number) => {
    if (!confirm("确定要删除这条跟进记录吗？")) return;

    setDeletingId(followupId);
    try {
      await followUpApi.delete(followupId);
      toast("跟进记录已删除", "success");
      await fetchFollowups();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "删除失败";
      toast(message, "error");
    } finally {
      setDeletingId(null);
    }
  };

  // -- Resume upload handlers --------------------------------------------

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setUploading(true);
    try {
      const result = await resumeImportApi.upload(file);
      setDraftId(result.lead_draft_id);
      setDraft(result.draft);
      setDraftModalOpen(true);
      toast("简历解析完成", "success");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "简历解析失败";
      toast(message, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmDraft = async () => {
    if (!draftId) return;
    setConfirming(true);
    try {
      const result = await leadDraftApi.confirm(draftId, {});
      toast("已生成正式线索", "success");
      setDraftModalOpen(false);
      router.push(`/leads/${result.lead_id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "确认失败";
      toast(message, "error");
    } finally {
      setConfirming(false);
    }
  };

  // -- Helpers -----------------------------------------------------------

  const getSourceName = (id: number | null) => {
    if (!id) return "-";
    return sources.find((s) => s.id === id)?.name || "-";
  };

  const getCourseName = (id: number | null) => {
    if (!id) return "-";
    return courses.find((c) => c.id === id)?.name || "-";
  };

  // -- Loading state -----------------------------------------------------

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopNav currentPath="/leads" />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <Loading text="加载中..." />
        </main>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen">
        <TopNav currentPath="/leads" />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <Empty title="线索不存在" description="该线索可能已被删除" />
        </main>
      </div>
    );
  }

  // -- Render ------------------------------------------------------------

  return (
    <div className="min-h-screen">
      <TopNav currentPath="/leads" />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => router.push("/leads")}>
              ← 返回列表
            </Button>
            <h1 className="text-xl font-bold text-gray-900">{lead.name}</h1>
            <Badge variant={statusBadgeVariant(lead.status)}>
              {STATUS_LABELS[lead.status] || lead.status}
            </Badge>
          </div>
          <div className="flex gap-2">
            {lead.status !== "enrolled" && (
              <Button
                size="sm"
                className="bg-green-600 text-white hover:bg-green-700 focus:ring-green-500 disabled:bg-green-300"
                loading={enrolling}
                onClick={handleEnroll}
              >
                标记为已报名
              </Button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="secondary"
              size="sm"
              loading={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              上传简历
            </Button>
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left: Lead detail */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic info */}
            <Card>
              <h2 className="mb-4 text-base font-semibold text-gray-900">
                基本信息
              </h2>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <Field label="姓名" value={lead.name} />
                <Field label="手机号" value={lead.phone || "-"} />
                <Field label="微信" value={lead.wechat || "-"} />
                <Field label="邮箱" value={lead.email || "-"} />
                <Field
                  label="性别"
                  value={lead.gender ? GENDER_LABELS[lead.gender] || lead.gender : "-"}
                />
                <Field label="年龄" value={lead.age != null ? String(lead.age) : "-"} />
              </div>
            </Card>

            {/* Education / Career */}
            <Card>
              <h2 className="mb-4 text-base font-semibold text-gray-900">
                教育/职业信息
              </h2>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <Field label="学历" value={lead.education || "-"} />
                <Field label="学校" value={lead.school || "-"} />
                <Field label="专业" value={lead.major || "-"} />
                <Field label="城市" value={lead.city || "-"} />
                <Field label="当前职业" value={lead.current_job || "-"} />
                <Field label="工作年限" value={lead.work_years || "-"} />
                <Field label="最近公司" value={lead.latest_company || "-"} />
                <Field label="最近岗位" value={lead.latest_position || "-"} />
              </div>
            </Card>

            {/* Business info */}
            <Card>
              <h2 className="mb-4 text-base font-semibold text-gray-900">
                业务信息
              </h2>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <Field label="意向课程" value={getCourseName(lead.intended_course_id)} />
                <Field label="线索来源" value={getSourceName(lead.source_id)} />
                <div>
                  <span className="text-gray-500">意向等级：</span>
                  {lead.intention_level ? (
                    <Badge variant={intentionBadgeVariant(lead.intention_level)}>
                      {INTENTION_LABELS[lead.intention_level] || lead.intention_level}
                    </Badge>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>
                <Field label="创建时间" value={lead.created_at} />
                <Field label="更新时间" value={lead.updated_at} />
              </div>
              {lead.remark && (
                <div className="mt-4 border-t border-gray-100 pt-4">
                  <Field label="备注" value={lead.remark} />
                </div>
              )}
              {lead.ai_summary && (
                <div className="mt-4 rounded-lg bg-blue-50 p-3">
                  <p className="text-xs font-medium text-blue-700">AI 摘要</p>
                  <p className="mt-1 text-sm text-blue-800">{lead.ai_summary}</p>
                </div>
              )}
            </Card>
          </div>

          {/* Right: FollowUp timeline */}
          <div className="space-y-6">
            {/* Add followup form */}
            <Card>
              <h2 className="mb-4 text-base font-semibold text-gray-900">
                新增跟进
              </h2>
              <form onSubmit={handleAddFollowUp} className="space-y-3">
                <Select
                  label="跟进方式"
                  value={fuType}
                  onChange={(e) => setFuType(e.target.value)}
                  options={Object.entries(FOLLOWUP_TYPE_LABELS).map(
                    ([v, l]) => ({ value: v, label: l }),
                  )}
                />
                <Textarea
                  label="跟进内容 *"
                  value={fuContent}
                  onChange={(e) => setFuContent(e.target.value)}
                  placeholder="请输入跟进内容..."
                  rows={3}
                />
                <Select
                  label="客户意向"
                  value={fuIntention}
                  onChange={(e) => setFuIntention(e.target.value)}
                  options={Object.entries(INTENTION_LABELS).map(
                    ([v, l]) => ({ value: v, label: l }),
                  )}
                  placeholder="请选择意向"
                />
                <Input
                  label="下次跟进时间"
                  type="datetime-local"
                  value={fuNextTime}
                  onChange={(e) => setFuNextTime(e.target.value)}
                />
                <Button
                  type="submit"
                  loading={fuSaving}
                  className="w-full"
                  size="sm"
                >
                  保存跟进
                </Button>
              </form>
            </Card>

            {/* Followup timeline */}
            <Card>
              <h2 className="mb-4 text-base font-semibold text-gray-900">
                跟进记录
                {followups.length > 0 && (
                  <span className="ml-1 text-sm font-normal text-gray-400">
                    ({followups.length})
                  </span>
                )}
              </h2>

              {followups.length === 0 ? (
                <Empty title="暂无跟进记录" description="新增一条跟进记录吧" />
              ) : (
                <div className="space-y-4">
                  {followups.map((fu) => (
                    <div
                      key={fu.id}
                      className="relative border-l-2 border-blue-200 pl-4 pb-1"
                    >
                      {/* Timeline dot */}
                      <div className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border-2 border-blue-500 bg-white" />

                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500">
                          {FOLLOWUP_TYPE_LABELS[fu.followup_type] || fu.followup_type}
                        </span>
                        <button
                          onClick={() => handleDeleteFollowUp(fu.id)}
                          disabled={deletingId === fu.id}
                          className="text-xs text-red-400 hover:text-red-600 disabled:opacity-50 transition-colors"
                        >
                          {deletingId === fu.id ? "删除中..." : "删除"}
                        </button>
                      </div>
                      <p className="mt-1 text-sm text-gray-800 whitespace-pre-wrap">
                        {fu.content}
                      </p>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                        <span>
                          跟进人：
                          <span className="font-medium text-gray-600">
                            {fu.created_by_name || "未知用户"}
                          </span>
                        </span>
                        {fu.intention_level && (
                          <span>
                            意向：
                            <span className="font-medium text-gray-600">
                              {INTENTION_LABELS[fu.intention_level] || fu.intention_level}
                            </span>
                          </span>
                        )}
                        {fu.next_followup_at && (
                          <span>下次跟进：{fu.next_followup_at}</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-gray-400">
                        {fu.created_at}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>

      {/* Draft confirmation modal */}
      <Modal
        open={draftModalOpen}
        onClose={() => setDraftModalOpen(false)}
        title="简历解析结果"
        size="lg"
      >
        {draft ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              {Object.entries(draft).map(([key, value]) => {
                if (value == null || value === "") return null;
                return (
                  <div key={key}>
                    <span className="text-gray-500">{key}：</span>
                    <span className="text-gray-900">{String(value)}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-3 border-t border-gray-200 pt-4">
              <Button loading={confirming} onClick={handleConfirmDraft}>
                确认生成线索
              </Button>
              <Button
                variant="secondary"
                onClick={() => setDraftModalOpen(false)}
              >
                关闭
              </Button>
            </div>
          </div>
        ) : (
          <Loading text="加载草稿..." />
        )}
      </Modal>
    </div>
  );
}

// -- Shared top nav ---------------------------------------------------------



// -- Field helper -----------------------------------------------------------

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-500">{label}：</span>
      <span className="text-gray-900">{value}</span>
    </div>
  );
}

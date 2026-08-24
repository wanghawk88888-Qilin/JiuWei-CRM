"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { configApi, leadDraftApi, resumeImportApi } from "@/lib/api";
import { useToast } from "@/components/Toast";
import Card from "@/components/Card";
import Button from "@/components/Button";
import Badge from "@/components/Badge";
import { Input, Select } from "@/components/Input";
import Modal from "@/components/Modal";
import Loading from "@/components/Loading";
import Empty from "@/components/Empty";
import TopNav from "@/components/TopNav";
import {
  BATCH_ITEM_STATUS_LABELS,
  BATCH_STATUS_LABELS,
  CONFIDENCE_LABELS,
  CONFLICT_LABELS,
  IMPORT_ERROR_LABELS,
  type BatchDetail,
  type BatchItem,
  type BatchLimits,
  type LeadSource,
} from "@/types";

const POLL_INTERVAL_MS = 1500;

type StatusFilter = "all" | "ready" | "needs_review" | "duplicate" | "failed";

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "ready", label: "可直接导入" },
  { key: "needs_review", label: "需人工确认" },
  { key: "duplicate", label: "重复线索" },
  { key: "failed", label: "解析失败" },
];

function itemBadgeVariant(status: string) {
  switch (status) {
    case "ready":
      return "green" as const;
    case "needs_review":
      return "yellow" as const;
    case "duplicate":
      return "purple" as const;
    case "failed":
      return "red" as const;
    case "confirmed":
      return "blue" as const;
    default:
      return "gray" as const;
  }
}

export default function BatchImportPage() {
  const router = useRouter();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [limits, setLimits] = useState<BatchLimits>({
    max_files: 50,
    max_file_size_mb: 10,
    allowed_extensions: [".docx", ".pdf"],
  });
  const [sources, setSources] = useState<LeadSource[]>([]);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [confirming, setConfirming] = useState(false);
  const [sourceId, setSourceId] = useState("");

  // -- Review modal state ---------------------------------------------------
  const [reviewItem, setReviewItem] = useState<BatchItem | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    education: "",
    school: "",
    major: "",
  });

  // -- Load config ----------------------------------------------------------
  useEffect(() => {
    resumeImportApi.limits().then(setLimits).catch(() => {});
    configApi.leadSources().then(setSources).catch(() => {});
  }, []);

  // -- Polling --------------------------------------------------------------
  const loadBatch = useCallback(
    async (batchId: number) => {
      try {
        const data = await resumeImportApi.getBatch(batchId);
        setDetail(data);
        return data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "获取批次失败";
        toast(message, "error");
        return null;
      }
    },
    [toast],
  );

  useEffect(() => {
    if (!detail || detail.batch.status !== "processing") return;

    pollTimerRef.current = setTimeout(() => {
      loadBatch(detail.batch.id);
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [detail, loadBatch]);

  // -- File selection -------------------------------------------------------
  const acceptFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming || incoming.length === 0) return;

      const allowed = limits.allowed_extensions;
      const files = Array.from(incoming);
      const rejected: string[] = [];
      const accepted = files.filter((file) => {
        const dot = file.name.lastIndexOf(".");
        const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
        if (!allowed.includes(ext)) {
          rejected.push(file.name);
          return false;
        }
        return true;
      });

      if (rejected.length > 0) {
        toast(
          `已忽略 ${rejected.length} 个不支持的文件（仅支持 ${allowed.join("/")}）`,
          "error",
        );
      }
      if (accepted.length === 0) return;

      setSelectedFiles((prev) => {
        const merged = [...prev];
        accepted.forEach((file) => {
          const exists = merged.some(
            (f) => f.name === file.name && f.size === file.size,
          );
          if (!exists) merged.push(file);
        });
        if (merged.length > limits.max_files) {
          toast(`单次最多 ${limits.max_files} 个文件，超出部分已忽略`, "error");
          return merged.slice(0, limits.max_files);
        }
        return merged;
      });
    },
    [limits, toast],
  );

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast("请先选择简历文件", "error");
      return;
    }

    setUploading(true);
    try {
      const result = await resumeImportApi.uploadBatch(selectedFiles);
      toast(`已上传 ${result.total} 份简历，正在解析`, "success");
      setSelectedFiles([]);
      setFilter("all");
      await loadBatch(result.batch_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "批量上传失败";
      toast(message, "error");
    } finally {
      setUploading(false);
    }
  };

  // -- Review ---------------------------------------------------------------
  const openReview = (item: BatchItem) => {
    setReviewItem(item);
    setForm({
      name: item.name ?? "",
      phone: item.phone ?? "",
      email: item.email ?? "",
      education: item.education ?? "",
      school: item.school ?? "",
      major: item.major ?? "",
    });
  };

  const handleReviewSave = async () => {
    if (!reviewItem?.lead_draft_id || !detail) return;

    setReviewSaving(true);
    try {
      const updated = await leadDraftApi.update(reviewItem.lead_draft_id, {
        name: form.name.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        education: form.education.trim() || null,
        school: form.school.trim() || null,
        major: form.major.trim() || null,
      });

      if (updated.status === "ready") {
        toast("已修正，可直接导入", "success");
      } else if (updated.status === "duplicate") {
        toast("该手机号在系统中已存在，已标记为重复", "error");
      } else {
        toast("已保存，姓名和手机号仍需补全", "error");
      }

      setReviewItem(null);
      await loadBatch(detail.batch.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "保存失败";
      toast(message, "error");
    } finally {
      setReviewSaving(false);
    }
  };

  // -- Confirm --------------------------------------------------------------
  const handleConfirmBatch = async () => {
    if (!detail) return;

    setConfirming(true);
    try {
      const result = await resumeImportApi.confirmBatch(detail.batch.id, {
        source_id: sourceId ? parseInt(sourceId, 10) : null,
      });

      if (result.confirmed_count > 0) {
        toast(`已生成 ${result.confirmed_count} 条正式线索`, "success");
      } else {
        toast("没有可导入的记录", "error");
      }
      if (result.skipped_count > 0) {
        toast(`${result.skipped_count} 条被跳过（重复或待确认）`, "error");
      }
      await loadBatch(detail.batch.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "批量确认失败";
      toast(message, "error");
    } finally {
      setConfirming(false);
    }
  };

  // -- Derived --------------------------------------------------------------
  const items = detail?.items ?? [];
  const visibleItems =
    filter === "all" ? items : items.filter((item) => item.status === filter);
  const processing = detail?.batch.status === "processing";

  // -- Render ---------------------------------------------------------------
  return (
    <div className="min-h-screen">
      <TopNav currentPath="/leads" />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">批量导入简历</h1>
            <p className="mt-1 text-sm text-gray-500">
              单次最多 {limits.max_files} 份，单份不超过{" "}
              {limits.max_file_size_mb}MB，支持{" "}
              {limits.allowed_extensions.join(" / ")}
            </p>
          </div>
          <Button variant="ghost" onClick={() => router.push("/leads")}>
            返回线索列表
          </Button>
        </div>

        {/* Upload zone */}
        <Card className="mb-6">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              acceptFiles(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragActive
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={limits.allowed_extensions.join(",")}
              onChange={(e) => {
                acceptFiles(e.target.files);
                e.target.value = "";
              }}
              className="hidden"
            />
            <p className="text-sm font-medium text-gray-700">
              点击选择，或将多份简历拖拽到这里
            </p>
            <p className="mt-1 text-xs text-gray-500">
              扫描件 / 图片版 PDF 无法自动识别，会标记为解析失败
            </p>
          </div>

          {selectedFiles.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-medium text-gray-700">
                  已选择 {selectedFiles.length} 个文件
                </p>
                <button
                  onClick={() => setSelectedFiles([])}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  清空
                </button>
              </div>
              <div className="max-h-40 overflow-y-auto rounded-lg border border-gray-200">
                {selectedFiles.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="flex items-center justify-between border-b border-gray-100 px-3 py-2 text-sm last:border-b-0"
                  >
                    <span className="truncate text-gray-700">{file.name}</span>
                    <button
                      onClick={() =>
                        setSelectedFiles((prev) =>
                          prev.filter((_, i) => i !== idx),
                        )
                      }
                      className="ml-3 shrink-0 text-xs text-gray-400 hover:text-red-600"
                    >
                      移除
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <Button loading={uploading} onClick={handleUpload}>
                  {uploading ? "上传中..." : `开始上传并解析`}
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* Result */}
        {detail && (
          <>
            <Card className="mb-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold text-gray-900">
                      本次上传 {detail.batch.total_files} 份
                    </h2>
                    <Badge variant={processing ? "yellow" : "blue"}>
                      {BATCH_STATUS_LABELS[detail.batch.status] ??
                        detail.batch.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    批次号 {detail.batch.batch_no}
                  </p>
                </div>
                {processing && <Loading text="解析中..." />}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                <Stat label="可直接导入" value={detail.batch.ready_count} tone="green" />
                <Stat label="需人工确认" value={detail.batch.needs_review_count} tone="yellow" />
                <Stat label="重复线索" value={detail.batch.duplicate_count} tone="purple" />
                <Stat label="解析失败" value={detail.batch.failed_count} tone="red" />
                <Stat label="已生成线索" value={detail.batch.confirmed_count} tone="blue" />
              </div>

              <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-gray-200 pt-4">
                <div className="w-48">
                  <Select
                    label="线索来源（可选）"
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    options={sources.map((s) => ({
                      value: String(s.id),
                      label: s.name,
                    }))}
                    placeholder="默认：简历上传"
                  />
                </div>
                <Button
                  loading={confirming}
                  disabled={processing || detail.batch.ready_count === 0}
                  onClick={handleConfirmBatch}
                >
                  批量确认导入（{detail.batch.ready_count}）
                </Button>
                <p className="text-xs text-gray-500">
                  仅导入「可直接导入」的记录；重复与失败项不会生成线索
                </p>
              </div>
            </Card>

            {/* Filter tabs */}
            <div className="mb-3 flex flex-wrap gap-2">
              {FILTERS.map((f) => {
                const count =
                  f.key === "all"
                    ? items.length
                    : items.filter((i) => i.status === f.key).length;
                return (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      filter === f.key
                        ? "bg-blue-600 text-white"
                        : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {f.label} ({count})
                  </button>
                );
              })}
            </div>

            {/* Result table */}
            <Card padding="none">
              {visibleItems.length === 0 ? (
                <div className="py-12">
                  <Empty title="该分类下没有记录" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b border-gray-200 bg-gray-50">
                      <tr className="text-left text-xs font-medium text-gray-500">
                        <th className="px-4 py-3">文件</th>
                        <th className="px-4 py-3">姓名</th>
                        <th className="px-4 py-3">手机号</th>
                        <th className="px-4 py-3">学历</th>
                        <th className="px-4 py-3">解析状态</th>
                        <th className="px-4 py-3">说明</th>
                        <th className="px-4 py-3">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleItems.map((item) => (
                        <tr
                          key={item.import_log_id}
                          className="border-b border-gray-100 last:border-b-0"
                        >
                          <td className="max-w-[220px] truncate px-4 py-3 text-gray-700">
                            {item.file_name}
                          </td>
                          <td className="px-4 py-3">
                            <FieldCell
                              value={item.name}
                              confidence={item.name_confidence}
                            />
                          </td>
                          <td className="px-4 py-3">
                            <FieldCell
                              value={item.phone}
                              confidence={item.phone_confidence}
                            />
                          </td>
                          <td className="px-4 py-3 text-gray-700">
                            {item.education ?? "—"}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={itemBadgeVariant(item.status)}>
                              {BATCH_ITEM_STATUS_LABELS[item.status] ??
                                item.status}
                            </Badge>
                          </td>
                          <td className="max-w-[240px] px-4 py-3 text-xs text-gray-500">
                            <ItemNote item={item} />
                          </td>
                          <td className="px-4 py-3">
                            <ItemActions
                              item={item}
                              onReview={() => openReview(item)}
                              onView={(leadId) => router.push(`/leads/${leadId}`)}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </>
        )}

        {!detail && (
          <Card>
            <div className="py-8">
              <Empty
                title="尚未上传简历"
                description="选择多份简历后开始批量解析"
              />
            </div>
          </Card>
        )}

        {/* Review modal */}
        <Modal
          open={reviewItem !== null}
          onClose={() => setReviewItem(null)}
          title="人工确认"
          size="lg"
        >
          {reviewItem && (
            <div className="space-y-4">
              <p className="text-xs text-gray-500">{reviewItem.file_name}</p>

              {Object.entries(reviewItem.conflicts).map(([field, conflict]) =>
                conflict ? (
                  <div key={field} className="rounded-lg bg-yellow-50 p-3">
                    <p className="text-xs font-medium text-yellow-800">
                      {CONFLICT_LABELS[conflict.code] ?? conflict.code}
                    </p>
                    {conflict.candidates.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {conflict.candidates.map((candidate) => (
                          <button
                            key={candidate}
                            onClick={() =>
                              setForm((prev) => ({ ...prev, [field]: candidate }))
                            }
                            className="rounded-full border border-yellow-300 bg-white px-2.5 py-0.5 text-xs text-yellow-800 hover:bg-yellow-100"
                          >
                            {candidate}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null,
              )}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="姓名 *"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="请输入姓名"
                />
                <Input
                  label="手机号 *"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="11 位大陆手机号"
                />
                <Input
                  label="邮箱"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
                <Input
                  label="学历"
                  value={form.education}
                  onChange={(e) =>
                    setForm({ ...form, education: e.target.value })
                  }
                />
                <Input
                  label="学校"
                  value={form.school}
                  onChange={(e) => setForm({ ...form, school: e.target.value })}
                />
                <Input
                  label="专业"
                  value={form.major}
                  onChange={(e) => setForm({ ...form, major: e.target.value })}
                />
              </div>

              <p className="text-xs text-gray-500">
                姓名与手机号补全且手机号未重复后，该条记录将变为「可直接导入」。
              </p>

              <div className="flex gap-3 border-t border-gray-200 pt-4">
                <Button loading={reviewSaving} onClick={handleReviewSave}>
                  保存
                </Button>
                <Button variant="secondary" onClick={() => setReviewItem(null)}>
                  取消
                </Button>
              </div>
            </div>
          )}
        </Modal>
      </main>
    </div>
  );
}

// -- Helpers ----------------------------------------------------------------

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "green" | "yellow" | "purple" | "red" | "blue";
}) {
  const toneClasses: Record<string, string> = {
    green: "text-green-700 bg-green-50",
    yellow: "text-yellow-700 bg-yellow-50",
    purple: "text-purple-700 bg-purple-50",
    red: "text-red-700 bg-red-50",
    blue: "text-blue-700 bg-blue-50",
  };
  return (
    <div className={`rounded-lg px-3 py-2 ${toneClasses[tone]}`}>
      <p className="text-xs">{label}</p>
      <p className="mt-0.5 text-xl font-bold">{value}</p>
    </div>
  );
}

function FieldCell({
  value,
  confidence,
}: {
  value: string | null;
  confidence: string | null;
}) {
  if (!value) {
    return <span className="text-gray-400">未识别</span>;
  }
  return (
    <span className="text-gray-900">
      {value}
      {confidence && confidence !== "high" && (
        <span className="ml-1 text-xs text-yellow-600">
          （可信度{CONFIDENCE_LABELS[confidence] ?? confidence}）
        </span>
      )}
    </span>
  );
}

function ItemNote({ item }: { item: BatchItem }) {
  if (item.status === "failed") {
    return (
      <span className="text-red-600">
        {IMPORT_ERROR_LABELS[item.error_code ?? ""] ??
          item.error_message ??
          "解析失败"}
      </span>
    );
  }
  if (item.status === "duplicate" && item.duplicate) {
    if (item.duplicate.in_batch) {
      return <span className="text-purple-700">本批次中已有相同手机号</span>;
    }
    return (
      <span className="text-purple-700">
        系统中已存在相同手机号线索
        {item.duplicate.existing_lead_name
          ? `（${item.duplicate.existing_lead_name}）`
          : ""}
      </span>
    );
  }
  if (item.status === "needs_review") {
    const codes = Object.values(item.conflicts)
      .map((c) => (c ? CONFLICT_LABELS[c.code] ?? c.code : null))
      .filter(Boolean);
    return <span className="text-yellow-700">{codes.join("；") || "字段可信度不足"}</span>;
  }
  return <span>—</span>;
}

function ItemActions({
  item,
  onReview,
  onView,
}: {
  item: BatchItem;
  onReview: () => void;
  onView: (leadId: number) => void;
}) {
  if (item.status === "confirmed" && item.confirmed_lead_id) {
    return (
      <button
        onClick={() => onView(item.confirmed_lead_id as number)}
        className="text-sm text-blue-600 hover:underline"
      >
        查看线索
      </button>
    );
  }
  if (item.status === "duplicate") {
    if (item.duplicate?.existing_lead_id) {
      return (
        <button
          onClick={() => onView(item.duplicate!.existing_lead_id as number)}
          className="text-sm text-blue-600 hover:underline"
        >
          查看已有线索
        </button>
      );
    }
    return <span className="text-sm text-gray-400">已跳过</span>;
  }
  if (item.status === "needs_review" || item.status === "ready") {
    return (
      <button onClick={onReview} className="text-sm text-blue-600 hover:underline">
        {item.status === "ready" ? "编辑" : "人工确认"}
      </button>
    );
  }
  return <span className="text-sm text-gray-400">—</span>;
}

"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { configApi, leadApi, leadDraftApi, resumeImportApi } from "@/lib/api";
import { useToast } from "@/components/Toast";
import Card from "@/components/Card";
import Button from "@/components/Button";
import { Input, Select, Textarea } from "@/components/Input";
import Modal from "@/components/Modal";
import Loading from "@/components/Loading";
import TopNav from "@/components/TopNav";
import {
  INTENTION_LABELS,
  STATUS_LABELS,
  type Course,
  type LeadDraft,
  type LeadSource,
} from "@/types";

function NewLeadPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMode = searchParams.get("upload") === "1";

  // -- Config data ----------------------------------------------------------
  const [sources, setSources] = useState<LeadSource[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  // -- Form state -----------------------------------------------------------
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [wechat, setWechat] = useState("");
  const [email, setEmail] = useState("");
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("");
  const [education, setEducation] = useState("");
  const [school, setSchool] = useState("");
  const [major, setMajor] = useState("");
  const [city, setCity] = useState("");
  const [currentJob, setCurrentJob] = useState("");
  const [intendedCourseId, setIntendedCourseId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [status, setStatus] = useState("new");
  const [intentionLevel, setIntentionLevel] = useState("");
  const [remark, setRemark] = useState("");
  const [saving, setSaving] = useState(false);

  // -- Resume upload state --------------------------------------------------
  const [uploading, setUploading] = useState(false);
  const [draftModalOpen, setDraftModalOpen] = useState(false);
  const [draft, setDraft] = useState<LeadDraft | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);

  // Load config
  useEffect(() => {
    const load = async () => {
      try {
        const [src, crs] = await Promise.all([
          configApi.leadSources(),
          configApi.courses(),
        ]);
        setSources(src);
        setCourses(crs);
      } catch {
        // Non-critical; form still works
      }
    };
    load();
  }, []);

  // If upload mode, trigger file input
  useEffect(() => {
    if (uploadMode && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [uploadMode]);

  // -- Handlers --------------------------------------------------------------

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast("请输入姓名", "error");
      return;
    }

    setSaving(true);
    try {
      await leadApi.create({
        name: name.trim(),
        phone: phone.trim() || null,
        wechat: wechat.trim() || null,
        email: email.trim() || null,
        gender: gender || null,
        age: age ? parseInt(age, 10) : null,
        education: education.trim() || null,
        school: school.trim() || null,
        major: major.trim() || null,
        city: city.trim() || null,
        current_job: currentJob.trim() || null,
        intended_course_id: intendedCourseId ? parseInt(intendedCourseId, 10) : null,
        source_id: sourceId ? parseInt(sourceId, 10) : null,
        status: status || "new",
        intention_level: intentionLevel || null,
        remark: remark.trim() || null,
      });
      toast("线索创建成功", "success");
      router.push("/leads");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "创建失败";
      toast(message, "error");
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input so same file can be re-uploaded
    e.target.value = "";

    setUploading(true);
    try {
      const result = await resumeImportApi.upload(file);
      toast("简历解析完成", "success");

      // Fetch the full draft
      const fullDraft = await leadDraftApi.get(result.lead_draft_id);
      setDraft(fullDraft);
      setDraftId(result.lead_draft_id);
      setDraftModalOpen(true);

      // Pre-fill form with draft data
      if (fullDraft.name) setName(fullDraft.name);
      if (fullDraft.phone) setPhone(fullDraft.phone);
      if (fullDraft.wechat) setWechat(fullDraft.wechat);
      if (fullDraft.email) setEmail(fullDraft.email);
      if (fullDraft.gender) setGender(fullDraft.gender);
      if (fullDraft.age) setAge(String(fullDraft.age));
      if (fullDraft.education) setEducation(fullDraft.education);
      if (fullDraft.school) setSchool(fullDraft.school);
      if (fullDraft.major) setMajor(fullDraft.major);
      if (fullDraft.city) setCity(fullDraft.city);
      if (fullDraft.latest_company) setCurrentJob(fullDraft.latest_company);

      // Try to match course suggestion
      if (fullDraft.ai_course_suggestion && courses.length > 0) {
        const matched = courses.find(
          (c) => c.name === fullDraft.ai_course_suggestion,
        );
        if (matched) setIntendedCourseId(String(matched.id));
      }
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
      const result = await leadDraftApi.confirm(draftId, {
        name: name.trim() || null,
        phone: phone.trim() || null,
        wechat: wechat.trim() || null,
        email: email.trim() || null,
        gender: gender || null,
        age: age ? parseInt(age, 10) : null,
        education: education.trim() || null,
        school: school.trim() || null,
        major: major.trim() || null,
        city: city.trim() || null,
        current_job: currentJob.trim() || null,
        intended_course_id: intendedCourseId
          ? parseInt(intendedCourseId, 10)
          : null,
        source_id: sourceId ? parseInt(sourceId, 10) : null,
        remark: remark.trim() || null,
      });
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

  // -- Render ----------------------------------------------------------------

  return (
    <div className="min-h-screen">
      <TopNav currentPath="/leads" />

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">新建线索</h1>
          <Button variant="ghost" onClick={() => router.back()}>
            返回
          </Button>
        </div>

        {/* Upload area */}
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">简历上传</p>
              <p className="mt-0.5 text-xs text-gray-500">
                上传 Word/PDF 简历自动提取信息
              </p>
            </div>
            <div>
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
                {uploading ? "解析中..." : "上传简历"}
              </Button>
            </div>
          </div>
        </Card>

        {/* Manual entry form */}
        <form onSubmit={handleSave}>
          <Card>
            <h2 className="mb-4 text-base font-semibold text-gray-900">
              基本信息
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input
                label="姓名 *"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="请输入姓名"
              />
              <Input
                label="手机号"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="请输入手机号"
              />
              <Input
                label="微信"
                value={wechat}
                onChange={(e) => setWechat(e.target.value)}
                placeholder="请输入微信号"
              />
              <Input
                label="邮箱"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="请输入邮箱"
                type="email"
              />
              <Select
                label="性别"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                options={[
                  { value: "male", label: "男" },
                  { value: "female", label: "女" },
                ]}
                placeholder="请选择性别"
              />
              <Input
                label="年龄"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="请输入年龄"
                type="number"
              />
            </div>
          </Card>

          <Card className="mt-4">
            <h2 className="mb-4 text-base font-semibold text-gray-900">
              教育/职业信息
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input
                label="学历"
                value={education}
                onChange={(e) => setEducation(e.target.value)}
                placeholder="如：本科、大专、硕士"
              />
              <Input
                label="学校"
                value={school}
                onChange={(e) => setSchool(e.target.value)}
                placeholder="请输入学校"
              />
              <Input
                label="专业"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                placeholder="请输入专业"
              />
              <Input
                label="当前城市"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="请输入城市"
              />
              <Input
                label="当前职业"
                value={currentJob}
                onChange={(e) => setCurrentJob(e.target.value)}
                placeholder="请输入当前职业"
              />
            </div>
          </Card>

          <Card className="mt-4">
            <h2 className="mb-4 text-base font-semibold text-gray-900">
              业务信息
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Select
                label="意向课程"
                value={intendedCourseId}
                onChange={(e) => setIntendedCourseId(e.target.value)}
                options={courses.map((c) => ({
                  value: String(c.id),
                  label: c.name,
                }))}
                placeholder="请选择课程"
              />
              <Select
                label="线索来源"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                options={sources.map((s) => ({
                  value: String(s.id),
                  label: s.name,
                }))}
                placeholder="请选择来源"
              />
              <Select
                label="当前状态"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                options={Object.entries(STATUS_LABELS).map(([v, l]) => ({
                  value: v,
                  label: l,
                }))}
              />
              <Select
                label="意向等级"
                value={intentionLevel}
                onChange={(e) => setIntentionLevel(e.target.value)}
                options={Object.entries(INTENTION_LABELS).map(([v, l]) => ({
                  value: v,
                  label: l,
                }))}
                placeholder="请选择意向等级"
              />
              <div className="sm:col-span-2">
                <Textarea
                  label="备注"
                  value={remark}
                  onChange={(e) => setRemark(e.target.value)}
                  placeholder="请输入备注信息"
                />
              </div>
            </div>
          </Card>

          <div className="mt-6 flex gap-3">
            <Button type="submit" loading={saving} size="lg">
              保存
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="lg"
              onClick={() => router.push("/leads")}
            >
              取消
            </Button>
          </div>
        </form>

        {/* Draft confirmation modal */}
        <Modal
          open={draftModalOpen}
          onClose={() => setDraftModalOpen(false)}
          title="简历解析结果"
          size="lg"
        >
          {draft ? (
            <div className="space-y-4">
              {/* AI Summary */}
              {draft.ai_summary && (
                <div className="rounded-lg bg-blue-50 p-3">
                  <p className="text-xs font-medium text-blue-700">AI 分析摘要</p>
                  <p className="mt-1 text-sm text-blue-800">{draft.ai_summary}</p>
                </div>
              )}

              {/* Draft fields */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                {draft.name && (
                  <Field label="姓名" value={draft.name} />
                )}
                {draft.phone && (
                  <Field label="手机号" value={draft.phone} />
                )}
                {draft.email && (
                  <Field label="邮箱" value={draft.email} />
                )}
                {draft.education && (
                  <Field label="学历" value={draft.education} />
                )}
                {draft.school && (
                  <Field label="学校" value={draft.school} />
                )}
                {draft.major && (
                  <Field label="专业" value={draft.major} />
                )}
                {draft.skills && (
                  <div className="col-span-2">
                    <span className="text-gray-500">技能：</span>
                    <span className="text-gray-900">{draft.skills}</span>
                  </div>
                )}
                {draft.ai_course_suggestion && (
                  <Field label="课程建议" value={draft.ai_course_suggestion} />
                )}
              </div>

              <div className="flex gap-3 border-t border-gray-200 pt-4">
                <Button loading={confirming} onClick={handleConfirmDraft}>
                  确认生成线索
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setDraftModalOpen(false)}
                >
                  继续编辑
                </Button>
              </div>
            </div>
          ) : (
            <Loading text="加载草稿..." />
          )}
        </Modal>
      </main>
    </div>
  );
}

// -- Helper -----------------------------------------------------------------

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-500">{label}：</span>
      <span className="text-gray-900">{value}</span>
    </div>
  );
}

export default function NewLeadPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        </div>
      }
    >
      <NewLeadPageInner />
    </Suspense>
  );
}

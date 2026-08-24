"""Integration tests for the v0.2.1 resume batch import API.

Covers requirement scenarios 1-4 and 15-24: file types, mixed batches, partial
failure isolation, duplicate detection, batch confirm idempotency, permissions,
and single-import regression.
"""

from app.models.lead import Lead
from app.models.lead_draft import LeadDraft

RESUME_ZHANGSAN = [
    "个人简历",
    "姓名：张三",
    "性别：男  年龄：26",
    "手机号：13812345678",
    "邮箱：zhangsan@example.com",
    "学历：本科",
    "毕业院校：北京大学",
    "专业：计算机科学与技术",
    "熟悉 Python 与自动化测试",
]

RESUME_LISI = [
    "个人简历",
    "姓名：李四",
    "手机号：13900001111",
    "学历：硕士",
]

RESUME_WANGWU = [
    "个人简历",
    "姓名：王五",
    "手机号：13700002222",
    "学历：大专",
]

# No name label and no usable header name -> needs_review.
RESUME_NO_NAME = [
    "求职意向：测试工程师",
    "手机号：13600003333",
    "学历：本科",
    "熟悉 Java",
]


def items_by_file(detail: dict) -> dict:
    return {item["file_name"]: item for item in detail["items"]}


def get_batch(client, batch_id: int, headers) -> dict:
    response = client.get(
        f"/api/v1/resume-imports/batches/{batch_id}", headers=headers
    )
    body = response.json()
    assert body["success"], body
    return body["data"]


# ---------------------------------------------------------------------------
# Scenarios 1-4 — file types and mixed batches
# ---------------------------------------------------------------------------

def test_single_docx_batch(client, counselor_auth, make_docx, upload_batch):
    """Scenario 1 — a single DOCX."""
    path = make_docx(RESUME_ZHANGSAN, "zhangsan.docx")
    body = upload_batch([path], counselor_auth)
    assert body["success"], body
    assert body["data"]["total"] == 1

    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    assert detail["batch"]["status"] == "ready"
    item = detail["items"][0]
    assert item["status"] == "ready"
    assert item["name"] == "张三"
    assert item["phone"] == "13812345678"
    assert item["education"] == "本科"
    assert item["lead_draft_id"] is not None


def test_single_text_pdf_batch(client, counselor_auth, make_pdf, upload_batch):
    """Scenario 2 — a single text-layer PDF."""
    path = make_pdf(RESUME_LISI, "lisi.pdf")
    body = upload_batch([path], counselor_auth)
    assert body["success"], body

    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    item = detail["items"][0]
    assert item["status"] == "ready"
    assert item["name"] == "李四"
    assert item["phone"] == "13900001111"


def test_multiple_docx_batch(client, counselor_auth, make_docx, upload_batch):
    """Scenario 3 — several DOCX files at once."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "a.docx"),
        make_docx(RESUME_LISI, "b.docx"),
        make_docx(RESUME_WANGWU, "c.docx"),
    ]
    body = upload_batch(paths, counselor_auth)
    assert body["data"]["total"] == 3

    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    assert detail["batch"]["ready_count"] == 3
    assert detail["batch"]["status"] == "ready"
    names = sorted(item["name"] for item in detail["items"])
    assert names == ["张三", "李四", "王五"]


def test_mixed_docx_and_pdf_batch(
    client, counselor_auth, make_docx, make_pdf, upload_batch
):
    """Scenario 4 — DOCX and PDF in the same batch."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "mix_a.docx"),
        make_pdf(RESUME_LISI, "mix_b.pdf"),
    ]
    body = upload_batch(paths, counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)

    assert detail["batch"]["ready_count"] == 2
    by_file = items_by_file(detail)
    assert by_file["mix_a.docx"]["name"] == "张三"
    assert by_file["mix_b.pdf"]["name"] == "李四"


# ---------------------------------------------------------------------------
# Scenario 16 — unsupported file types
# ---------------------------------------------------------------------------

def test_unsupported_file_type_is_rejected_per_file(
    client, counselor_auth, make_docx, make_bogus_file, upload_batch
):
    """Scenario 16 + 17 — a bad file fails alone, the good one still imports."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "good.docx"),
        make_bogus_file("bad.txt"),
    ]
    body = upload_batch(paths, counselor_auth)
    assert body["success"], body

    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    by_file = items_by_file(detail)

    assert by_file["bad.txt"]["status"] == "failed"
    assert by_file["bad.txt"]["error_code"] == "INVALID_FILE_TYPE"
    assert by_file["good.docx"]["status"] == "ready"
    assert detail["batch"]["failed_count"] == 1
    assert detail["batch"]["ready_count"] == 1


def test_scanned_pdf_reports_no_extractable_text(
    client, counselor_auth, make_scanned_pdf, upload_batch
):
    """Image-only PDFs must fail loudly, never be guessed at."""
    path = make_scanned_pdf("scanned.pdf")
    body = upload_batch([path], counselor_auth)

    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    item = detail["items"][0]
    assert item["status"] == "failed"
    assert item["error_code"] == "PDF_NO_EXTRACTABLE_TEXT"
    assert item["name"] is None
    assert item["phone"] is None


# ---------------------------------------------------------------------------
# Scenarios 17-18 — partial success and error isolation
# ---------------------------------------------------------------------------

def test_partial_batch_keeps_every_good_result(
    client, counselor_auth, make_docx, make_pdf, make_scanned_pdf,
    make_bogus_file, upload_batch,
):
    """Scenario 18 — mixed outcomes all survive in one batch."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "p_ok1.docx"),
        make_docx(RESUME_LISI, "p_ok2.docx"),
        make_pdf(RESUME_WANGWU, "p_ok3.pdf"),
        make_docx(RESUME_NO_NAME, "p_review.docx"),
        make_scanned_pdf("p_fail.pdf"),
        make_bogus_file("p_bad.txt"),
    ]
    body = upload_batch(paths, counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)

    assert detail["batch"]["total_files"] == 6
    assert detail["batch"]["ready_count"] == 3
    assert detail["batch"]["needs_review_count"] == 1
    assert detail["batch"]["failed_count"] == 2
    assert detail["batch"]["status"] == "partially_ready"
    # Every uploaded file is still represented.
    assert len(detail["items"]) == 6


def test_missing_name_goes_to_review_not_lead(
    client, counselor_auth, make_docx, upload_batch
):
    """Scenario 13 at API level — no name means no automatic Lead."""
    path = make_docx(RESUME_NO_NAME, "noname.docx")
    body = upload_batch([path], counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)

    item = detail["items"][0]
    assert item["status"] == "needs_review"
    assert item["name"] is None
    assert item["phone"] == "13600003333"


# ---------------------------------------------------------------------------
# Scenario 15 — duplicate phone detection
# ---------------------------------------------------------------------------

def test_existing_phone_marks_duplicate(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Scenario 15 — an existing Lead phone blocks automatic creation."""
    existing = Lead(name="张三（旧）", phone="13812345678", status="new")
    db.add(existing)
    db.commit()
    db.refresh(existing)

    path = make_docx(RESUME_ZHANGSAN, "dup.docx")
    body = upload_batch([path], counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)

    item = detail["items"][0]
    assert item["status"] == "duplicate"
    assert item["duplicate"]["existing_lead_id"] == existing.id
    assert item["duplicate"]["existing_lead_name"] == "张三（旧）"
    assert detail["batch"]["duplicate_count"] == 1
    assert detail["batch"]["ready_count"] == 0


def test_duplicate_is_not_confirmed(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Confirming a batch must never turn a duplicate into a second Lead."""
    db.add(Lead(name="张三（旧）", phone="13812345678", status="new"))
    db.commit()
    before = db.query(Lead).count()

    path = make_docx(RESUME_ZHANGSAN, "dup2.docx")
    body = upload_batch([path], counselor_auth)
    batch_id = body["data"]["batch_id"]

    response = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={},
        headers=counselor_auth,
    )
    result = response.json()
    assert result["success"], result
    assert result["data"]["confirmed_count"] == 0
    assert db.query(Lead).count() == before


def test_duplicate_within_same_batch(
    client, counselor_auth, make_docx, upload_batch
):
    """The same phone twice in one batch must not produce two Leads."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "same_a.docx"),
        make_docx(RESUME_ZHANGSAN, "same_b.docx"),
    ]
    body = upload_batch(paths, counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)

    statuses = sorted(item["status"] for item in detail["items"])
    assert statuses == ["duplicate", "ready"]
    assert detail["items"][1]["duplicate"]["in_batch"] is True


# ---------------------------------------------------------------------------
# Scenarios 19-20 — batch confirm and idempotency
# ---------------------------------------------------------------------------

def test_batch_confirm_creates_leads(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Scenario 19 — confirm turns every ready draft into a Lead."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "c_a.docx"),
        make_docx(RESUME_LISI, "c_b.docx"),
        make_docx(RESUME_NO_NAME, "c_review.docx"),
    ]
    body = upload_batch(paths, counselor_auth)
    batch_id = body["data"]["batch_id"]

    response = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={},
        headers=counselor_auth,
    )
    result = response.json()["data"]

    # The needs_review file is not confirmed.
    assert result["confirmed_count"] == 2
    created_phones = {
        lead.phone
        for lead in db.query(Lead).filter(Lead.id.in_(
            [c["lead_id"] for c in result["created"]]
        )).all()
    }
    assert created_phones == {"13812345678", "13900001111"}

    detail = get_batch(client, batch_id, counselor_auth)
    assert detail["batch"]["confirmed_count"] == 2
    assert detail["batch"]["needs_review_count"] == 1


def test_batch_confirm_is_idempotent(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Scenario 20 (P0) — double-clicking confirm never duplicates Leads."""
    paths = [
        make_docx(RESUME_ZHANGSAN, "i_a.docx"),
        make_docx(RESUME_LISI, "i_b.docx"),
    ]
    body = upload_batch(paths, counselor_auth)
    batch_id = body["data"]["batch_id"]

    first = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={}, headers=counselor_auth,
    ).json()["data"]
    count_after_first = db.query(Lead).count()

    second = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={}, headers=counselor_auth,
    ).json()["data"]

    assert first["confirmed_count"] == 2
    assert second["confirmed_count"] == 0
    assert db.query(Lead).count() == count_after_first

    drafts = db.query(LeadDraft).filter(LeadDraft.batch_id == batch_id).all()
    assert all(d.confirmed_lead_id is not None for d in drafts)
    assert len({d.confirmed_lead_id for d in drafts}) == 2


def test_confirm_rejects_unknown_batch(client, counselor_auth):
    response = client.post(
        "/api/v1/resume-imports/batches/999999/confirm",
        json={}, headers=counselor_auth,
    )
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "BATCH_NOT_FOUND"


# ---------------------------------------------------------------------------
# Human review flow
# ---------------------------------------------------------------------------

def test_review_promotes_draft_to_ready_then_confirms(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Requirement 23 — fixing name + phone makes a draft confirmable."""
    path = make_docx(RESUME_NO_NAME, "r_review.docx")
    body = upload_batch([path], counselor_auth)
    batch_id = body["data"]["batch_id"]

    detail = get_batch(client, batch_id, counselor_auth)
    draft_id = detail["items"][0]["lead_draft_id"]
    assert detail["items"][0]["status"] == "needs_review"

    updated = client.put(
        f"/api/v1/lead-drafts/{draft_id}",
        json={"name": "赵 六", "phone": "138-1234-9999"},
        headers=counselor_auth,
    ).json()
    assert updated["success"], updated
    assert updated["data"]["status"] == "ready"
    assert updated["data"]["name"] == "赵六"       # spacing normalised
    assert updated["data"]["phone"] == "13812349999"  # dashes normalised

    result = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={}, headers=counselor_auth,
    ).json()["data"]
    assert result["confirmed_count"] == 1

    lead = db.query(Lead).filter(Lead.id == result["created"][0]["lead_id"]).first()
    assert lead.name == "赵六"
    assert lead.phone == "13812349999"


def test_review_with_duplicate_phone_marks_duplicate(
    client, counselor_auth, make_docx, upload_batch, db
):
    """Correcting a phone into an existing one must flag, not create."""
    db.add(Lead(name="已有线索", phone="13555556666", status="new"))
    db.commit()

    path = make_docx(RESUME_NO_NAME, "r_dup.docx")
    body = upload_batch([path], counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    draft_id = detail["items"][0]["lead_draft_id"]

    updated = client.put(
        f"/api/v1/lead-drafts/{draft_id}",
        json={"name": "钱七", "phone": "13555556666"},
        headers=counselor_auth,
    ).json()
    assert updated["data"]["status"] == "duplicate"


def test_review_with_incomplete_fields_stays_in_review(
    client, counselor_auth, make_docx, upload_batch
):
    path = make_docx(RESUME_NO_NAME, "r_incomplete.docx")
    body = upload_batch([path], counselor_auth)
    detail = get_batch(client, body["data"]["batch_id"], counselor_auth)
    draft_id = detail["items"][0]["lead_draft_id"]

    updated = client.put(
        f"/api/v1/lead-drafts/{draft_id}",
        json={"name": "孙八", "phone": "12345"},
        headers=counselor_auth,
    ).json()
    assert updated["data"]["status"] == "needs_review"


# ---------------------------------------------------------------------------
# Batch limits
# ---------------------------------------------------------------------------

def test_batch_file_limit_enforced(
    client, counselor_auth, make_docx, upload_batch, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RESUME_BATCH_MAX_FILES", 2)
    paths = [
        make_docx(RESUME_ZHANGSAN, f"limit_{i}.docx") for i in range(3)
    ]
    body = upload_batch(paths, counselor_auth)
    assert body["success"] is False
    assert body["error_code"] == "BATCH_FILE_LIMIT_EXCEEDED"


def test_batch_limits_endpoint(client, counselor_auth):
    body = client.get(
        "/api/v1/resume-imports/batch-limits", headers=counselor_auth
    ).json()
    assert body["success"]
    assert body["data"]["max_files"] == 50
    assert set(body["data"]["allowed_extensions"]) == {".docx", ".pdf"}


# ---------------------------------------------------------------------------
# Scenarios 23-24 — permissions
# ---------------------------------------------------------------------------

def test_counselor_cannot_see_another_counselors_batch(
    client, counselor_auth, other_counselor_auth, make_docx, upload_batch
):
    """Scenario 23 — counselors are scoped to their own batches."""
    path = make_docx(RESUME_ZHANGSAN, "perm.docx")
    body = upload_batch([path], counselor_auth)
    batch_id = body["data"]["batch_id"]

    response = client.get(
        f"/api/v1/resume-imports/batches/{batch_id}", headers=other_counselor_auth
    ).json()
    assert response["success"] is False
    assert response["error_code"] == "FORBIDDEN"


def test_admin_can_see_any_batch(
    client, counselor_auth, admin_auth, make_docx, upload_batch
):
    """Scenario 24 — admin has full visibility."""
    path = make_docx(RESUME_ZHANGSAN, "perm_admin.docx")
    body = upload_batch([path], counselor_auth)
    batch_id = body["data"]["batch_id"]

    response = client.get(
        f"/api/v1/resume-imports/batches/{batch_id}", headers=admin_auth
    ).json()
    assert response["success"] is True
    assert response["data"]["batch"]["id"] == batch_id


def test_batch_requires_authentication(client, make_docx):
    response = client.get("/api/v1/resume-imports/batches/1")
    assert response.status_code in (401, 403)


def test_counselor_owns_leads_created_from_their_batch(
    client, counselor_auth, make_docx, upload_batch, db
):
    path = make_docx(RESUME_ZHANGSAN, "owner.docx")
    body = upload_batch([path], counselor_auth)
    batch_id = body["data"]["batch_id"]

    result = client.post(
        f"/api/v1/resume-imports/batches/{batch_id}/confirm",
        json={}, headers=counselor_auth,
    ).json()["data"]

    lead = db.query(Lead).filter(Lead.id == result["created"][0]["lead_id"]).first()
    me = client.get("/api/v1/auth/me", headers=counselor_auth).json()["data"]
    assert lead.owner_id == me["id"]


# ---------------------------------------------------------------------------
# Batch listing
# ---------------------------------------------------------------------------

def test_batch_list_scoped_by_role(
    client, counselor_auth, other_counselor_auth, make_docx, upload_batch
):
    path = make_docx(RESUME_ZHANGSAN, "list.docx")
    upload_batch([path], counselor_auth)

    mine = client.get(
        "/api/v1/resume-imports/batches", headers=counselor_auth
    ).json()["data"]
    theirs = client.get(
        "/api/v1/resume-imports/batches", headers=other_counselor_auth
    ).json()["data"]

    assert len(mine) >= 1
    assert all(b["id"] not in [m["id"] for m in mine] for b in theirs)

"""Regression tests for the v0.1 single-resume import flow and legacy data.

Requirement 31: batch import must not change how the existing single-file
import, LeadDraft confirmation, or old production drafts behave.
"""

from app.models.import_log import ImportLog
from app.models.lead import Lead
from app.models.lead_draft import LeadDraft

RESUME = [
    "个人简历",
    "姓名：周九",
    "手机号：13611112222",
    "邮箱：zhoujiu@example.com",
    "学历：本科",
    "熟悉 Python",
]


def upload_single(client, path, headers):
    with open(path, "rb") as handle:
        response = client.post(
            "/api/v1/resume-imports",
            files={"file": (path.name, handle, "application/octet-stream")},
            headers=headers,
        )
    return response.json()


# ---------------------------------------------------------------------------
# Scenario 21 — the original single-import flow still works
# ---------------------------------------------------------------------------

def test_single_docx_import_still_works(client, counselor_auth, make_docx):
    path = make_docx(RESUME, "single.docx")
    body = upload_single(client, path, counselor_auth)

    assert body["success"], body
    data = body["data"]
    # The v0.1 response contract is unchanged.
    assert set(data.keys()) == {
        "import_log_id", "lead_draft_id", "parse_status", "draft"
    }
    assert data["draft"]["name"] == "周九"
    assert data["draft"]["phone"] == "13611112222"
    assert data["draft"]["status"] == "pending"


def test_single_import_draft_confirms_to_lead(
    client, counselor_auth, make_docx, db
):
    path = make_docx(RESUME, "single_confirm.docx")
    body = upload_single(client, path, counselor_auth)
    draft_id = body["data"]["lead_draft_id"]

    result = client.post(
        f"/api/v1/lead-drafts/{draft_id}/confirm",
        json={"name": "周九", "phone": "13611112222"},
        headers=counselor_auth,
    ).json()

    assert result["success"], result
    lead = db.query(Lead).filter(Lead.id == result["data"]["lead_id"]).first()
    assert lead.name == "周九"
    assert lead.phone == "13611112222"

    draft = db.query(LeadDraft).filter(LeadDraft.id == draft_id).first()
    assert draft.status == "confirmed"
    assert draft.confirmed_lead_id == lead.id
    # A single import is not part of any batch.
    assert draft.batch_id is None


def test_single_import_confirm_is_not_repeatable(
    client, counselor_auth, make_docx
):
    path = make_docx(RESUME, "single_twice.docx")
    body = upload_single(client, path, counselor_auth)
    draft_id = body["data"]["lead_draft_id"]

    first = client.post(
        f"/api/v1/lead-drafts/{draft_id}/confirm", json={}, headers=counselor_auth
    ).json()
    second = client.post(
        f"/api/v1/lead-drafts/{draft_id}/confirm", json={}, headers=counselor_auth
    ).json()

    assert first["success"] is True
    assert second["success"] is False


def test_single_import_rejects_bad_type(client, counselor_auth, make_bogus_file):
    path = make_bogus_file("single_bad.txt")
    body = upload_single(client, path, counselor_auth)

    assert body["success"] is False
    assert body["error_code"] == "INVALID_FILE_TYPE"


def test_single_import_scanned_pdf_records_reason(
    client, counselor_auth, make_scanned_pdf, db
):
    path = make_scanned_pdf("single_scanned.pdf")
    body = upload_single(client, path, counselor_auth)

    assert body["success"] is True
    log = db.query(ImportLog).filter(
        ImportLog.id == body["data"]["import_log_id"]
    ).first()
    assert log.parse_status == "failed"
    assert log.error_code == "PDF_NO_EXTRACTABLE_TEXT"


# ---------------------------------------------------------------------------
# Scenario 22 — pre-v0.2.1 drafts keep working
# ---------------------------------------------------------------------------

def test_legacy_draft_without_new_columns_confirms(client, counselor_auth, db):
    """A draft written before v0.2.1 has NULL in every new column."""
    me = client.get("/api/v1/auth/me", headers=counselor_auth).json()["data"]

    legacy = LeadDraft(
        name="老草稿",
        phone="13500001234",
        education="本科",
        status="pending",
        created_by=me["id"],
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)

    # Exactly what an old row looks like.
    assert legacy.batch_id is None
    assert legacy.name_confidence is None
    assert legacy.phone_confidence is None
    assert legacy.conflict_flags is None
    assert legacy.duplicate_lead_id is None

    fetched = client.get(
        f"/api/v1/lead-drafts/{legacy.id}", headers=counselor_auth
    ).json()
    assert fetched["success"], fetched
    assert fetched["data"]["name"] == "老草稿"

    result = client.post(
        f"/api/v1/lead-drafts/{legacy.id}/confirm", json={}, headers=counselor_auth
    ).json()
    assert result["success"], result

    lead = db.query(Lead).filter(Lead.id == result["data"]["lead_id"]).first()
    assert lead.name == "老草稿"


def test_legacy_draft_keeps_pending_status_on_update(
    client, counselor_auth, db
):
    """Editing a legacy draft must not flip it into the batch state machine."""
    me = client.get("/api/v1/auth/me", headers=counselor_auth).json()["data"]
    legacy = LeadDraft(
        name="老草稿2", phone="13500009999", status="pending", created_by=me["id"]
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)

    updated = client.put(
        f"/api/v1/lead-drafts/{legacy.id}",
        json={"education": "硕士"},
        headers=counselor_auth,
    ).json()

    assert updated["success"], updated
    assert updated["data"]["status"] == "pending"
    assert updated["data"]["education"] == "硕士"


def test_legacy_draft_discard_still_works(client, counselor_auth, db):
    me = client.get("/api/v1/auth/me", headers=counselor_auth).json()["data"]
    legacy = LeadDraft(name="待丢弃", status="pending", created_by=me["id"])
    db.add(legacy)
    db.commit()
    db.refresh(legacy)

    result = client.post(
        f"/api/v1/lead-drafts/{legacy.id}/discard", headers=counselor_auth
    ).json()
    assert result["success"], result

    db.refresh(legacy)
    assert legacy.status == "discarded"

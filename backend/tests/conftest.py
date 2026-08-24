"""Shared pytest fixtures.

The production database is NEVER touched: this module points DATABASE_URL and
UPLOAD_DIR at a throwaway temp directory *before* any application module is
imported, because `app.database.engine` is built at import time.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# -- Isolate the test environment BEFORE importing the app -------------------
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="jiuwei-crm-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(_TEST_ROOT / "uploads")
os.environ["JWT_SECRET_KEY"] = "test-only-secret"
os.environ["TEMP_FILE_RETENTION_DAYS"] = "0"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    """Remove the temp database and uploads once the run is over."""
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    """A TestClient with the app lifespan (create_all + migrations) executed."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_business_tables(client):
    """Truncate business tables between tests, leaving users in place.

    Test-database only — see the DATABASE_URL override at the top of the file.
    """
    from sqlalchemy import inspect, text

    yield
    existing = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        for table in (
            "lead_drafts",
            "import_logs",
            "resume_import_batches",
            "lead_followups",
            "leads",
        ):
            if table in existing:
                conn.execute(text(f"DELETE FROM {table}"))


def _ensure_user(username: str, role: str, real_name: str) -> int:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            user = User(
                username=username,
                password_hash=get_password_hash("test-password-123"),
                real_name=real_name,
                role=role,
                is_active=1,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return user.id
    finally:
        session.close()


def _token(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-password-123"},
    )
    body = response.json()
    assert body["success"], body
    return body["data"]["access_token"]


@pytest.fixture(scope="session")
def admin_auth(client):
    _ensure_user("test_admin", "admin", "测试管理员")
    return {"Authorization": f"Bearer {_token(client, 'test_admin')}"}


@pytest.fixture(scope="session")
def counselor_auth(client):
    _ensure_user("test_counselor", "counselor", "测试咨询师")
    return {"Authorization": f"Bearer {_token(client, 'test_counselor')}"}


@pytest.fixture(scope="session")
def other_counselor_auth(client):
    _ensure_user("test_counselor2", "counselor", "另一位咨询师")
    return {"Authorization": f"Bearer {_token(client, 'test_counselor2')}"}


# ---------------------------------------------------------------------------
# Test resume builders
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def resume_dir():
    path = _TEST_ROOT / "resumes"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture()
def make_docx(resume_dir):
    """Build a .docx resume from lines of text. Returns its path."""
    from docx import Document

    counter = {"n": 0}

    def _make(lines: list[str], filename: str | None = None) -> Path:
        counter["n"] += 1
        name = filename or f"resume_{counter['n']}.docx"
        doc = Document()
        for line in lines:
            doc.add_paragraph(line)
        target = resume_dir / name
        doc.save(str(target))
        return target

    return _make


@pytest.fixture()
def make_pdf(resume_dir):
    """Build a text-layer .pdf resume from lines of text. Returns its path."""
    import fitz

    counter = {"n": 0}

    def _make(lines: list[str], filename: str | None = None) -> Path:
        counter["n"] += 1
        name = filename or f"resume_{counter['n']}.pdf"
        doc = fitz.open()
        page = doc.new_page()
        y = 60
        for line in lines:
            # china-s is PyMuPDF's built-in Simplified Chinese font.
            page.insert_text((60, y), line, fontname="china-s", fontsize=12)
            y += 20
        target = resume_dir / name
        doc.save(str(target))
        doc.close()
        return target

    return _make


@pytest.fixture()
def make_scanned_pdf(resume_dir):
    """Build a PDF with no text layer, standing in for a scanned resume."""
    import fitz

    counter = {"n": 0}

    def _make(filename: str | None = None) -> Path:
        counter["n"] += 1
        name = filename or f"scanned_{counter['n']}.pdf"
        doc = fitz.open()
        page = doc.new_page()
        # A drawn rectangle produces page content but zero extractable text.
        page.draw_rect(fitz.Rect(50, 50, 400, 500), color=(0, 0, 0), width=2)
        target = resume_dir / name
        doc.save(str(target))
        doc.close()
        return target

    return _make


@pytest.fixture()
def make_bogus_file(resume_dir):
    """Build a file with an unsupported extension."""

    def _make(filename: str = "notes.txt", content: str = "hello") -> Path:
        target = resume_dir / filename
        target.write_text(content, encoding="utf-8")
        return target

    return _make


@pytest.fixture()
def upload_batch(client):
    """POST a list of local paths to the batch endpoint."""

    def _upload(paths, headers) -> dict:
        files = []
        handles = []
        try:
            for path in paths:
                handle = open(path, "rb")
                handles.append(handle)
                files.append(("files", (Path(path).name, handle,
                                        "application/octet-stream")))
            response = client.post(
                "/api/v1/resume-imports/batch", files=files, headers=headers
            )
        finally:
            for handle in handles:
                handle.close()
        return response.json()

    return _upload

"""Smart-import LLM parser (CO-A01): offline-first with heuristic fallback.

The LLM is always stubbed (``import_parser.llm`` monkeypatched) so no test ever
hits the network. Two regimes are covered:

* No key / LLM failure / malformed reply -> deterministic heuristic.
* Stubbed LLM success -> structured candidates in the SAME shape the commit path
  expects (verified end-to-end through the parse -> commit endpoints).
"""
from __future__ import annotations

from app.ai import import_parser, llm
from app.services import imports as svc


def _auth(client, email="owner@example.com", org="Acme"):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner",
            "orgName": org,
        },
    )
    return {"Authorization": f"Bearer {r.json()['token']}"}


# --------------------------------------------------------------------------- #
# Fallback regime (the CI/default path: no API key)
# --------------------------------------------------------------------------- #
def test_no_key_uses_heuristic(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", None)
    raw = "Name,Email\nAda Lovelace,ada@x.com"
    assert import_parser.parse_import(raw) == svc.parse_text(raw)


def test_empty_input_uses_heuristic(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    out = import_parser.parse_import("   ")
    assert out == svc.parse_text("   ")
    assert out["candidates"] == []


def test_llm_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)

    def _boom(*a, **k):
        raise llm.LLMUnavailableError("network down")

    monkeypatch.setattr(llm, "structured_complete", _boom)
    raw = "Name,Email\nAda,ada@x.com"
    out = import_parser.parse_import(raw)
    assert out == svc.parse_text(raw)  # identical heuristic result


def test_malformed_llm_reply_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)
    # Not a list and no candidates/students key -> unusable -> heuristic.
    monkeypatch.setattr(llm, "structured_complete", lambda *a, **k: {"foo": "bar"})
    raw = "Sarah Lee sarah@mail.com 0422 333 444"
    out = import_parser.parse_import(raw)
    assert out == svc.parse_text(raw)


def test_empty_candidate_array_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(llm, "structured_complete", lambda *a, **k: [])
    raw = "Name\nTommy"
    out = import_parser.parse_import(raw)
    assert out == svc.parse_text(raw)


# --------------------------------------------------------------------------- #
# LLM success regime (stubbed) — messy fixtures
# --------------------------------------------------------------------------- #
def _stub_llm(monkeypatch, reply):
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(llm, "structured_complete", lambda *a, **k: reply)


def test_llm_splits_student_and_guardian(monkeypatch):
    _stub_llm(
        monkeypatch,
        [
            {
                "name": "Tommy Smith",
                "email": None,
                "phone": "0400111222",
                "tags": ["maths"],
                "guardians": [
                    {
                        "name": "Jane Smith",
                        "relationship": "mother",
                        "phone": "0400999888",
                    }
                ],
            }
        ],
    )
    out = import_parser.parse_import("any messy roster")
    assert out["source"] == "llm"
    c = out["candidates"][0]
    assert c["name"] == "Tommy Smith"
    assert "0400111222" in c["phone"]
    assert c["tags"] == ["maths"]
    g = c["guardians"][0]
    assert g["name"] == "Jane Smith"
    assert g["relationship"] == "mother"
    assert "0400999888" in g["phone"]
    assert g["isPrimary"] is True
    # Shape is commit-compatible: all heuristic candidate keys present.
    assert set(svc._blank_candidate()).issubset(c.keys())


def test_llm_recurrence_from_chinese_freetext(monkeypatch):
    _stub_llm(
        monkeypatch,
        {
            "students": [
                {
                    "name": "李华",
                    "phone": "0422333444",
                    "scheduleText": "周二周四4-5pm",
                    "recurrence": {
                        "daysOfWeek": ["TU", "TH"],
                        "startTime": "16:00",
                        "endTime": "17:00",
                    },
                }
            ]
        },
    )
    out = import_parser.parse_import("李华 0422333444 周二周四4-5pm")
    c = out["candidates"][0]
    assert c["name"] == "李华"
    assert c["scheduleText"] == "周二周四4-5pm"
    assert c["recurrence"]["daysOfWeek"] == ["TU", "TH"]
    assert c["recurrence"]["startTime"] == "16:00"


def test_llm_dirty_email_is_normalised(monkeypatch):
    _stub_llm(
        monkeypatch,
        [{"name": "Grace Hopper", "email": "contact: grace@navy.mil please"}],
    )
    out = import_parser.parse_import("x")
    assert out["candidates"][0]["email"] == "grace@navy.mil"


def test_llm_missing_name_lowers_confidence(monkeypatch):
    _stub_llm(monkeypatch, [{"name": "", "phone": "0400000000"}])
    out = import_parser.parse_import("0400000000")
    c = out["candidates"][0]
    assert c["confidence"] < 1.0
    assert any("name" in w.lower() for w in c["warnings"])


def test_llm_invalid_status_defaults_active(monkeypatch):
    _stub_llm(monkeypatch, [{"name": "Ada", "status": "nonsense"}])
    out = import_parser.parse_import("x")
    assert out["candidates"][0]["status"] == "active"


def test_llm_garbage_rows_dropped_then_fallback(monkeypatch):
    # A row with no name and no contact is dropped; if nothing remains we fall
    # back to the heuristic rather than return an empty candidate list.
    _stub_llm(monkeypatch, [{"name": "", "email": None, "phone": None}])
    raw = "Name\nReal Person"
    out = import_parser.parse_import(raw)
    assert out == svc.parse_text(raw)


# --------------------------------------------------------------------------- #
# End-to-end: stubbed LLM parse -> commit creates real students (no network)
# --------------------------------------------------------------------------- #
def test_llm_parse_then_commit_creates_students(client, monkeypatch):
    _stub_llm(
        monkeypatch,
        [
            {
                "name": "Tommy Smith",
                "phone": "0400111222",
                "guardians": [{"name": "Jane Smith", "phone": "0400999888"}],
            }
        ],
    )
    h = _auth(client)
    job = client.post(
        "/api/v1/students/import/parse",
        json={"rawInput": "messy roster paste"},
        headers=h,
    ).json()
    assert job["parsed"]["source"] == "llm"

    commit = client.post(
        f"/api/v1/students/import/{job['id']}/commit",
        json={"parsed": job["parsed"]},
        headers=h,
    )
    assert commit.status_code == 200, commit.text
    assert len(commit.json()["parsed"]["createdStudentIds"]) == 1

    students = client.get("/api/v1/students", headers=h).json()["items"]
    assert [s["name"] for s in students] == ["Tommy Smith"]
    guardians = client.get(
        f"/api/v1/guardians?studentId={students[0]['id']}", headers=h
    ).json()["items"]
    assert guardians[0]["name"] == "Jane Smith"

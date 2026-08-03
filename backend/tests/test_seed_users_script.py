"""Tests for scripts/seed_users.py (RC1 Phase 0 — Security Remediation,
Finding 3).

Exercises the script's real seed()/DB-write path, but only against
uniquely-named throwaway accounts created and deleted entirely within
these tests -- the real demo accounts (admin@construction.ai and friends)
are never created, rotated, or otherwise touched, per the sprint's "no
test users without guaranteed cleanup" rule.
"""
import uuid
import pytest

from scripts import seed_users
from tests.conftest import TestingSessionLocal
from app.models.auth import UserAccount


def _cleanup(emails: list[str]) -> None:
    db = TestingSessionLocal()
    try:
        db.query(UserAccount).filter(UserAccount.email.in_(emails)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_no_fixed_password_literal_remains_in_seed_users():
    for entry in seed_users.SEED_USERS:
        assert "password" not in entry
        for value in entry.values():
            assert value != "Admin123!"


def test_refuse_in_production_blocks_by_default(monkeypatch):
    monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "production")
    monkeypatch.delenv("SEED_USERS_ALLOW_PRODUCTION", raising=False)
    with pytest.raises(SystemExit):
        seed_users._refuse_in_production()


def test_refuse_in_production_allows_explicit_override(monkeypatch):
    monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("SEED_USERS_ALLOW_PRODUCTION", "yes")
    seed_users._refuse_in_production()  # must not raise


def test_refuse_in_production_allows_development(monkeypatch):
    monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "development")
    monkeypatch.delenv("SEED_USERS_ALLOW_PRODUCTION", raising=False)
    seed_users._refuse_in_production()  # must not raise


def test_credentials_file_is_the_designated_local_output(tmp_path, monkeypatch):
    target = tmp_path / "creds.local.txt"
    monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", target)
    seed_users._write_credentials_file([("someone@test.local", "abc123xyz")])
    content = target.read_text(encoding="utf-8")
    assert "Never commit" in content
    assert "someone@test.local" in content
    assert "abc123xyz" in content


class TestSeedAgainstThrowawayAccountsOnly:
    def test_created_users_get_distinct_random_passwords_and_must_change_flag(self, tmp_path, monkeypatch):
        suffix = uuid.uuid4().hex[:8]
        fake_users = [
            {"email": f"rc1-seed-test-a-{suffix}@test.local", "full_name": "RC1 Test A", "role": "viewer"},
            {"email": f"rc1-seed-test-b-{suffix}@test.local", "full_name": "RC1 Test B", "role": "viewer"},
        ]
        emails = [u["email"] for u in fake_users]
        monkeypatch.setattr(seed_users, "SEED_USERS", fake_users)
        monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", tmp_path / "creds.local.txt")
        monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "development")
        try:
            seed_users.seed(rotate_existing=False)
            db = TestingSessionLocal()
            try:
                rows = db.query(UserAccount).filter(UserAccount.email.in_(emails)).all()
                assert len(rows) == 2
                for row in rows:
                    assert row.must_change_password is True

                written = (tmp_path / "creds.local.txt").read_text(encoding="utf-8")
                pw_a = next(l for l in written.splitlines() if emails[0] in l).split("\t")[1]
                pw_b = next(l for l in written.splitlines() if emails[1] in l).split("\t")[1]
                assert pw_a != pw_b
                assert len(pw_a) >= 16
            finally:
                db.close()
        finally:
            _cleanup(emails)

    def test_rerun_without_flag_does_not_rotate_existing_credentials(self, tmp_path, monkeypatch):
        suffix = uuid.uuid4().hex[:8]
        email = f"rc1-seed-test-c-{suffix}@test.local"
        fake_users = [{"email": email, "full_name": "RC1 Test C", "role": "viewer"}]
        monkeypatch.setattr(seed_users, "SEED_USERS", fake_users)
        monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", tmp_path / "creds1.local.txt")
        monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "development")
        try:
            seed_users.seed(rotate_existing=False)
            db = TestingSessionLocal()
            try:
                original_hash = db.query(UserAccount).filter(UserAccount.email == email).first().hashed_password
            finally:
                db.close()

            monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", tmp_path / "creds2.local.txt")
            seed_users.seed(rotate_existing=False)  # plain rerun, no flag
            db = TestingSessionLocal()
            try:
                row = db.query(UserAccount).filter(UserAccount.email == email).first()
                assert row.hashed_password == original_hash
            finally:
                db.close()
            # nothing new was issued on the rerun -> no credentials file written
            assert not (tmp_path / "creds2.local.txt").exists()
        finally:
            _cleanup([email])

    def test_rotate_existing_flag_issues_a_new_password(self, tmp_path, monkeypatch):
        suffix = uuid.uuid4().hex[:8]
        email = f"rc1-seed-test-d-{suffix}@test.local"
        fake_users = [{"email": email, "full_name": "RC1 Test D", "role": "viewer"}]
        monkeypatch.setattr(seed_users, "SEED_USERS", fake_users)
        monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", tmp_path / "creds1.local.txt")
        monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "development")
        try:
            seed_users.seed(rotate_existing=False)
            db = TestingSessionLocal()
            try:
                original_hash = db.query(UserAccount).filter(UserAccount.email == email).first().hashed_password
            finally:
                db.close()

            monkeypatch.setattr(seed_users, "CREDENTIALS_OUTPUT_PATH", tmp_path / "creds2.local.txt")
            seed_users.seed(rotate_existing=True)
            db = TestingSessionLocal()
            try:
                row = db.query(UserAccount).filter(UserAccount.email == email).first()
                assert row.hashed_password != original_hash
                assert row.must_change_password is True
            finally:
                db.close()
        finally:
            _cleanup([email])

    def test_production_environment_blocks_seed_entirely(self, monkeypatch):
        monkeypatch.setattr(seed_users.settings, "ENVIRONMENT", "production")
        monkeypatch.delenv("SEED_USERS_ALLOW_PRODUCTION", raising=False)
        with pytest.raises(SystemExit):
            seed_users.seed()

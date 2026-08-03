"""Tests for the Hermes Agent provider adapter.

All tests mock subprocess.run — no live Hermes/Ollama instance is required
for the automated suite.
"""
import json
import subprocess

import pytest

from app.ai.providers.base import (
    LLMProvider,
    LLMRequest,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.providers.hermes import HermesProvider


def _make_provider(**overrides):
    kwargs = dict(
        model="qwen2.5:3b",
        hermes_bin="/fake/path/hermes",
        profile="amad",
        hermes_provider="ollama-launch",
        timeout_seconds=30,
    )
    kwargs.update(overrides)
    return HermesProvider(**kwargs)


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestIsAvailable:
    def test_available_when_binary_exists(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))
        assert provider.is_available() is True

    def test_unavailable_when_binary_missing(self):
        provider = _make_provider(hermes_bin=r"C:\nonexistent\hermes.exe")
        assert provider.is_available() is False

    def test_unavailable_when_not_found_on_path(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        provider = HermesProvider(model="qwen2.5:3b", hermes_bin=None)
        assert provider.is_available() is False

    def test_implements_protocol(self, tmp_path):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))
        assert isinstance(provider, LLMProvider)


class TestGenerateSuccess:
    def test_successful_response_parsing(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            usage_path = args[args.index("--usage-file") + 1]
            with open(usage_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "model": "qwen2.5:3b",
                        "input_tokens": 120,
                        "output_tokens": 30,
                        "completed": True,
                        "failed": False,
                    },
                    f,
                )
            return _FakeCompletedProcess(returncode=0, stdout="The answer is 42.\n")

        monkeypatch.setattr(subprocess, "run", fake_run)

        req = LLMRequest(system_prompt="EVIDENCE:\n[1] PRJ-001", user_prompt="Status?")
        resp = provider.generate(req)

        assert resp.content == "The answer is 42."
        assert resp.provider == "hermes"
        assert resp.model == "qwen2.5:3b"
        assert resp.prompt_tokens == 120
        assert resp.completion_tokens == 30
        assert resp.latency_ms >= 0

    def test_command_never_uses_shell(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))
        captured = {}

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["shell"] = kwargs.get("shell")
            return _FakeCompletedProcess(returncode=0, stdout="ok")

        monkeypatch.setattr(subprocess, "run", fake_run)
        provider.generate(LLMRequest(system_prompt="sys", user_prompt="q"))

        assert captured["shell"] is False
        assert isinstance(captured["args"], list)
        assert "-p" in captured["args"] and "amad" in captured["args"]

    def test_prompt_truncated_when_oversized(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))
        captured = {}

        def fake_run(args, **kwargs):
            captured["prompt"] = args[args.index("-z") + 1]
            return _FakeCompletedProcess(returncode=0, stdout="ok")

        monkeypatch.setattr(subprocess, "run", fake_run)
        huge_evidence = "X" * 50000
        provider.generate(LLMRequest(system_prompt=huge_evidence, user_prompt="q"))

        assert len(captured["prompt"]) < 50000
        assert "truncated" in captured["prompt"]


class TestErrorMapping:
    def test_timeout_maps_to_provider_timeout_error(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args, timeout=30)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderTimeoutError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_connection_failure_maps_to_unavailable(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            return _FakeCompletedProcess(
                returncode=1,
                stderr="hermes -z: agent failed: Connection refused",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderUnavailableError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_missing_binary_raises_unavailable_without_subprocess_call(self, monkeypatch):
        provider = _make_provider(hermes_bin=r"C:\nonexistent\hermes.exe")
        called = {"count": 0}

        def fake_run(*args, **kwargs):
            called["count"] += 1
            return _FakeCompletedProcess(returncode=0, stdout="ok")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderUnavailableError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))
        assert called["count"] == 0

    def test_auth_failure_maps_to_provider_auth_error(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            return _FakeCompletedProcess(
                returncode=1, stderr="hermes -z: agent failed: 401 Unauthorized"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderAuthError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_rate_limit_maps_to_provider_rate_limit_error(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            return _FakeCompletedProcess(
                returncode=1, stderr="hermes -z: agent failed: 429 too many requests"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderRateLimitError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_empty_response_raises_unavailable(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            return _FakeCompletedProcess(returncode=0, stdout="   \n")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderUnavailableError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_generic_failure_maps_to_unavailable(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            return _FakeCompletedProcess(returncode=1, stderr="something unexpected broke")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(ProviderUnavailableError):
            provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))

    def test_missing_usage_file_does_not_crash(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "hermes"
        fake_bin.write_text("")
        provider = _make_provider(hermes_bin=str(fake_bin))

        def fake_run(args, **kwargs):
            # Never writes the usage file at all.
            return _FakeCompletedProcess(returncode=0, stdout="fine")

        monkeypatch.setattr(subprocess, "run", fake_run)
        resp = provider.generate(LLMRequest(system_prompt="s", user_prompt="q"))
        assert resp.content == "fine"
        assert resp.prompt_tokens is None
        assert resp.completion_tokens is None


class TestFactorySelection:
    def setup_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    def teardown_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    def test_hermes_selected_without_api_key(self, monkeypatch):
        from app.ai.providers.factory import get_llm_provider, reset_provider

        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "hermes")
        monkeypatch.setattr("app.config.settings.LLM_API_KEY", None)
        monkeypatch.setattr("app.config.settings.LLM_MODEL", "qwen2.5:3b")
        reset_provider()

        provider = get_llm_provider()
        assert isinstance(provider, HermesProvider)
        assert provider.provider_name == "hermes"
        assert provider.model_name == "qwen2.5:3b"

    def test_hermes_branch_evaluated_before_mock_fallback(self, monkeypatch):
        """Regression guard: `provider == hermes` must not fall through to
        the generic `provider == mock or not api_key` branch just because
        no API key is set — Hermes never needs one locally."""
        from app.ai.providers.factory import get_llm_provider, reset_provider
        from app.ai.providers.fake import FakeLLMProvider

        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "hermes")
        monkeypatch.setattr("app.config.settings.LLM_API_KEY", "")
        reset_provider()

        provider = get_llm_provider()
        assert not isinstance(provider, FakeLLMProvider)
        assert isinstance(provider, HermesProvider)

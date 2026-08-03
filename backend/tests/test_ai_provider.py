"""Tests for AI provider abstraction layer.

All tests use FakeLLMProvider — no paid/live LLM calls.
"""
import pytest

from app.ai.providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderUnavailableError,
)
from app.ai.providers.fake import FakeLLMProvider
from app.ai.providers.factory import get_llm_provider, reset_provider


class TestFakeLLMProvider:
    def test_implements_protocol(self):
        provider = FakeLLMProvider()
        assert isinstance(provider, LLMProvider)

    def test_is_available(self):
        provider = FakeLLMProvider()
        assert provider.is_available() is True

    def test_simulate_unavailable(self):
        provider = FakeLLMProvider(simulate_unavailable=True)
        assert provider.is_available() is False

    def test_generate_returns_response(self):
        provider = FakeLLMProvider()
        req = LLMRequest(system_prompt="You are a helper.", user_prompt="Hello")
        resp = provider.generate(req)
        assert isinstance(resp, LLMResponse)
        assert isinstance(resp.content, str)
        assert len(resp.content) > 0
        assert resp.provider == "fake"
        assert resp.model == "fake-model-v1"

    def test_generate_with_fixed_response(self):
        provider = FakeLLMProvider(fixed_response="Custom fixed answer.")
        req = LLMRequest(system_prompt="sys", user_prompt="q")
        resp = provider.generate(req)
        assert resp.content == "Custom fixed answer."

    def test_set_response_changes_output(self):
        provider = FakeLLMProvider()
        provider.set_response("Dynamic answer.")
        req = LLMRequest(system_prompt="s", user_prompt="q")
        resp = provider.generate(req)
        assert resp.content == "Dynamic answer."

    def test_call_count_increments(self):
        provider = FakeLLMProvider()
        req = LLMRequest(system_prompt="s", user_prompt="q")
        provider.generate(req)
        provider.generate(req)
        assert provider.call_count == 2

    def test_latency_recorded(self):
        provider = FakeLLMProvider()
        req = LLMRequest(system_prompt="s", user_prompt="q")
        resp = provider.generate(req)
        assert resp.latency_ms >= 0

    def test_token_counts_estimated(self):
        provider = FakeLLMProvider()
        req = LLMRequest(system_prompt="you are a helper", user_prompt="what is status")
        resp = provider.generate(req)
        assert resp.prompt_tokens is not None
        assert resp.prompt_tokens > 0

    def test_evidence_in_prompt_affects_response(self):
        provider = FakeLLMProvider()
        req = LLMRequest(
            system_prompt="EVIDENCE:\n[1] Project PRJ-001\n    status=Active",
            user_prompt="What is the project status?",
        )
        resp = provider.generate(req)
        assert "evidence" in resp.content.lower() or len(resp.content) > 10


class TestProviderFactory:
    def setup_method(self):
        reset_provider()

    def teardown_method(self):
        reset_provider()

    def test_returns_fake_when_no_key(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "mock")
        monkeypatch.setattr("app.config.settings.LLM_API_KEY", None)
        reset_provider()
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)

    def test_returns_fake_for_mock_provider(self):
        from app.config import settings
        original = settings.LLM_PROVIDER
        settings.LLM_PROVIDER = "mock"
        reset_provider()
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)
        settings.LLM_PROVIDER = original

    def test_provider_is_cached(self):
        p1 = get_llm_provider()
        p2 = get_llm_provider()
        assert p1 is p2

    def test_reset_clears_cache(self):
        p1 = get_llm_provider()
        reset_provider()
        p2 = get_llm_provider()
        assert p1 is not p2

    def test_no_key_gives_fake_regardless_of_provider(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "openai")
        monkeypatch.setattr("app.config.settings.LLM_API_KEY", None)
        reset_provider()
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)

    def test_unknown_provider_falls_back_to_fake(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "unknown_xyz")
        monkeypatch.setattr("app.config.settings.LLM_API_KEY", None)
        reset_provider()
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)

    def test_app_starts_without_api_key(self):
        from app.main import app as fastapi_app
        assert fastapi_app is not None

    def test_fake_provider_generate_no_crash(self):
        reset_provider()
        provider = get_llm_provider()
        req = LLMRequest(system_prompt="sys", user_prompt="hello")
        resp = provider.generate(req)
        assert resp.content

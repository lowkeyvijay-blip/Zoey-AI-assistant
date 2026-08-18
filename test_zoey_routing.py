"""Deterministic tests for Zoey routing and Ollama generation.

These tests never hit the network: the orchestrator is stubbed and
the LLM methods are monkeypatched. They verify the latency fixes:

1. conversation/tool intents skip analyze_memory() (single LLM call)
2. memory intents still run memory detection
3. every generation payload carries keep_alive + num_predict
"""

import json

import pytest

from core.zoey import Zoey


class StubOrchestrator:

    def __init__(self, intent):
        self.intent = intent

    def handle(self, message):
        return {
            "type": "conversation",
            "message": message,
            "intent": self.intent,
            "confidence": 1.0,
        }


class FakeUrlOpen:
    """Context manager response stand-in for urllib.request.urlopen."""

    def __init__(self):
        self.body = None

    def __call__(self, request, timeout):
        self.body = request.data
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps({"response": "ok"}).encode("utf-8")


@pytest.fixture
def zoey(monkeypatch):
    instance = Zoey(orchestrator=StubOrchestrator("conversation"))

    calls = {
        "analyze_memory": 0,
        "remember": 0,
        "ask_ai": 0,
    }

    def fake_analyze_memory(message):
        calls["analyze_memory"] += 1
        return {
            "content": "prefers dark mode",
            "type": "preference",
            "importance": 0.5,
        }

    def fake_remember(content, memory_type, importance):
        calls["remember"] += 1
        return "stored"

    def fake_ask_ai(message):
        calls["ask_ai"] += 1
        return "canned answer"

    monkeypatch.setattr(instance, "analyze_memory", fake_analyze_memory)
    monkeypatch.setattr(instance, "remember", fake_remember)
    monkeypatch.setattr(instance, "ask_ai", fake_ask_ai)

    return instance, calls


def test_conversation_intent_skips_memory_detection(zoey):
    instance, calls = zoey
    instance.orchestrator.intent = "conversation"

    result = instance.respond_structured("hello there")

    assert result["type"] == "text"
    assert result["content"] == "canned answer"
    assert calls["analyze_memory"] == 0
    assert calls["remember"] == 0
    assert calls["ask_ai"] == 1


def test_tool_intent_skips_memory_detection(zoey):
    instance, calls = zoey
    instance.orchestrator.intent = "tool"

    result = instance.respond_structured("open notepad")

    assert result["content"] == "canned answer"
    assert calls["analyze_memory"] == 0
    assert calls["remember"] == 0
    assert calls["ask_ai"] == 1


def test_memory_intent_still_runs_memory_detection(zoey):
    instance, calls = zoey
    instance.orchestrator.intent = "memory"

    result = instance.respond_structured("I prefer dark mode")

    assert result["content"] == "canned answer"
    assert calls["analyze_memory"] == 1
    assert calls["remember"] == 1
    assert calls["ask_ai"] == 1


@pytest.mark.parametrize("module_path", [
    "core.zoey",
    "core.intent",
    "core.planner",
    "core.agent_loop",
])
def test_generation_payload_has_keep_alive_and_num_predict(
    monkeypatch,
    module_path,
):
    module = __import__(module_path, fromlist=["_generate"])

    fake = FakeUrlOpen()
    monkeypatch.setattr(module.urllib.request, "urlopen", fake)

    if module_path == "core.zoey":
        getter = Zoey.__new__(Zoey)._generate
    elif module_path == "core.intent":
        getter = module.IntentClassifier()._generate
    elif module_path == "core.planner":
        getter = module.Planner()._generate
    elif module_path == "core.agent_loop":
        getter = module.AgentLoop().ask_model

    getter("test prompt")

    payload = json.loads(fake.body.decode("utf-8"))
    assert payload["keep_alive"] == "30m"
    assert payload["num_predict"] == 512

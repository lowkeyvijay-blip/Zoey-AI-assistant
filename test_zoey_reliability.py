"""Reliability tests for Zoey's V2.1 fast paths and context.

All tests are deterministic: the orchestrator and LLM calls are
stubbed, so nothing here touches Ollama or the network.
"""

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


class RecordingZoey(Zoey):

    def __init__(self, intent="conversation"):
        super().__init__(orchestrator=StubOrchestrator(intent))
        self.llm_calls = 0

    def _generate(self, prompt):
        self.llm_calls += 1
        return f"llm answer {self.llm_calls}"


@pytest.fixture
def zoey():
    instance = RecordingZoey()
    yield instance


class TestCalculatorFastPath:

    def test_goal_arithmetic_never_reaches_llm(self, zoey):
        result = zoey.respond_structured(
            "₹25,00,000 / ₹85,000"
        )

        assert zoey.llm_calls == 0
        assert "2500000 / 85000" in result["content"]
        assert "29.411765" in result["content"]

    def test_simple_math_fast_path(self, zoey):
        result = zoey.respond_structured("what is 12 + 8")

        assert zoey.llm_calls == 0
        assert result["content"] == "12 + 8 = 20"

    def test_last_calculation_stored(self, zoey):
        zoey.respond_structured("100 * 3")

        assert zoey._last_calculation is not None
        assert zoey._last_calculation["result"] == 300

    def test_conversation_without_numbers_uses_llm(self, zoey):
        zoey.respond_structured("hello there")

        assert zoey.llm_calls == 1

    def test_plain_number_mention_is_not_math(self, zoey):
        zoey.respond_structured("I have 2 meetings today")

        assert zoey.llm_calls == 1

    def test_non_math_question_not_hijacked(self, zoey):
        result = zoey.respond_structured("what is your name?")

        assert zoey.llm_calls == 1
        assert "your name" not in result["content"]


class TestTimeFastPath:

    @pytest.mark.parametrize("question", [
        "what time is it?",
        "what's the date today?",
        "what day is it",
        "what is the time right now",
    ])
    def test_time_questions_answered_from_clock(self, zoey, question):
        result = zoey.respond_structured(question)

        assert zoey.llm_calls == 0
        assert "It's" in result["content"]

    def test_deadline_word_does_not_trigger(self, zoey):
        zoey.respond_structured("how do I stay motivated all the time?")

        assert zoey.llm_calls >= 1


class TestHistoryAndContext:

    def test_history_records_turns(self, zoey):
        zoey.respond_structured("hello there")
        zoey.respond_structured("tell me a joke")

        speakers = [speaker for speaker, _ in zoey._history]

        assert speakers.count("USER") == 2
        assert speakers.count("ZOEY") == 2

    def test_ask_ai_prompt_contains_history_and_clock(self, zoey):
        zoey.respond_structured("hello there")

        prompt_holder = {}

        def fake_generate(prompt):
            prompt_holder["prompt"] = prompt
            zoey.llm_calls += 1
            return "second answer"

        zoey._generate = fake_generate

        zoey.ask_ai("what did I just say?")

        prompt = prompt_holder["prompt"]

        assert "RECENT CONVERSATION" in prompt
        assert "hello there" in prompt
        assert "CURRENT DATE/TIME" in prompt

    def test_ask_ai_prompt_includes_last_calculation(self, zoey):
        zoey.respond_structured("100 * 3")

        prompt_holder = {}

        def fake_generate(prompt):
            prompt_holder["prompt"] = prompt
            return "answer"

        zoey._generate = fake_generate

        zoey.ask_ai("you messed up that calculation")

        prompt = prompt_holder["prompt"]

        assert "LAST CALCULATION" in prompt
        assert "= 300" in prompt


class TestMemoryParallelism:

    def test_memory_intent_runs_analysis_alongside_response(self, monkeypatch):
        instance = Zoey(orchestrator=StubOrchestrator("memory"))

        events = []

        def fake_analyze(message):
            events.append("analyze_start")
            events.append("analyze_done")
            return None

        def fake_ask_ai(message):
            events.append("ask_ai")
            return "canned"

        monkeypatch.setattr(instance, "analyze_memory", fake_analyze)
        monkeypatch.setattr(instance, "ask_ai", fake_ask_ai)

        result = instance.respond_structured("I prefer dark mode")

        assert result["content"] == "canned"
        # ask_ai must start before analysis finishes (parallel),
        # and both must run exactly once.
        assert events.count("analyze_start") == 1
        assert events.count("ask_ai") == 1

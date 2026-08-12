from core.intent import IntentClassifier


class ScriptedClassifier(IntentClassifier):

    def __init__(self, responses=None, threshold=0.7):
        super().__init__(threshold=threshold)
        self.responses = list(responses or [])

    def _generate(self, prompt):
        if not self.responses:
            raise RuntimeError("no scripted response left")
        return self.responses.pop(0)


def verify(condition: bool, message: str):
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"  PASS: {message}")


def main():
    print("\nPHASE 9.2 TEST: INTENT CLASSIFIER (deterministic)\n")
    print("=" * 60)

    print("\nTEST 1: GOAL WITH VALID JSON")

    classifier = ScriptedClassifier([(
        '{"intent": "goal", '
        '"goal": "Finish Zoey today", '
        '"confidence": 0.9}'
    )])

    result = classifier.classify("I want to finish Zoey today")

    verify(
        result["intent"] == "goal",
        "natural goal is classified as goal"
    )
    verify(
        result["goal"] == "Finish Zoey today",
        "the cleaned goal is extracted"
    )
    verify(
        result["confidence"] == 0.9,
        "confidence is preserved"
    )

    print("\nTEST 2: MARKDOWN CODE FENCES ARE STRIPPED")

    classifier = ScriptedClassifier([(
        "```json\n"
        '{"intent": "goal", '
        '"goal": "Prepare for the exam", '
        '"confidence": 0.85}\n'
        "```"
    )])

    result = classifier.classify("Help me prepare for the exam")

    verify(
        result["intent"] == "goal",
        "fenced goal JSON is still parsed"
    )
    verify(
        result["goal"] == "Prepare for the exam",
        "fenced goal text is extracted"
    )

    print("\nTEST 3: LOW CONFIDENCE GOAL IS SAFE")

    classifier = ScriptedClassifier([(
        '{"intent": "goal", '
        '"goal": "Something vague", '
        '"confidence": 0.5}'
    )])

    result = classifier.classify(
        "I think maybe I should do something"
    )

    verify(
        result["intent"] == "conversation",
        "low-confidence goal stays conversation"
    )
    verify(
        result["goal"] is None,
        "the goal is cleared for low confidence"
    )
    verify(
        result["confidence"] == 0.5,
        "the raw confidence is still reported"
    )

    print("\nTEST 4: GOAL AT THE THRESHOLD BOUNDARY")

    classifier = ScriptedClassifier([(
        '{"intent": "goal", '
        '"goal": "Finish the report", '
        '"confidence": 0.7}'
    )])

    result = classifier.classify("I want to finish the report")

    verify(
        result["intent"] == "goal",
        "confidence equal to threshold is accepted"
    )

    print("\nTEST 5: MISSING GOAL TEXT IS NOT A GOAL")

    classifier = ScriptedClassifier([(
        '{"intent": "goal", "confidence": 0.9}'
    )])

    result = classifier.classify("I want something")

    verify(
        result["intent"] == "conversation",
        "goal with no goal text stays conversation"
    )

    print("\nTEST 6: EMPTY GOAL TEXT IS NOT A GOAL")

    classifier = ScriptedClassifier([(
        '{"intent": "goal", "goal": "   ", '
        '"confidence": 0.9}'
    )])

    result = classifier.classify("I want something")

    verify(
        result["intent"] == "conversation",
        "whitespace-only goal stays conversation"
    )

    print("\nTEST 7: TOOL INTENT IS NOT A GOAL")

    classifier = ScriptedClassifier([(
        '{"intent": "tool", "goal": null, '
        '"confidence": 0.95}'
    )])

    result = classifier.classify("Open Notepad")

    verify(
        result["intent"] == "tool",
        "tool command keeps its tool intent"
    )
    verify(
        result["goal"] is None,
        "tool command is not rewritten as a goal"
    )

    print("\nTEST 8: MEMORY INTENT IS NOT A GOAL")

    classifier = ScriptedClassifier([(
        '{"intent": "memory", "goal": null, '
        '"confidence": 0.95}'
    )])

    result = classifier.classify(
        "I prefer working at night"
    )

    verify(
        result["intent"] == "memory",
        "memory statement keeps its memory intent"
    )
    verify(
        result["goal"] is None,
        "memory statement is not rewritten as a goal"
    )

    print("\nTEST 9: QUESTION STAYS CONVERSATION")

    classifier = ScriptedClassifier([(
        '{"intent": "conversation", "goal": null, '
        '"confidence": 0.99}'
    )])

    result = classifier.classify(
        "What's the capital of France?"
    )

    verify(
        result["intent"] == "conversation",
        "question is classified as conversation"
    )

    print("\nTEST 10: INVALID JSON IS SAFE")

    classifier = ScriptedClassifier([
        "this is not json"
    ])

    result = classifier.classify("I want to build a website")

    verify(
        result["intent"] == "conversation",
        "invalid JSON falls back to conversation"
    )

    print("\nTEST 11: NON-DICT JSON IS SAFE")

    classifier = ScriptedClassifier([
        '["goal", "conversation"]'
    ])

    result = classifier.classify("I want to build a website")

    verify(
        result["intent"] == "conversation",
        "non-dict JSON falls back to conversation"
    )

    print("\nTEST 12: UNKNOWN INTENT IS SAFE")

    classifier = ScriptedClassifier([(
        '{"intent": "planning", "goal": null, '
        '"confidence": 0.9}'
    )])

    result = classifier.classify("I want to build a website")

    verify(
        result["intent"] == "conversation",
        "unknown intent falls back to conversation"
    )

    print("\nTEST 13: CLASSIFIER EXCEPTION IS SAFE")

    classifier = ScriptedClassifier([])

    result = classifier.classify("I want to build a website")

    verify(
        result["intent"] == "conversation",
        "an exception falls back to conversation"
    )

    print("\nTEST 14: CONFIDENCE IS CLAMPED")

    classifier = ScriptedClassifier([(
        '{"intent": "conversation", "goal": null, '
        '"confidence": 1.7}'
    )])

    result = classifier.classify("hello")

    verify(
        result["confidence"] == 1.0,
        "confidence above 1.0 is clamped to 1.0"
    )

    classifier = ScriptedClassifier([(
        '{"intent": "conversation", "goal": null, '
        '"confidence": -0.4}'
    )])

    result = classifier.classify("hello")

    verify(
        result["confidence"] == 0.0,
        "confidence below 0.0 is clamped to 0.0"
    )

    print("\nTEST 15: INVALID MESSAGE INPUT")

    classifier = ScriptedClassifier([])

    for bad in (None, "", "   ", 42):
        result = classifier.classify(bad)
        verify(
            result["intent"] == "conversation",
            f"classify({bad!r}) stays conversation"
        )

    print("\nTEST 16: QUOTED 'null' GOAL IS REJECTED")

    classifier = ScriptedClassifier([(
        '{"intent": "memory", "goal": "null", '
        '"confidence": 0.9}'
    )])

    result = classifier.classify("I prefer working at night")

    verify(
        result["intent"] == "memory",
        "quoted-null goal does not break memory intent"
    )
    verify(
        result["goal"] is None,
        "the literal string 'null' is treated as no goal"
    )

    classifier = ScriptedClassifier([(
        '{"intent": "goal", "goal": "null", '
        '"confidence": 0.9}'
    )])

    result = classifier.classify("I want something")

    verify(
        result["intent"] == "conversation",
        "goal intent with quoted-null goal stays conversation"
    )

    print("\n" + "=" * 60)
    print("PHASE 9.2 CLASSIFIER TESTS PASSED")


if __name__ == "__main__":
    main()

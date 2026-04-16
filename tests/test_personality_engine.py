from jarvis.modules.ai.personality_engine import PersonalityEngine


def test_personality_mode_changes_prefix() -> None:
    engine = PersonalityEngine()
    engine.set_mode("casual")
    assert engine.format_response("Ready.").startswith("Sure thing!")

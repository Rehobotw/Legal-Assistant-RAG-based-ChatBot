from app.services.rag.pipeline import _extract_decision


def test_fallback_holding_uses_the_decision_section_only() -> None:
    content = "facts and arguments\n\nውሳኔ\nየፍርድ ቤቱ ውሳኔ ተሽሯል።"

    assert "የፍርድ ቤቱ ውሳኔ ተሽሯል።" in _extract_decision(content)

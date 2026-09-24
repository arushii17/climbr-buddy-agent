from tools.lead_scorer import LeadScorerTool


class DummyLogger:
    def log(self, stage, message):
        pass


def test_high_quality_lead():
    scorer = LeadScorerTool(
        DummyLogger()
    )

    lead = {
        "company": "Example SaaS",
        "is_relevant_business": True,
        "has_digital_presence": True,
        "growth_signal": True,
        "service_need": True,
        "evidence": [
            "Evidence one",
            "Evidence two",
        ],
    }

    result = scorer.score(lead)

    assert result["score"] == 100


def test_low_evidence_lead():
    scorer = LeadScorerTool(
        DummyLogger()
    )

    lead = {
        "company": "Example",
        "is_relevant_business": True,
        "has_digital_presence": False,
        "growth_signal": False,
        "service_need": False,
        "evidence": [],
    }

    result = scorer.score(lead)

    assert result["score"] == 25


def test_score_never_exceeds_100():
    scorer = LeadScorerTool(
        DummyLogger()
    )

    lead = {
        "company": "Example",
        "is_relevant_business": True,
        "has_digital_presence": True,
        "growth_signal": True,
        "service_need": True,
        "evidence": [
            "One",
            "Two",
            "Three",
        ],
    }

    result = scorer.score(lead)

    assert result["score"] <= 100
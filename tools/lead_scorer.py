class LeadScorerTool:
    name = "lead_scorer"

    def __init__(self, logger):
        self.logger = logger

    def score(self, lead):
        company = lead.get(
            "company",
            "Unknown",
        )

        self.logger.log(
            "TOOL",
            f"Scoring lead: {company}",
        )

        score = 0
        reasons = []

        # Core business relevance
        if lead.get("is_relevant_business"):
            score += 25
            reasons.append(
                "Business fits Climbr's target market."
            )

        # Active digital footprint
        if lead.get("has_digital_presence"):
            score += 15
            reasons.append(
                "Company has an established digital presence."
            )

        # Observable growth signal
        if lead.get("growth_signal"):
            score += 25
            reasons.append(
                "Public evidence contains a growth signal."
            )

        # Evidence-backed agency need
        if lead.get("service_need"):
            score += 25
            reasons.append(
                "Evidence suggests a potential need "
                "for digital agency services."
            )

        # Evidence quality
        evidence_count = len(
            lead.get("evidence", [])
        )

        if evidence_count >= 2:
            score += 10
            reasons.append(
                "Multiple supporting evidence points "
                "were identified."
            )

        # Confidence adjustment
        confidence = (
            lead.get("confidence", "")
            .strip()
            .lower()
        )

        if confidence == "low":
            score -= 10
            reasons.append(
                "Score reduced because evidence "
                "confidence is low."
            )

        elif confidence == "medium":
            score -= 5
            reasons.append(
                "Score slightly reduced because "
                "evidence confidence is moderate."
            )

        score = max(
            0,
            min(score, 100),
        )

        return {
            "score": score,
            "score_reasons": reasons,
        }
from .inference import clinical_risk_score


def route_clinical_input(payload):
    """Map explicit, clinician-entered warning flags to a review queue; never diagnose."""
    if not isinstance(payload, dict):
        raise ValueError("Clinical payload must be a dictionary")
    if any(key in payload for key in ("symptoms", "vitals", "metrics", "clinical_summary")):
        result = clinical_risk_score(payload)
        return {
            **result,
            "reasons": result.get("risk_factors", ["clinical_review_requested"]),
            "decision_support_only": True,
            "diagnosis": None,
            "requires_clinician_review": True,
        }

    allowed = {"red_flag", "urgent_review", "routine_review", "mobility_observations"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unsupported clinical routing fields: {', '.join(sorted(unknown))}")
    red_flag = payload.get("red_flag", False)
    urgent_review = payload.get("urgent_review", False)
    routine_review = payload.get("routine_review", False)
    if not all(isinstance(flag, bool) for flag in (red_flag, urgent_review, routine_review)):
        raise ValueError("Routing flags must be booleans")

    if red_flag:
        decision = {"route": "immediate_clinician_review", "priority": "immediate", "reasons": ["red_flag_submitted_by_clinician"]}
    elif urgent_review:
        decision = {"route": "urgent_clinician_review", "priority": "urgent", "reasons": ["urgent_review_submitted_by_clinician"]}
    else:
        decision = {"route": "routine_clinician_review", "priority": "routine", "reasons": ["routine_review_requested" if routine_review else "no_urgency_flag_submitted"]}

    result = {
        **decision,
        "decision_support_only": True,
        "diagnosis": None,
        "requires_clinician_review": True,
    }
    observations = payload.get("mobility_observations")
    if observations is not None:
        from .biomechanics import summarize_landmarks

        result["biomechanics"] = summarize_landmarks(observations)
    return result

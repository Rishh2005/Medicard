from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    route: str
    priority: str
    reasons: tuple[str, ...]


def route_clinical_input(payload):
    """Map explicit, clinician-entered warning flags to a review queue; never diagnose."""
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
        decision = Route("immediate_clinician_review", "immediate", ("red_flag_submitted_by_clinician",))
    elif urgent_review:
        decision = Route("urgent_clinician_review", "urgent", ("urgent_review_submitted_by_clinician",))
    else:
        reasons = ("routine_review_requested",) if routine_review else ("no_urgency_flag_submitted",)
        decision = Route("routine_clinician_review", "routine", reasons)
    result = {
        "route": decision.route,
        "priority": decision.priority,
        "reasons": list(decision.reasons),
        "decision_support_only": True,
        "diagnosis": None,
        "requires_clinician_review": True,
    }
    observations = payload.get("mobility_observations")
    if observations is not None:
        from .biomechanics import summarize_landmarks

        result["biomechanics"] = summarize_landmarks(observations)
    return result

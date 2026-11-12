import math
from typing import Any, Dict, Iterable, List, Optional


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_symptoms(symptoms):
    if not symptoms:
        return []
    if isinstance(symptoms, str):
        return [part.strip().lower() for part in symptoms.split(",") if part.strip()]
    if isinstance(symptoms, list):
        return [str(item).strip().lower() for item in symptoms if str(item).strip()]
    return [str(symptoms).lower()]


def clinical_risk_score(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = payload or {}
    symptoms = _normalise_symptoms(payload.get("symptoms"))
    vitals = payload.get("vitals") or {}
    metrics = payload.get("metrics") or {}
    red_flag = bool(payload.get("red_flag") or payload.get("emergency") or any(item in symptoms for item in ["chest pain", "shortness of breath", "severe bleeding", "syncope", "unresponsive"])))

    risk = 0.24
    if red_flag:
        risk += 0.45
    if "cardiac" in symptoms or "chest pain" in symptoms:
        risk += 0.19
    if "stroke" in symptoms or "neurological" in symptoms or "weakness" in symptoms:
        risk += 0.18
    if "orthopedic" in symptoms or "fracture" in symptoms or "joint pain" in symptoms:
        risk += 0.15
    if "fever" in symptoms or "infection" in symptoms:
        risk += 0.12

    heart_rate = _to_float(vitals.get("heart_rate"))
    oxygen = _to_float(vitals.get("oxygen_sat"))
    systolic = _to_float(vitals.get("systolic_bp"))
    if heart_rate > 120:
        risk += 0.12
    if oxygen < 92:
        risk += 0.18
    if systolic > 160 or systolic < 90:
        risk += 0.10
    if metrics.get("triage_score") is not None:
        risk += min(0.25, max(0.0, _to_float(metrics["triage_score"]) / 100.0 * 0.25))

    risk = max(0.05, min(0.98, risk))
    if red_flag or risk >= 0.7:
        route = "Emergency Triage"
        priority = "immediate"
        specialist = "Emergency Medicine"
    elif risk >= 0.45:
        route = "Cardiology"
        priority = "urgent"
        specialist = "Cardiology"
    elif risk >= 0.25:
        route = "General Medicine"
        priority = "standard"
        specialist = "General Medicine"
    else:
        route = "General Medicine"
        priority = "routine"
        specialist = "General Medicine"

    risk_factors = []
    if red_flag:
        risk_factors.append("red_flag_symptoms")
    if heart_rate > 120:
        risk_factors.append("tachycardia")
    if oxygen < 92:
        risk_factors.append("hypoxemia")
    if systolic > 160 or systolic < 90:
        risk_factors.append("blood_pressure_out_of_range")
    if symptoms:
        risk_factors.extend(symptoms[:3])
    if not risk_factors:
        risk_factors.append("routine_screening")

    return {
        "route": route,
        "priority": priority,
        "recommended_specialist": specialist,
        "confidence": round(min(0.99, max(0.55, risk)), 3),
        "risk_score": round(risk, 3),
        "risk_factors": risk_factors[:6],
        "decision_support_only": True,
        "diagnosis": None,
        "requires_clinician_review": True,
    }

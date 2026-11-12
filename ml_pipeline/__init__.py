def mask_patient(patient):
    """Return a display-safe Patient dict without identifiers or contact details."""
    masked = dict(patient)
    for field in ("id", "identifier", "telecom", "address", "photo", "contact", "communication"):
        masked.pop(field, None)
    if "name" in masked:
        masked["name"] = [{"text": "Protected"}]
    return masked

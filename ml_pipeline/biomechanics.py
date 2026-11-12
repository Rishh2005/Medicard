import math


def summarize_landmarks(observations):
    """Compute geometric summaries from normalized 2D landmark coordinates."""
    if not isinstance(observations, list) or len(observations) < 3 or len(observations) > 100:
        raise ValueError("mobility_observations must contain 3 to 100 landmarks")
    points = []
    for point in observations:
        if not isinstance(point, dict) or set(point) != {"x", "y"}:
            raise ValueError("Each landmark must contain only x and y")
        x, y = point["x"], point["y"]
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("Landmark coordinates must be numeric")
        if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("Landmark coordinates must be finite values from 0 to 1")
        points.append((float(x), float(y)))
    distances = [
        math.hypot(points[index + 1][0] - points[index][0], points[index + 1][1] - points[index][1])
        for index in range(len(points) - 1)
    ]
    return {
        "landmark_count": len(points),
        "normalized_path_length": round(sum(distances), 5),
        "interpretation": "geometry_only_not_a_clinical_assessment",
    }

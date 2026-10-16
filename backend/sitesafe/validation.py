"""Shared validators for data arriving from devices and the dashboard."""

import math

from rest_framework import serializers


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise serializers.ValidationError(f"{label} must be a number.")
    if not math.isfinite(value):
        raise serializers.ValidationError(f"{label} must be finite.")
    return float(value)


def validate_lat_lng(lat, lng):
    lat = _finite_number(lat, "lat")
    lng = _finite_number(lng, "lng")
    if not -90.0 <= lat <= 90.0:
        raise serializers.ValidationError("lat must be between -90 and 90.")
    if not -180.0 <= lng <= 180.0:
        raise serializers.ValidationError("lng must be between -180 and 180.")
    return lat, lng


def validate_location(value):
    """``{lat, lng}`` object or null."""
    if value is None:
        return value
    if not isinstance(value, dict):
        raise serializers.ValidationError("location must be an object with lat and lng.")
    if "lat" not in value or "lng" not in value:
        raise serializers.ValidationError("location must include lat and lng.")
    lat, lng = validate_lat_lng(value["lat"], value["lng"])
    return {**value, "lat": lat, "lng": lng}


def validate_bbox(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise serializers.ValidationError("bbox must be a list of four numbers [x1, y1, x2, y2].")
    x1, y1, x2, y2 = (_finite_number(v, "bbox value") for v in value)
    if min(x1, y1, x2, y2) < 0:
        raise serializers.ValidationError("bbox coordinates must not be negative.")
    if x2 <= x1 or y2 <= y1:
        raise serializers.ValidationError("bbox must satisfy x2 > x1 and y2 > y1.")
    return [x1, y1, x2, y2]


def validate_polygon(value):
    """Empty list (no GPS boundary) or at least three {lat, lng} / [lat, lng] vertices."""
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError("boundaries must be a list of vertices.")
    if len(value) < 3:
        raise serializers.ValidationError("A zone boundary needs at least three vertices.")
    out = []
    for point in value:
        if isinstance(point, dict) and "lat" in point and "lng" in point:
            lat, lng = validate_lat_lng(point["lat"], point["lng"])
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            lat, lng = validate_lat_lng(point[0], point[1])
        else:
            raise serializers.ValidationError("Each vertex must be {lat, lng} or [lat, lng].")
        out.append({"lat": lat, "lng": lng})
    if len({(p["lat"], p["lng"]) for p in out}) < 3:
        raise serializers.ValidationError("A zone boundary needs at least three distinct vertices.")
    return out


def validate_camera_ids(value):
    if value in (None, []):
        return []
    if not isinstance(value, list) or not all(isinstance(c, str) for c in value):
        raise serializers.ValidationError("camera_ids must be a list of strings.")
    cleaned = [c.strip() for c in value]
    if any(not c or len(c) > 64 for c in cleaned):
        raise serializers.ValidationError("Each camera_id must be 1-64 characters.")
    if len(set(cleaned)) != len(cleaned):
        raise serializers.ValidationError("camera_ids must not contain duplicates.")
    return cleaned

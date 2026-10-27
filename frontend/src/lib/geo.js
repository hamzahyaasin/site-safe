const METRES_PER_DEGREE = 111320

/** The point ``metres`` away from [lat, lng] in compass direction ``bearing`` (degrees from north). */
export function offset([lat, lng], bearing, metres) {
  const rad = (bearing * Math.PI) / 180
  const dLat = (metres * Math.cos(rad)) / METRES_PER_DEGREE
  const dLng = (metres * Math.sin(rad)) / (METRES_PER_DEGREE * Math.cos((lat * Math.PI) / 180))
  return [lat + dLat, lng + dLng]
}

/**
 * A camera's view cone as a polygon: the camera position, then an arc
 * ``range`` metres away from ``heading - fov/2`` to ``heading + fov/2``.
 * Accurate to well under a metre over a site; not for long distances.
 */
export function viewCone({ latitude, longitude, heading, field_of_view: fov, view_range_m: range }, steps = 16) {
  const origin = [latitude, longitude]
  const arc = Array.from({ length: steps + 1 }, (_, i) => offset(origin, heading - fov / 2 + (fov * i) / steps, range))
  return [origin, ...arc]
}

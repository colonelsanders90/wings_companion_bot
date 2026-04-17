import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_rooms(user_lat: float, user_lng: float, rooms: list, n: int = 5) -> list[tuple[float, dict]]:
    ranked = sorted(rooms, key=lambda r: haversine_km(user_lat, user_lng, r["lat"], r["lng"]))
    return [(haversine_km(user_lat, user_lng, r["lat"], r["lng"]), r) for r in ranked[:n]]

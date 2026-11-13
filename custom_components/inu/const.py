"""Inu uses its own limited connection, never a Home Assistant or model API key."""
DOMAIN = "inu"
BASE_URL = "https://inuwithyou.com/api/home-assistant"
KEY = "connection_key"
PLATFORMS = ["text", "button", "sensor"]
FINAL_OUTCOMES = frozenset({"queued", "completed", "already_completed", "not_found", "ambiguous", "blocked", "unsupported", "unavailable"})

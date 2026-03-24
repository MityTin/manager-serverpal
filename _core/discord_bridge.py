import requests

def forward_chat_to_discord(player_name: str, channel: str, message: str, webhook_url: str) -> None:
	"""Send an ingame chat message to a Discord webhook using the player's name.
	This is a lightweight helper so Bot1 logic can live outside serverpal.py.
	"""
	if not webhook_url:
		return
	username = f"{player_name} [{channel}]"
	content  = message
	try:
		requests.post(webhook_url, json={"username": username, "content": content}, timeout=5)
	except Exception:
		# Swallow exceptions to keep game loop stable; caller may log separately.
		pass


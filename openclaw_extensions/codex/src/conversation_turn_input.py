def build_codex_conversation_turn_input(params: dict) -> list:
    prompt = params["prompt"]
    event = params["event"]
    items: list = []
    body_for_agent = (event.get("bodyForAgent") or "").strip() if isinstance(event, dict) else ""
    content = (event.get("content") or "").strip() if isinstance(event, dict) else ""
    text = body_for_agent or content or prompt
    items.append({"type": "text", "text": text, "text_elements": []})
    if isinstance(event, dict) and isinstance(event.get("images"), list):
        for image in event["images"]:
            items.append({"type": "image", "url": image["url"]})
    return items

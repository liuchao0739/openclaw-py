A2UI_PATH = "/__openclaw__/a2ui"
CANVAS_HOST_PATH = "/__openclaw__/canvas"
CANVAS_WS_PATH = "/__openclaw__/ws"

_CANVAS_WS_PATH_JSON = CANVAS_WS_PATH


def is_a2ui_path(pathname: str) -> bool:
    return pathname == A2UI_PATH or pathname.startswith(A2UI_PATH + "/")


def _lowercase_preserving_whitespace(value: str) -> str:
    result = []
    for char in value:
        if char.isspace():
            result.append(char)
        else:
            result.append(char.lower())
    return "".join(result)


def inject_canvas_live_reload(html: str) -> str:
    snippet = f"""
<script>
(() => {{
  const handlerNames = ["openclawCanvasA2UIAction"];
  function postToNode(payload) {{
    try {{
      const raw = typeof payload === "string" ? payload : JSON.stringify(payload);
      for (const name of handlerNames) {{
        const iosHandler = globalThis.webkit?.messageHandlers?.[name];
        if (iosHandler && typeof iosHandler.postMessage === "function") {{
          iosHandler.postMessage(raw);
          return true;
        }}
        const androidHandler = globalThis[name];
        if (androidHandler && typeof androidHandler.postMessage === "function") {{
          androidHandler.postMessage(raw);
          return true;
        }}
      }}
    }} catch {{}}
    return false;
  }}
  function sendUserAction(userAction) {{
    const id =
      (userAction && typeof userAction.id === "string" && userAction.id.trim()) ||
      (globalThis.crypto?.randomUUID?.() ?? String(Date.now()));
    const action = {{ ...userAction, id }};
    return postToNode({{ userAction: action }});
  }}
  globalThis.OpenClaw = globalThis.OpenClaw ?? {{}};
  globalThis.OpenClaw.postMessage = postToNode;
  globalThis.OpenClaw.sendUserAction = sendUserAction;
  globalThis.openclawPostMessage = postToNode;
  globalThis.openclawSendUserAction = sendUserAction;

  try {{
    const cap = new URLSearchParams(location.search).get("oc_cap");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const capQuery = cap ? "?oc_cap=" + encodeURIComponent(cap) : "";
    const ws = new WebSocket(proto + "://" + location.host + {_CANVAS_WS_PATH_JSON!r} + capQuery);
    ws.onmessage = (ev) => {{
      if (String(ev.data || "") === "reload") location.reload();
    }};
  }} catch {{}}
}})();
</script>
""".strip()

    lowered = _lowercase_preserving_whitespace(html)
    idx = lowered.rfind("</body>")
    if idx >= 0:
        return html[:idx] + "\n" + snippet + "\n" + html[idx:]
    return html + "\n" + snippet + "\n"

MANIFEST: dict = {
    "id": "feishu",
    "name": "Feishu/Lark",
    "description": "OpenClaw Feishu/Lark channel plugin for chats and workplace tools (community maintained by @m1heng).",
    "activation": {"onStartup": False},
    "channels": ["feishu"],
    "contracts": {
        "tools": [
            "feishu_app_scopes",
            "feishu_bitable_create_app",
            "feishu_bitable_create_field",
            "feishu_bitable_create_record",
            "feishu_bitable_get_meta",
            "feishu_bitable_get_record",
            "feishu_bitable_list_fields",
            "feishu_bitable_list_records",
            "feishu_bitable_update_record",
            "feishu_chat",
            "feishu_doc",
            "feishu_drive",
            "feishu_perm",
            "feishu_wiki",
        ]
    },
    "channelEnvVars": {
        "feishu": [
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "FEISHU_VERIFICATION_TOKEN",
            "FEISHU_ENCRYPT_KEY",
        ]
    },
    "channel": {
        "id": "feishu",
        "label": "Feishu",
        "selectionLabel": "Feishu/Lark (飞书)",
        "docsPath": "/channels/feishu",
        "docsLabel": "feishu",
        "blurb": "飞书/Lark enterprise messaging with doc/wiki/drive tools.",
        "aliases": ["lark"],
        "order": 35,
        "quickstartAllowFrom": True,
    },
}

PLUGIN_ID = MANIFEST["id"]
PLUGIN_NAME = MANIFEST["name"]
PLUGIN_DESCRIPTION = MANIFEST["description"]
CHANNEL_ID = "feishu"
CHANNEL_LABEL = "Feishu"
CHANNEL_ALIASES = ["lark"]
CHANNEL_ENV_VARS = MANIFEST["channelEnvVars"]["feishu"]
CONTRACT_TOOLS = MANIFEST["contracts"]["tools"]

from .register_sync_runtime import register_bedrock_mantle_plugin

PROVIDER_ID = "amazon-bedrock-mantle"


def define_plugin_entry():
    return {
        "id": PROVIDER_ID,
        "name": "Amazon Bedrock Mantle Provider",
        "description": "Bundled Amazon Bedrock Mantle (OpenAI-compatible) provider plugin",
        "register": register_bedrock_mantle_plugin,
    }


default_entry = define_plugin_entry()

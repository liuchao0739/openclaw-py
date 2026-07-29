from .speech_provider import build_azure_speech_provider


def _register(api):
    api["registerSpeechProvider"](build_azure_speech_provider())


plugin_entry: dict = {
    "id": "azure-speech",
    "name": "Azure Speech",
    "description": "Bundled Azure Speech provider",
    "register": _register,
}

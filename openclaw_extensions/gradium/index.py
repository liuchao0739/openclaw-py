from .speech_provider import build_gradium_speech_provider


def define_plugin_entry(*, id: str, name: str, description: str, register):
    return {
        "id": id,
        "name": name,
        "description": description,
        "register": register,
    }


def _register(api):
    api["registerSpeechProvider"](build_gradium_speech_provider())


default = define_plugin_entry(
    id="gradium",
    name="Gradium Speech",
    description="Bundled Gradium speech provider",
    register=_register,
)

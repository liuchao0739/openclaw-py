from openclaw_extensions.elevenlabs.config_compat import (
    migrate_eleven_labs_legacy_talk_config,
)


def _register(api) -> None:
    register_fn = (
        api.get("registerConfigMigration")
        if isinstance(api, dict)
        else getattr(api, "registerConfigMigration", None)
    )
    if not callable(register_fn):
        return
    register_fn(lambda config: migrate_eleven_labs_legacy_talk_config(config))


plugin_entry: dict = {
    "id": "elevenlabs",
    "name": "ElevenLabs Setup",
    "description": "Lightweight ElevenLabs setup hooks",
    "register": _register,
}

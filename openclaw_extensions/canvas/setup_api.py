from .config_migration import migrate_legacy_canvas_host_config

plugin_entry: dict = {
    "id": "canvas",
    "name": "Canvas Setup",
    "description": "Lightweight Canvas setup hooks",
    "register": {
        "configMigration": lambda config: migrate_legacy_canvas_host_config(config),
    },
}

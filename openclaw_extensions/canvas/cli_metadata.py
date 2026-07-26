"""Canvas CLI metadata entrypoint used for lightweight command discovery."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry


def _register(api: OpenClawPluginApi) -> None:
    api.register_node_cli_feature(  # type: ignore[attr-defined]
        lambda _ctx: None,
        {
            "descriptors": [
                {
                    "name": "canvas",
                    "description": "Capture or render canvas content from a paired node",
                    "hasSubcommands": True,
                },
            ],
        },
    )


default = define_plugin_entry(
    id="canvas",
    name="Canvas",
    description="Experimental Canvas control and A2UI rendering surfaces for paired nodes.",
    register=_register,
)

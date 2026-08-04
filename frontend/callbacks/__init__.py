"""Registro centralizado de callbacks Dash."""

from __future__ import annotations


def register_callbacks(dash_app) -> None:
    """Importa módulos de callback após dash_app existir (registro via @callback)."""
    from callbacks import context, global_filter, pipeline, routing, wizard_state  # noqa: F401

    routing.register(dash_app)
    global_filter.register(dash_app)
    context.register(dash_app)
    wizard_state.register(dash_app)
    pipeline.register(dash_app)

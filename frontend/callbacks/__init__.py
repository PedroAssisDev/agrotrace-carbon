"""Registro centralizado de callbacks Dash."""

from __future__ import annotations


def register_callbacks(dash_app) -> None:
    """Importa módulos de callback após dash_app existir (registro via @callback)."""
    from callbacks import context, calculation_review, data_entry, general_analysis_tabs, global_filter, pipeline, provenance_queries, routing, technical_audit, wizard_state  # noqa: F401

    routing.register(dash_app)
    global_filter.register(dash_app)
    context.register(dash_app)
    data_entry.register(dash_app)
    wizard_state.register(dash_app)
    pipeline.register(dash_app)
    calculation_review.register(dash_app)
    technical_audit.register(dash_app)
    provenance_queries.register(dash_app)
    general_analysis_tabs.register(dash_app)

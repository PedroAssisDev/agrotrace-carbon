"""Future HTTP adapter for provenance integration."""

from __future__ import annotations

from app.domain.ports.provenance_ports import (
    ProvenanceDataReaderPort,
    ProvenanceEventReaderPort,
)


class HttpProvenanceClient(ProvenanceEventReaderPort, ProvenanceDataReaderPort):
    def fetch_pending_events(self, *, event_types, after_created_at=None, limit=100):
        raise NotImplementedError("HTTP provenance client is reserved for a future phase")

    def get_event_by_id(self, outbox_event_id: str):
        raise NotImplementedError("HTTP provenance client is reserved for a future phase")

    def get_reporting_period(self, reporting_period_id):
        raise NotImplementedError

    def get_pipeline_run(self, pipeline_run_id):
        raise NotImplementedError

    def get_calculation_result_set(self, calculation_result_set_id):
        raise NotImplementedError

    def get_hash_records_for_subject(self, subject_kind, subject_id):
        raise NotImplementedError

    def get_aggregation_link_by_id(self, link_id):
        raise NotImplementedError

    def get_calculation_execution_method_version_hash(self, calculation_execution_id):
        raise NotImplementedError

    def get_calculation_execution_parameter_set_hash(self, calculation_execution_id):
        raise NotImplementedError

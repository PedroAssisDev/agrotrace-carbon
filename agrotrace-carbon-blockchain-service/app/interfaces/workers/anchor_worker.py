from __future__ import annotations

import json
import time
from uuid import UUID

from app.application.container import ServiceContainer, init_database
from app.application.dto.commands import ObserveEventsCommand, ReprocessFailedAnchoringCommand, SimulateAnchoringCommand
from app.application.use_cases.observe_provenance_events import ObserveProvenanceEventsUseCase
from app.application.use_cases.process_anchor_requests import ProcessAnchorRequestsUseCase
from app.application.use_cases.reprocess_failed_anchoring import ReprocessFailedAnchoringUseCase
from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
from app.domain.value_objects.statuses import EvidencePackageStatus


def run_once(container: ServiceContainer) -> None:
    with container.unit_of_work() as uow:
        ObserveProvenanceEventsUseCase(uow, container.event_reader).execute(ObserveEventsCommand())
        package_ids = ProcessAnchorRequestsUseCase(uow, container.data_reader).execute()
        for package_id in package_ids:
            package = uow.evidence_packages.get(UUID(package_id))
            if package and package.status == EvidencePackageStatus.READY_TO_ANCHOR.value:
                SimulateAnchoringUseCase(uow, container.providers).execute(
                    SimulateAnchoringCommand(
                        evidence_package_id=package.evidence_package_id,
                        network_code=container.settings.default_network_code,
                    )
                )
        ReprocessFailedAnchoringUseCase(
            uow, container.data_reader, container.providers
        ).execute(ReprocessFailedAnchoringCommand(limit=10))


def main() -> None:
    container = ServiceContainer()
    init_database(container.settings)
    while True:
        run_once(container)
        time.sleep(5)


if __name__ == "__main__":
    main()

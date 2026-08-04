from app.application.container import ServiceContainer, init_database
from app.application.dto.commands import VerifyEvidencePackageCommand
from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
from app.shared.ids import ensure_uuid
import sys


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/verify_package.py <evidence_package_id>")
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = VerifyEvidencePackageUseCase(uow).execute(
            VerifyEvidencePackageCommand(evidence_package_id=ensure_uuid(sys.argv[1]))
        )
        print(result.is_valid)


if __name__ == "__main__":
    main()

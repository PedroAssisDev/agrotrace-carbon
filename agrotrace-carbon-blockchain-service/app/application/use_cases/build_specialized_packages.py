from __future__ import annotations

from app.application.dto.commands import BuildEvidencePackageCommand
from app.application.dto.results import BuildEvidencePackageResult
from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.provenance.sqlite_provenance_event_reader import SQLiteProvenanceDataReader


class BuildMonthlyEvidencePackageUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, data_reader: SQLiteProvenanceDataReader) -> None:
        self._delegate = BuildEvidencePackageUseCase(uow, data_reader)

    def execute(self, command: BuildEvidencePackageCommand) -> BuildEvidencePackageResult:
        return self._delegate.execute(command)


class BuildAnnualEvidencePackageUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, data_reader: SQLiteProvenanceDataReader) -> None:
        self._delegate = BuildEvidencePackageUseCase(uow, data_reader)

    def execute(self, command: BuildEvidencePackageCommand) -> BuildEvidencePackageResult:
        return self._delegate.execute(command)


class BuildDailyToMonthlyAggregationPackageUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, data_reader: SQLiteProvenanceDataReader) -> None:
        self._delegate = BuildEvidencePackageUseCase(uow, data_reader)

    def execute(self, command: BuildEvidencePackageCommand) -> BuildEvidencePackageResult:
        return self._delegate.execute(command)


class BuildMonthlyToAnnualAggregationPackageUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, data_reader: SQLiteProvenanceDataReader) -> None:
        self._delegate = BuildEvidencePackageUseCase(uow, data_reader)

    def execute(self, command: BuildEvidencePackageCommand) -> BuildEvidencePackageResult:
        return self._delegate.execute(command)

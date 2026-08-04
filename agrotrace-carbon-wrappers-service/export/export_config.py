"""Configuração de exportação pós-wrapper.

O separador `;_;` é multi-caractere: a serialização usa regras estilo RFC 4180
(aspas e escape), não o módulo csv da stdlib com delimitador de um só caractere.
A extensão padrão `.delimited.csv` deixa explícito que não é CSV RFC clássico;
pode-se usar `.csv` desde que consumidores respeitem o mesmo separador e quoting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportConfiguration:
    base_dir: Path
    field_separator: str = ";_;"
    file_extension: str = ".delimited.csv"
    encoding: str = "utf-8"
    write_canonical: bool = True
    write_normalized: bool = True
    write_rejected: bool = True
    write_validation_report: bool = True
    write_manifest: bool = True
    write_empty_normalized_on_failure: bool = False
    write_processing_log: bool = False
    ensure_data_layout: bool = True
    input_subdir: str = "input"
    processed_subdir: str = "processed"
    rejected_subdir: str = "rejected"
    logs_subdir: str = "logs"
    validation_reports_subdir: str = "validation_reports"
    use_date_subfolders: bool = True

    def input_root(self) -> Path:
        return self.base_dir / self.input_subdir

    def processed_root(self) -> Path:
        return self.base_dir / self.processed_subdir

    def rejected_root(self) -> Path:
        return self.base_dir / self.rejected_subdir

    def validation_reports_root(self) -> Path:
        return self.base_dir / self.validation_reports_subdir

    def logs_root(self) -> Path:
        return self.base_dir / self.logs_subdir

"""
Exportacao pos-wrapper — delimitador ;_;, manifest, relatorios.

Uso:
  from wrappers.export import ExportConfiguration, persist_processing_result
  process_file(..., export_config=ExportConfiguration(base_dir=Path("data")))
"""

from .delimited import DelimitedExportStrategy, DelimitedSerializer
from .delimited_reader import (
    read_delimited_file,
    read_delimited_table,
    split_delimited_line,
    split_physical_lines,
)
from .export_config import ExportConfiguration
from .manifest import MANIFEST_REQUIRED_KEYS, validate_export_manifest
from .output_writer import (
    OutputWriter,
    ProcessedFileDescriptor,
    RejectedFileDescriptor,
    persist_processing_result,
)

__all__ = [
    "DelimitedSerializer",
    "ExportConfiguration",
    "OutputWriter",
    "MANIFEST_REQUIRED_KEYS",
    "ProcessedFileDescriptor",
    "RejectedFileDescriptor",
    "persist_processing_result",
    "read_delimited_file",
    "read_delimited_table",
    "split_delimited_line",
    "split_physical_lines",
    "validate_export_manifest",
]

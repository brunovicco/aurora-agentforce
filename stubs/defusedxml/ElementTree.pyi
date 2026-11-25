"""Local stub for the defusedxml parse interface used by the portal."""

from io import BytesIO
from pathlib import Path
from xml.etree.ElementTree import ElementTree

def parse(
    source: str | Path | BytesIO,
    parser: object | None = None,
    forbid_dtd: bool = False,
    forbid_entities: bool = True,
    forbid_external: bool = True,
) -> ElementTree: ...

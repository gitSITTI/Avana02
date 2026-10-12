"""MSOSA / Cameo / MagicDraw project files (.mdzip, zipped XMI): CONTRACT STUB, deliberately not implemented.

What is documented (MagicDraw file-format docs, see the research report): from 17.0.1 a project is a zip of XMI 2.4, text and
binary resources, with entries such as com.nomagic.magicdraw.uml_model.model.

Why: there is no documented reader contract for .mdzip, and the report's advice is to export ReqIF
(Cameo Requirements Modeler) or use the Teamwork Cloud / Open API route when you have access.
How to implement it later: obtain a real, shareable .mdzip, add it to tests/fixtures with a manifest,
write `read()` to yield RawRecord per stereotyped Requirement element, and the conformance suite will
tell you when it is done. Until then sniff() answers truthfully (it can recognise the file) and read() refuses.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Discovery, Source, register
from ..model import Fidelity, RawRecord


@register
class MdzipAdapter(Adapter):
    name = "mdzip"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True)
    implemented = False
    maturity = "stub"

    def sniff(self, src: Source) -> float:
        if Path(src.uri).suffix.lower() != ".mdzip":
            return 0.0
        try:
            zipfile.ZipFile(src.uri).close()
            return 0.55   # recognised, so the user gets the helpful NotImplementedError below instead of 'unknown file'
        except (zipfile.BadZipFile, OSError):
            return 0.0

    def discover(self, src: Source) -> Discovery:
        raise NotImplementedError("Export ReqIF from MSOSA (Cameo Requirements Modeler) and open that instead; see adapters/mdzip.py")

    def read(self, src: Source) -> Iterator[RawRecord]:
        raise NotImplementedError("Export ReqIF from MSOSA (Cameo Requirements Modeler) and open that instead; see adapters/mdzip.py")

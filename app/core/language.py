from __future__ import annotations

import re

from app.domain.enums import Language


BENGALI_BLOCK = re.compile(r"[\u0980-\u09FF]")
LATIN_BLOCK = re.compile(r"[A-Za-z]")


def detect_language(complaint: str, explicit_language: Language | None) -> Language:
    if explicit_language is not None:
        return explicit_language

    has_bn = bool(BENGALI_BLOCK.search(complaint))
    has_latin = bool(LATIN_BLOCK.search(complaint))

    if has_bn and has_latin:
        return Language.MIXED
    if has_bn:
        return Language.BN
    return Language.EN


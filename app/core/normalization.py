from __future__ import annotations

import re


BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_bangla_numerals(text: str) -> str:
    return text.translate(BENGALI_DIGITS)


def sanitize_complaint(text: str, max_chars: int) -> str:
    cleaned = normalize_bangla_numerals(text)
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;").replace("{", "(").replace("}", ")")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars]


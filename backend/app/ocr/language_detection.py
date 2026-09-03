"""Lightweight script-based language detection for OCR output.

This intentionally detects meaningful amounts of Kannada and Latin script; a
single stray glyph cannot change the document route.
"""

from collections import Counter
from typing import Iterable

from backend.app.ocr.ocr_models import OCRElement

KANNADA_START = ord("\u0c80")
KANNADA_END = ord("\u0cff")


def script_counts(text: str) -> Counter:
    counts: Counter = Counter()
    for char in text:
        codepoint = ord(char)
        if KANNADA_START <= codepoint <= KANNADA_END:
            counts["kannada"] += 1
        elif char.isascii() and char.isalpha():
            counts["latin"] += 1
        elif char.isdigit():
            counts["numeric"] += 1
        elif char.isalpha():
            counts["other"] += 1
    return counts


def detect_language_from_text(text: str) -> str:
    counts = script_counts(text)
    kannada = counts["kannada"]
    latin = counts["latin"]
    letters = kannada + latin + counts["other"]

    if letters < 8:
        return "Unknown"

    kannada_ratio = kannada / letters
    latin_ratio = latin / letters

    # Any document with meaningful Kannada content is classified as Kannada.
    # Tesseract handles kan+eng in a single pass, so "Mixed" is not needed.
    if kannada >= 8 and kannada_ratio >= 0.20:
        return "Kannada"
    if latin >= 8 and latin_ratio >= 0.70:
        return "English"
    return "Unknown"


def detect_language(elements: Iterable[OCRElement]) -> str:
    return detect_language_from_text(" ".join(element.text for element in elements))


def has_meaningful_kannada(elements: Iterable[OCRElement]) -> bool:
    text = " ".join(element.text for element in elements)
    counts = script_counts(text)
    letters = counts["kannada"] + counts["latin"] + counts["other"]
    return counts["kannada"] >= 8 and letters > 0 and counts["kannada"] / letters >= 0.20

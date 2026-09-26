"""
Перевірка файлів лікарняного за їхнім вмістом (сигнатурою), а не за розширенням
чи заголовком Content-Type, які клієнт може вказати будь-які.

Модуль не залежить від Django — його можна тестувати окремо.
"""

import re

MAX_FILE_BYTES = 10 * 1024 * 1024  # один файл
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # усі файли одного надсилання (лист з вкладеннями)
MAX_FILES_PER_UPLOAD = 5
MAX_FILES_PER_REQUEST = 10

# ftyp-бренди контейнера HEIF (так знімає iPhone)
_HEIF_BRANDS = {
    b"heic",
    b"heix",
    b"hevc",
    b"hevx",
    b"heim",
    b"heis",
    b"mif1",
    b"msf1",
    b"avif",
}


def detect_file_type(head: bytes) -> tuple[str, str] | None:
    """Повертає (content_type, розширення) або None, якщо формат не підтримується."""
    if head.startswith(b"%PDF-"):
        return "application/pdf", "pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", "webp"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIF_BRANDS:
        if head[8:12] == b"avif":
            return "image/avif", "avif"
        return "image/heic", "heic"
    if head[:2] == b"BM":
        return "image/bmp", "bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff", "tiff"
    return None


def safe_filename(original: str, extension: str, index: int) -> str:
    """Ім'я для вкладення: без шляхів і дивних символів, з розширенням за реальним типом."""
    stem = original.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = stem.rsplit(".", 1)[0] if "." in stem else stem
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_")[:80]
    return f"{stem or f'L4_{index}'}.{extension}"

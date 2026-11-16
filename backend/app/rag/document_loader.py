import hashlib
from pathlib import Path


def load_document(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, content_hash

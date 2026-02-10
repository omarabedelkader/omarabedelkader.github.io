from datetime import datetime
from pathlib import Path


def last_updated_label(source_file: Path) -> str:
    """Return `Month YYYY` based on the source markdown's modification time."""
    modified_at = datetime.fromtimestamp(source_file.stat().st_mtime)
    return modified_at.strftime("%B %Y")
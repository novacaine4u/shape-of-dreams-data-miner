"""Website export placeholder."""

from __future__ import annotations

from pathlib import Path


def build_website(data_directory: Path, output_directory: Path) -> None:
    """Create the future website output directory.

    The actual frontend will be added after the normalized database format is stable.
    """
    output_directory.mkdir(parents=True, exist_ok=True)

from pathlib import Path
from typing import Union


def get_unique_filename(
    base_path: Union[str, Path], return_full_path: bool = False
) -> Union[str, Path]:
    """
    Find a unique filename by appending version numbers if a file with the base name already exists.

    Args:
        base_path: Base path for the file (existing or not)
        return_full_path: If True, returns the full path as a Path object,
                          otherwise just the filename as a string

    Returns:
        A unique filename (str) or full path (Path) that doesn't conflict with existing files
    """
    # Create path object if it's not already
    path = Path(base_path)

    # Check if a file with this path already exists
    if not path.exists():
        return path if return_full_path else path.name

    # Extract components
    directory = path.parent
    base_name = path.stem
    extension = path.suffix
    version = 2

    while True:
        new_filename = f"{base_name} - v{version}{extension}"
        new_path = directory / new_filename

        if not new_path.exists():
            return new_path if return_full_path else new_filename

        version += 1

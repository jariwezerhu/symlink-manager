import logging
from pathlib import Path
from typing import Optional, Union

from symlink_manager.media import Media, MediaFile
from symlink_manager.utils import get_unique_filename
from symlink_manager.database import Repository, Session


class Symlinker:
    """
    Class that handles creating symbolic links for media files in a structured library.
    """

    def __init__(
        self,
        library_base: Union[str, Path],
        separate_anime: bool = True,
    ):
        """
        Initialize the Symlinker.

        Args:
            library_base: Base directory for the media library
            separate_anime: Whether to place anime in separate directories
        """
        self.library_base = Path(library_base)
        self.separate_anime = separate_anime
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_media_directory(self, media: Media) -> Path:
        """
        Create a directory for the given media if it doesn't exist.

        Args:
            media: The Media entity

        Returns:
            Path to the created directory
        """
        media_path = media.get_path(self.library_base, self.separate_anime)
        media_path.mkdir(exist_ok=True)
        self.logger.debug(f"Created or verified media directory: {media_path}")
        return media_path

    def format_symlink_path(self, media_file: MediaFile) -> Path:
        """
        Format the symlink path for a media file.

        Args:
            media_file: The MediaFile entity

        Returns:
            Unique path for the symlink

        Raises:
            ValueError: If media_file is not associated with a Media entity
        """
        if not media_file.media:
            raise ValueError(
                f"MediaFile (id={
                    media_file.id
                }) is not associated with any Media entity"
            )

        # Create the media directory
        media_path = self.create_media_directory(media_file.media)

        # Get the media file path and ensure it's unique
        file_path = media_path / media_file.get_path()
        unique_path = get_unique_filename(file_path, return_full_path=True)

        return unique_path

    def create_symlink(self, media_file: MediaFile) -> Optional[Path]:
        """
        Create a symbolic link for the media file.

        Args:
            media_file: The MediaFile entity

        Returns:
            Path to the created symlink, or None if operation failed

        Raises:
            ValueError: If media_file is not associated with a Media entity
            FileNotFoundError: If the target file doesn't exist
        """
        # If already symlinked, return existing path
        if media_file.symlink_path and Path(media_file.symlink_path).exists():
            self.logger.debug(
                f"Media file is already symlinked at {media_file.symlink_path}"
            )
            return Path(media_file.symlink_path)

        # Get target path and verify it exists
        target_path = Path(media_file.target_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Target file not found: {target_path}")

        # Format symlink path
        symlink_path = self.format_symlink_path(media_file)

        try:
            with Repository(Session()) as repo:
                # Create parent directories if needed
                symlink_path.parent.mkdir(parents=True, exist_ok=True)

                # Create the symlink (symlink_path -> target_path)
                symlink_path.symlink_to(target_path)
                self.logger.info(f"Created symlink: {
                                 symlink_path} -> {target_path}")

                # Update the media file with the new symlink path
                repo.update(media_file, symlink_path=str(symlink_path))
                return symlink_path
        except OSError as e:
            self.logger.error(f"Failed to create symlink: {e}")
            return None

import logging
from pathlib import Path
from typing import Iterator, List, Optional, Set, Union

from symlink_manager.database import Repository, Session
from symlink_manager.media import Media, MediaFile
from symlink_manager.services import Parser

from .categories import Categories


class LibraryScanner:
    """Scanner responsible for getting existing library entries"""

    # Set of recognized video file extensions
    VIDEO_EXTENSIONS: Set[str] = {".mkv", ".mov", ".avi", ".mp4", ".wmv"}

    def __init__(
        self,
        library_base: Union[str, Path],
        parser: Parser,
        categories: Optional[Categories] = None,
    ):
        """
        Initialize the scanner

        Args:
            library_base: Base directory for the media library
            categories: Optional custom categories configuration
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.library_base = Path(library_base)
        self.parser = parser
        self.categories = categories or Categories()

    def full_scan(self):
        self.logger.info("Performing a full scan of media library")

        media_paths = self.get_media_paths()
        for media_path in media_paths:
            try:
                media_info = self.get_media_info(media_path)
                if media_info:  # Check if info was successfully retrieved
                    self.index_media(**media_info, path=media_path)

            except ValueError as e:
                self.logger.error(f"Value error processing media {
                                  media_path}: {e}")
            except TypeError as e:
                self.logger.error(
                    f"Type error processing media {
                        media_path
                    } (possibly mismatched parameters): {e}"
                )
            except KeyError as e:
                self.logger.error(
                    f"Missing key while processing media {media_path}: {e}"
                )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error processing media {media_path}: {e}",
                    exc_info=True,
                )

    def get_media_files(self, media_path: Path, recursive: bool = True) -> List[Path]:
        """
        Get all media files in a directory

        Args:
            media_path: Path to the media directory
            recursive: Whether to search subdirectories recursively

        Returns:
            List of Path objects for media files
        """
        self.logger.debug(f"Scanning for media files in {media_path}")

        files = []

        # Determine the glob pattern based on recursion preference
        pattern = "**/*" if recursive else "*"

        # Process all files in the directory
        for file_path in media_path.glob(pattern):
            # Skip if not a file
            if not file_path.is_file():
                continue

            # Skip if extension not recognized
            if file_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
                continue

            files.append(file_path)

        self.logger.debug(f"Found {len(files)} media files in {media_path}")
        return files

    def get_media_paths(self) -> Iterator:
        for category_name, category_path in self.categories.get_all_paths(
            self.library_base
        ).items():
            self.logger.info(f"Scanning '{category_name}' at {category_path}")

            try:
                for media_path in category_path.iterdir():
                    # Skip non-directories
                    if not media_path.is_dir():
                        continue
                    yield media_path
            except PermissionError:
                self.logger.error(f"Permission denied: {category_path}")
            except Exception as e:
                self.logger.error(f"Error scanning {category_path}: {e}")

    def get_media_info(self, media_path: Union[str, Path]) -> dict:
        try:
            # Get category:
            category_name = Path(media_path).parent.name

            # Parse media directory name
            title, year, imdb_id = self.parser.parse_media(media_path).values()

            # Determine if anime or not
            anime = True if "anime" in category_name.lower() else False

            # Determine if movie or staticmethod
            kind = "movie" if "movie" in category_name.lower() else "show"

            # Create media info dictionary
            media_info = {
                "kind": kind,
                "imdb_id": imdb_id,
                "title": title,
                "year": year,
                "anime": anime,
            }

            # Yield the category and media info
            return media_info

        except ValueError as e:
            self.logger.warning(f"Skipping invalid media path: {e}")

    def index_media(
        self,
        kind: str,
        imdb_id: str,
        title: str,
        year: int,
        anime: bool,
        path: Union[Path, str],
    ):
        """Scan the media library and add or update entities in the database.

        Args:
            library_scanner: Configured LibraryScanner instance
        """
        with Repository(Session()) as repo:
            # Use Media.create class method
            existing = repo.get_by_id(Media, imdb_id)
            if existing:
                self.logger.debug(f"Skipping existing media: {existing}")
                return
            media = Media.create(kind, imdb_id, title, year, anime)
            repo.add(media)

            # Get media files
            files = self.get_media_files(path)

            # Skip if no media files found
            if not files:
                self.logger.warning(f"No valid media files found in {path}")

            for file in files:
                symlink_path = str(file)
                target_path = str(
                    file.resolve() if file.is_symlink() else None)
                file_size = file.stat().st_size
                season, episode = self.parser.extract_media_episode(
                    symlink_path)

                # Use MediaFile.create class method
                media_file = MediaFile.create(
                    media_id=imdb_id,
                    symlink_path=symlink_path,
                    target_path=target_path,
                    file_size=file_size,
                    season=season,
                    episode=episode,
                )
                repo.add(media_file)
                self.logger.debug(f"Successfully indexed media: {media}")

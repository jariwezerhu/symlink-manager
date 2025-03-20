from logging import getLogger
from pathlib import Path
from typing import Iterator, List, Set, Union

from symlink_manager.database import Repository, Session
from symlink_manager.media import Media, MediaFile, Torrent
from symlink_manager.services import Parser, Resolver


class TorrentScanner:
    VIDEO_EXTENSIONS: Set[str] = {".mkv", ".mov", ".avi", ".mp4", ".wmv"}

    def __init__(
        self, torrent_base: Union[str, Path], parser: Parser, resolver: Resolver
    ):
        self.logger = getLogger(self.__class__.__name__)
        self.parser = parser
        self.resolver = resolver
        self.torrent_base = Path(torrent_base)

    def full_scan(self):
        """
        Perform a full scan of all torrents and index them in the database.
        """
        self.logger.info("Performing a full scan of torrent directory")
        torrent_paths = self.get_torrent_paths()
        for torrent_path in torrent_paths:
            try:
                with Repository(Session()) as repo:
                    existing = repo.get(Torrent, Torrent.path == str(torrent_path))
                    if existing:
                        self.logger.debug(f"Skipping existing torrent: {existing}")
                        continue
                torrent_info = self.get_torrent_info(torrent_path)
                if torrent_info:  # Check if info was successfully retrieved
                    self.index_torrent(**torrent_info)

            except ValueError as e:
                self.logger.error(f"Value error processing torrent {torrent_path}: {e}")
            except TypeError as e:
                self.logger.error(
                    f"Type error processing torrent {
                        torrent_path
                    } (possibly mismatched parameters): {e}"
                )
            except KeyError as e:
                self.logger.error(
                    f"Missing key while processing torrent {torrent_path}: {e}"
                )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error processing torrent {torrent_path}: {e}",
                    exc_info=True,
                )

    def get_torrent_files(
        self, torrent_path: Path, recursive: bool = True
    ) -> List[Path]:
        """
        Get all torrent files in a directory

        Args:
            torrent_path: Path to the torrent directory

        Returns:
            List of Path objects for torrent files
        """
        self.logger.debug(f"Scanning for torrent files in {torrent_path}")

        files = []

        # Determine the glob pattern based on recursion preference
        pattern = "**/*" if recursive else "*"

        # Process all files in the directory
        for file_path in torrent_path.glob(pattern):
            # Skip if not a file
            if not file_path.is_file():
                continue

            # Skip if extension not recognized
            if file_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
                continue

            files.append(file_path)

        self.logger.debug(f"Found {len(files)} torrent files in {torrent_path}")
        return files

    def get_torrent_paths(self) -> Iterator:
        """
        Scan all torrents in the torrent folder, yielding path objects.

        Yields:
            Path: Path objects for each torrent directory
        """
        base_path = self.torrent_base  # Store in variable for exception handler
        try:
            for torrent_path in base_path.iterdir():
                # Skip non-directories
                if not torrent_path.is_dir():
                    continue
                yield torrent_path
        except PermissionError:
            self.logger.error(f"Permission denied: {base_path}")
        except Exception as e:
            self.logger.error(f"Error scanning {base_path}: {e}")

    def get_torrent_info(self, torrent_path: Union[str, Path]):
        """
        Extract information from a torrent path.

        Args:
            torrent_path: Path to the torrent directory

        Returns:
            dict: Dictionary containing torrent information, or None if parsing failed
        """
        try:
            # Parse torrent folder name
            title, year, kind = self.parser.parse_torrent(torrent_path).values()

            # Get torrent files
            files = self.get_torrent_files(torrent_path)

            # Skip if no torrent files found
            if not files:
                self.logger.warning(f"No valid torrent files found in {torrent_path}")
                return None

            # Create torrent info dictionary
            return {
                "kind": kind,
                "title": title,
                "year": year,
                "torrent_path": torrent_path,
                "files": files,
            }
        except ValueError as e:
            self.logger.warning(f"Skipping invalid torrent path {torrent_path}: {e}")
            return None

    def index_torrent(
        self,
        torrent_path: Union[str, Path],
        files: List[Path],
        kind: str,
        title: str,
        year: int,
    ):
        """
        Index a torrent and its media files in the database.

        This method creates a Torrent record in the database and associates
        media files with it. For movies, it selects the largest file as the
        primary media file. For TV shows, it processes each file individually,
        extracting season and episode information.

        Args:
            torrent_path: Path to the torrent directory
            files: List of media file paths contained in the torrent
            kind: Type of media content ('movie' or 'show')
            title: Title of the media content
            year: Release year of the media content

        Note:
            This method commits changes to the database through the Repository
            context manager.

        Raises:
            ValueError: If no valid files are found or parsing fails
            SQLAlchemyError: If database operations fail
        """
        with Repository(Session()) as repo:
            torrent = repo.add(
                Torrent(path=str(torrent_path), torrent_title=title, torrent_year=year)
            )

            if kind == "movie":
                target_path = max(files, key=lambda file: Path(file).stat().st_size)

                # Use MediaFile.create class method
                media_file = MediaFile.create(
                    torrent_id=torrent.id,
                    target_path=str(target_path),
                    file_size=target_path.stat().st_size,
                )
                repo.add(media_file)
            else:
                for file in files:
                    # File processing for TV shows
                    season, episode = self.parser.parse_torrent_episode(file)
                    if season and episode:
                        # Use MediaFile.create class method
                        media_file = MediaFile.create(
                            torrent_id=torrent.id,
                            target_path=str(file),
                            file_size=file.stat().st_size,
                            season=season,
                            episode=episode,
                        )
                        repo.add(media_file)
            self.logger.debug(f"Successfully indexed torrent: {torrent_path}")

    def add_missing_media_to_torrents(self):
        """
        Find torrents without media associations, resolve their media information,
        and update the database with the appropriate associations.
        """
        with Repository(Session()) as repo:
            all_torrents = repo.get_all(Torrent)
            for torrent in all_torrents:
                if not torrent.media_id:
                    try:
                        torrent_info = self.parser.parse_torrent(torrent.path)
                        imdb_id = self.resolver.get_imdb_id(**torrent_info)

                        if not imdb_id:
                            self.logger.warning(
                                f"Could not resolve IMDb ID for torrent: {torrent.path}"
                            )
                            continue

                        if not repo.get_by_id(Media, imdb_id):
                            try:
                                media_info = self.resolver.get_media(imdb_id)
                                media = Media.create(**media_info)
                                repo.add(media)
                                self.logger.info(
                                    f"Created new media record: {
                                        media_info.get('title')
                                    } ({imdb_id})"
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"Failed to create media for IMDb ID {imdb_id}: {e}"
                                )
                                continue

                        repo.update(torrent, media_id=imdb_id)
                        self.logger.info(
                            f"Linked torrent {torrent.path} to media {imdb_id}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error processing torrent {torrent.path}: {e}"
                        )

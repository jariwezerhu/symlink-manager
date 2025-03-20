import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from PTT import parse_title


class Parser:
    """
    Parser for extracting metadata from media and torrent file paths.

    This class provides methods to parse file and directory names to extract
    structured information such as titles, years, IMDb IDs, and episode details.
    It handles two distinct naming conventions:
    1. Media library entries: "Title (Year) {imdb-ttID}"
    2. Torrent files/directories: Various formats parsed by PTT library
    """

    def __init__(self):
        """
        Initialize the Parser with regex patterns for media path and episode parsing.
        """
        self.media_pattern = re.compile(
            r"^(?P<title>.*?)\s*\((?P<year>\d{4})\)\s*\{imdb-tt(?P<imdb_id>\d+)\}$"
        )
        self.episode_pattern = r"[sS](\d+)[eE](\d+)"

    def parse_torrent(
        self, torrent_path: Union[str, Path]
    ) -> Dict[str, Union[str, int]]:
        """
        Parse a torrent directory name to extract media metadata using PTT parser.

        Args:
            torrent_path: Path object or string representing the torrent directory

        Returns:
            Dict containing the extracted metadata:
                - title: Media title string
                - year: Release year (int or str depending on PTT parser)
                - kind: Content type ('movie' or 'show')

        Raises:
            ValueError: If parsing fails or required metadata (like title) is missing
        """
        torrent_path = Path(torrent_path)
        parsed_torrent = parse_title(torrent_path.name)
        title = parsed_torrent.get("title")
        year = parsed_torrent.get("year")
        kind = self._determine_media_type(parsed_torrent)
        if not title:
            raise ValueError(f"Missing title in parsed result for {
                             torrent_path.name}")
        return {"title": title, "year": year, "kind": kind}

    def parse_torrent_episode(
        self, file_path: Union[str, Path]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract season and episode information from a torrent file path using PTT.

        This method is specifically for parsing episode information from torrent
        files, which may have a variety of naming conventions handled by the PTT library.

        Args:
            file_path: Path object or string representing the episode file

        Returns:
            Tuple of (season, episode), where each is either a string or None if not found
        """
        file_path = Path(file_path)
        parsed_file = parse_title(file_path.name)
        season = parsed_file.get("seasons")
        episode = parsed_file.get("episodes")
        if season and episode:
            return season[0], episode[0]
        if episode:
            return None, episode[0]
        return None, None

    def _determine_media_type(self, parsed_data: dict) -> str:
        """
        Determine if parsed content is a show or movie based on metadata.

        Args:
            parsed_data: Dictionary of parsed metadata from PTT

        Returns:
            String 'show' if season or episode information is present, otherwise 'movie'
        """
        return (
            "show"
            if bool(parsed_data.get("seasons") or parsed_data.get("episode"))
            else "movie"
        )

    def parse_media(self, media_path: Union[str, Path]) -> Dict[str, str]:
        """
        Parse a media library directory name to extract metadata.

        This method expects directories in the format: "Title (Year) {imdb-ttID}"
        used in the organized media library.

        Args:
            media_path: Path to the media directory

        Returns:
            Dictionary containing:
                - title: Media title string
                - year: Release year as string
                - imdb_id: IMDb ID string without the 'tt' prefix

        Raises:
            ValueError: If the path name doesn't match the expected format
        """
        name = Path(media_path).name
        match = self.media_pattern.search(name)
        if not match:
            raise ValueError(f"Media path format not recognized: {name}")
        return {
            "title": match.group("title").strip(),
            "year": match.group("year"),
            "imdb_id": match.group("imdb_id"),
        }

    def extract_media_episode(
        self, media_file: Union[str, Path]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract season and episode information from a media library file path using regex.

        This method is specifically for parsing episode information from organized
        media library files, which follow the SxxExx pattern in their filenames.

        Args:
            media_file: Path object or string representing the episode file

        Returns:
            Tuple of (season, episode), where each is either a string or None if not found
        """
        match = re.search(self.episode_pattern, str(media_file))
        if match:
            season = match.group(1)
            episode = match.group(2)
            return season, episode
        return None, None

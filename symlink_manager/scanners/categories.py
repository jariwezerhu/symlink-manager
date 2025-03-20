from typing import Optional, Dict
from pathlib import Path


class Categories:
    """Configuration for media library directory categories"""

    def __init__(
        self,
        separate_animes: Optional[bool] = True,
        movies: Optional[str] = None,
        shows: Optional[str] = None,
        anime_movies: Optional[str] = None,
        anime_shows: Optional[str] = None,
    ):
        self.separate_animes = separate_animes
        self.movies = movies or "movies"
        self.shows = shows or "shows"
        self.anime_movies = anime_movies or "anime_movies"
        self.anime_shows = anime_shows or "anime_shows"

    def get_all_paths(self, library_base: Path) -> Dict[str, Path]:
        """
        Get all category paths for scanning

        Args:
            library_base: Base directory for the media library

        Returns:
            Dictionary mapping category names to full Path objects
        """
        if self.separate_animes:
            return {
                "Movies": library_base / self.movies,
                "Shows": library_base / self.shows,
                "Anime Movies": library_base / self.anime_movies,
                "Anime Shows": library_base / self.anime_shows,
            }
        else:
            return {
                "Movies": library_base / self.movies,
                "Shows": library_base / self.shows,
            }

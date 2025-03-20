from typing import Any, Dict, List, Optional

from imdb import Cinemagoer


class Resolver:
    """
    Resolver for media information using the IMDb database.

    This class provides methods to search for media by title and retrieve
    detailed information about movies and TV shows from IMDb.

    Attributes:
        SHOW_TYPES: List of IMDb kinds that should be considered TV shows
        VALID_TYPES: List of valid media types this resolver can handle
    """

    SHOW_TYPES = ["tv series", "tv mini series"]
    VALID_TYPES = ["movie", "show"]

    def __init__(self):
        """
        Initialize the Resolver with a Cinemagoer client.
        """
        self.ia = Cinemagoer()

    def get_imdb_id(self, title: str, year: Optional[str], kind: str) -> Optional[str]:
        """
        Search for an IMDb ID based on title, year, and media type.

        Args:
            title: The title of the media to search for
            year: Optional release year to narrow search results
            kind: Type of media ('movie' or 'show')

        Returns:
            IMDb ID as a string if found, None otherwise

        Raises:
            ValueError: If an invalid kind is provided
            RuntimeError: If the IMDb API connection fails
        """
        if not title:
            raise ValueError("Title cannot be empty")

        if kind not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid media type: {kind}. Must be one of {self.VALID_TYPES}"
            )

        search_str = f"{title} {year if year else ''}"

        try:
            results = self.ia.search_movie(search_str)
        except Exception as e:
            raise RuntimeError(f"IMDb API search failed: {str(e)}")

        # Return None if no results found (no need for an exception)
        for result in results:
            result_type = "show" if result.get("kind") in self.SHOW_TYPES else "movie"
            if result_type == kind:
                return result.movieID

        return None  # No matching results found

    def get_media(self, imdb_id: str) -> Dict[str, Any]:
        """
        Retrieve detailed media information given an IMDb ID.

        Args:
            imdb_id: The IMDb ID of the media

        Returns:
            Dictionary containing media details

        Raises:
            ValueError: If IMDb ID is invalid
            RuntimeError: If media retrieval fails
        """
        if not imdb_id:
            raise ValueError("IMDb ID cannot be empty")

        try:
            media = self.ia.get_movie(imdb_id, info=["main"])

            if not media:
                raise ValueError(f"No media found for IMDb ID: {imdb_id}")

            media_info = {
                "imdb_id": imdb_id,
                "title": media.get("title"),
                "year": media.get("year"),
                "anime": self._is_anime(
                    media.get("genres", []), media.get("countries", [])
                ),
                "kind": "show" if media.get("kind") in self.SHOW_TYPES else "movie",
            }
            return media_info

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(
                f"Failed to retrieve media for IMDb ID {imdb_id}: {str(e)}"
            )

    def _is_anime(
        self, genres: Optional[List[str]], countries: Optional[List[str]]
    ) -> bool:
        """
        Determine if a media is anime based on its genres and countries.

        Args:
            genres: List of genres for the media
            countries: List of production countries

        Returns:
            True if the media is identified as anime, False otherwise
        """
        genres = genres or []
        countries = countries or []

        return "Anime" in genres or ("Animation" in genres and "Japan" in countries)


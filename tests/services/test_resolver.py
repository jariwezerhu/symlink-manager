import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

# Correct import from the package structure
from symlink_manager.services.resolver import Resolver


class TestResolver:
    """Test suite for the Resolver class."""

    def test_init(self):
        """Test that Resolver initializes with a Cinemagoer client."""
        # Patch Cinemagoer at the correct import location
        with patch(
            "symlink_manager.services.resolver.Cinemagoer"
        ) as mock_cinemagoer_class:
            resolver = Resolver()
            # Verify Cinemagoer was instantiated
            mock_cinemagoer_class.assert_called_once()

    # Tests for get_imdb_id method

    def test_get_imdb_id_empty_title(self):
        """Test that get_imdb_id raises ValueError when title is empty."""
        resolver = Resolver()
        with pytest.raises(ValueError, match="Title cannot be empty"):
            resolver.get_imdb_id("", "2020", "movie")

    def test_get_imdb_id_invalid_kind(self):
        """Test that get_imdb_id raises ValueError when kind is invalid."""
        resolver = Resolver()
        with pytest.raises(ValueError, match="Invalid media type"):
            resolver.get_imdb_id("Test Movie", "2020", "invalid_kind")

    def test_get_imdb_id_api_failure(self):
        """Test that get_imdb_id handles API failures gracefully."""
        resolver = Resolver()

        # Patch the search_movie method to raise an exception
        with patch.object(
            resolver.ia, "search_movie", side_effect=Exception("API connection failed")
        ):
            with pytest.raises(RuntimeError, match="IMDb API search failed"):
                resolver.get_imdb_id("Test Movie", "2020", "movie")

    def test_get_imdb_id_movie_found(self):
        """Test that get_imdb_id returns correct ID when a matching movie is found."""
        resolver = Resolver()

        # Create a mock movie result
        mock_movie = MagicMock()
        mock_movie.get.return_value = "movie"
        mock_movie.movieID = "123456"

        # Patch the search_movie method to return our mock movie
        with patch.object(resolver.ia, "search_movie", return_value=[mock_movie]):
            result = resolver.get_imdb_id("Test Movie", "2020", "movie")
            assert result == "123456"

    def test_get_imdb_id_show_found(self):
        """Test that get_imdb_id returns correct ID when a matching show is found."""
        resolver = Resolver()

        # Create a mock show result
        mock_show = MagicMock()
        mock_show.get.return_value = "tv series"  # This is in SHOW_TYPES
        mock_show.movieID = "654321"

        # Patch the search_movie method to return our mock show
        with patch.object(resolver.ia, "search_movie", return_value=[mock_show]):
            result = resolver.get_imdb_id("Test Show", "2020", "show")
            assert result == "654321"

    def test_get_imdb_id_no_matching_type(self):
        """Test that get_imdb_id returns None when no matching type is found."""
        resolver = Resolver()

        # Create a mock movie when searching for a show
        mock_movie = MagicMock()
        mock_movie.get.return_value = "movie"
        mock_movie.movieID = "123456"

        # Patch the search_movie method to return our mock movie
        with patch.object(resolver.ia, "search_movie", return_value=[mock_movie]):
            result = resolver.get_imdb_id("Test Show", "2020", "show")
            assert result is None

    def test_get_imdb_id_no_results(self):
        """Test that get_imdb_id returns None when no results are found."""
        resolver = Resolver()

        # Patch the search_movie method to return an empty list
        with patch.object(resolver.ia, "search_movie", return_value=[]):
            result = resolver.get_imdb_id("Nonexistent Movie", "2020", "movie")
            assert result is None

    def test_get_imdb_id_year_none(self):
        """Test that get_imdb_id works correctly when year is None."""
        resolver = Resolver()

        # Create a mock movie result
        mock_movie = MagicMock()
        mock_movie.get.return_value = "movie"
        mock_movie.movieID = "123456"

        # Patch the search_movie method to return our mock movie
        with patch.object(resolver.ia, "search_movie", return_value=[mock_movie]):
            result = resolver.get_imdb_id("Test Movie", None, "movie")

            # Check that search_movie was called with the correct string
            resolver.ia.search_movie.assert_called_once_with("Test Movie ")
            assert result == "123456"

    # Tests for get_media method

    def test_get_media_empty_id(self):
        """Test that get_media raises ValueError when IMDb ID is empty."""
        resolver = Resolver()
        with pytest.raises(ValueError, match="IMDb ID cannot be empty"):
            resolver.get_media("")

    def test_get_media_not_found(self):
        """Test that get_media raises ValueError when no media is found for the given ID."""
        resolver = Resolver()

        # Patch the get_movie method to return None
        with patch.object(resolver.ia, "get_movie", return_value=None):
            with pytest.raises(ValueError, match="No media found for IMDb ID"):
                resolver.get_media("999999")

    def test_get_media_api_failure(self):
        """Test that get_media handles API failures gracefully."""
        resolver = Resolver()

        # Patch the get_movie method to raise an exception
        with patch.object(
            resolver.ia, "get_movie", side_effect=Exception("API connection failed")
        ):
            with pytest.raises(
                RuntimeError, match="Failed to retrieve media for IMDb ID"
            ):
                resolver.get_media("123456")

    def test_get_media_movie_success(self):
        """Test that get_media returns correct data for movies."""
        resolver = Resolver()

        # Set up mock movie data
        mock_movie = {
            "title": "Test Movie",
            "year": 2020,
            "kind": "movie",
            "genres": ["Action", "Thriller"],
            "countries": ["USA"],
        }

        # Patch the get_movie method to return our mock movie
        with patch.object(resolver.ia, "get_movie", return_value=mock_movie):
            result = resolver.get_media("123456")

            expected = {
                "imdb_id": "123456",
                "title": "Test Movie",
                "year": 2020,
                "anime": False,
                "kind": "movie",
            }

            assert result == expected
            resolver.ia.get_movie.assert_called_once_with(
                "123456", info=["main"])

    def test_get_media_show_success(self):
        """Test that get_media returns correct data for shows."""
        resolver = Resolver()

        # Set up mock show data
        mock_show = {
            "title": "Test Show",
            "year": 2020,
            "kind": "tv series",  # This is in SHOW_TYPES
            "genres": ["Drama", "Comedy"],
            "countries": ["UK"],
        }

        # Patch the get_movie method to return our mock show
        with patch.object(resolver.ia, "get_movie", return_value=mock_show):
            result = resolver.get_media("654321")

            expected = {
                "imdb_id": "654321",
                "title": "Test Show",
                "year": 2020,
                "anime": False,
                "kind": "show",
            }

            assert result == expected

    def test_get_media_anime_detection(self):
        """Test that get_media correctly identifies anime."""
        resolver = Resolver()

        # Set up mock anime data
        mock_anime = {
            "title": "Test Anime",
            "year": 2020,
            "kind": "movie",
            "genres": ["Animation", "Anime"],
            "countries": ["Japan"],
        }

        # Patch the get_movie method to return our mock anime
        with patch.object(resolver.ia, "get_movie", return_value=mock_anime):
            result = resolver.get_media("789012")

            expected = {
                "imdb_id": "789012",
                "title": "Test Anime",
                "year": 2020,
                "anime": True,
                "kind": "movie",
            }

            assert result == expected

    def test_get_media_incomplete_data(self):
        """Test that get_media handles incomplete data gracefully."""
        resolver = Resolver()

        # Set up mock incomplete data
        mock_incomplete = {
            "title": "Test Incomplete",
            # Missing year, kind, genres, countries
        }

        # Patch the get_movie method to return our mock incomplete data
        with patch.object(resolver.ia, "get_movie", return_value=mock_incomplete):
            result = resolver.get_media("123456")

            # Should default missing values appropriately
            expected = {
                "imdb_id": "123456",
                "title": "Test Incomplete",
                "year": None,  # get() returns None for missing keys
                "anime": False,  # Default for missing genres/countries
                "kind": "movie",  # Default for missing kind
            }

            assert result == expected

    # Tests for _is_anime method

    def test_is_anime_anime_genre(self):
        """Test that _is_anime returns True when 'Anime' is in genres."""
        resolver = Resolver()
        genres = ["Action", "Adventure", "Anime"]
        countries = ["USA"]

        assert resolver._is_anime(genres, countries) is True

    def test_is_anime_animation_japan(self):
        """Test that _is_anime returns True for 'Animation' genre from Japan."""
        resolver = Resolver()
        genres = ["Animation", "Fantasy"]
        countries = ["Japan"]

        assert resolver._is_anime(genres, countries) is True

    def test_is_anime_animation_not_japan(self):
        """Test that _is_anime returns False for 'Animation' not from Japan."""
        resolver = Resolver()
        genres = ["Animation", "Fantasy"]
        countries = ["USA"]

        assert resolver._is_anime(genres, countries) is False

    def test_is_anime_not_anime(self):
        """Test that _is_anime returns False for non-anime content."""
        resolver = Resolver()
        genres = ["Action", "Adventure"]
        countries = ["USA"]

        assert resolver._is_anime(genres, countries) is False

    def test_is_anime_empty_lists(self):
        """Test that _is_anime handles empty genres and countries lists."""
        resolver = Resolver()
        assert resolver._is_anime([], []) is False

    def test_is_anime_none_values(self):
        """Test that _is_anime handles None values for genres and countries."""
        resolver = Resolver()
        assert resolver._is_anime(None, None) is False
        assert resolver._is_anime(["Anime"], None) is True
        assert resolver._is_anime(None, ["Japan"]) is False

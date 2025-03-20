import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import re

# Import the Parser class - adjust path as needed for your project structure
from symlink_manager.services.parser import Parser


@pytest.fixture
def parser():
    """Fixture to create a Parser instance for tests."""
    return Parser()


# Tests for __init__ method
def test_parser_init():
    """Test Parser initialization."""
    parser = Parser()

    # Verify the media_pattern is a compiled regex with the expected pattern
    assert isinstance(parser.media_pattern, re.Pattern)
    assert (
        parser.media_pattern.pattern
        == r"^(?P<title>.*?)\s*\((?P<year>\d{4})\)\s*\{imdb-tt(?P<imdb_id>\d+)\}$"
    )

    # Verify the episode pattern
    assert parser.episode_pattern == r"[sS](\d+)[eE](\d+)"


# Tests for parse_torrent method
@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_movie(mock_parse_title, parser):
    """Test parsing a movie torrent."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "title": "The Matrix",
        "year": 1999,
        # No seasons or episodes -> should be a movie
    }

    # Call the method with a test path
    result = parser.parse_torrent("The.Matrix.1999.1080p.BluRay.x264")

    # Verify the results
    assert result == {"title": "The Matrix", "year": 1999, "kind": "movie"}
    mock_parse_title.assert_called_once_with(
        "The.Matrix.1999.1080p.BluRay.x264")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_show(mock_parse_title, parser):
    """Test parsing a TV show torrent."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "title": "Breaking Bad",
        "year": 2008,
        "seasons": [5],  # Has seasons -> should be a show
        "episode": None,
    }

    # Call the method with a test path
    result = parser.parse_torrent("Breaking.Bad.S05.1080p.BluRay.x264")

    # Verify the results
    assert result == {"title": "Breaking Bad", "year": 2008, "kind": "show"}
    mock_parse_title.assert_called_once_with(
        "Breaking.Bad.S05.1080p.BluRay.x264")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_missing_title(mock_parse_title, parser):
    """Test parsing a torrent with a missing title."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "year": 2020,
        # No title
    }

    # Call the method should raise ValueError
    with pytest.raises(ValueError, match="Missing title in parsed result for"):
        parser.parse_torrent("Unknown.2020.1080p.BluRay.x264")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_with_path_object(mock_parse_title, parser):
    """Test parsing a torrent with a Path object."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "title": "The Matrix",
        "year": 1999,
    }

    # Create a Path object
    path = Path("The.Matrix.1999.1080p.BluRay.x264")

    # Call the method
    result = parser.parse_torrent(path)

    # Verify the results
    assert result == {"title": "The Matrix", "year": 1999, "kind": "movie"}
    mock_parse_title.assert_called_once_with(
        "The.Matrix.1999.1080p.BluRay.x264")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_with_string_year(mock_parse_title, parser):
    """Test parsing a torrent with a string year value."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "title": "The Matrix",
        "year": "1999",  # Year as string
    }

    # Call the method
    result = parser.parse_torrent("The.Matrix.1999.1080p.BluRay.x264")

    # Verify the results - the implementation preserves original types
    assert result == {"title": "The Matrix", "year": "1999", "kind": "movie"}


# Tests for parse_torrent_episode method
@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_episode_both(mock_parse_title, parser):
    """Test parsing an episode with both season and episode."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "seasons": ["01"],
        "episodes": ["05"],
    }

    # Call the method
    season, episode = parser.parse_torrent_episode("Show.S01E05.mp4")

    # Verify the results - implementation preserves string values
    assert season == "01"  # String value preserved
    assert episode == "05"  # String value preserved
    mock_parse_title.assert_called_once_with("Show.S01E05.mp4")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_episode_only(mock_parse_title, parser):
    """Test parsing an episode with only episode number."""
    # Set up the mock response
    mock_parse_title.return_value = {
        "episodes": ["05"],
        # No seasons
    }

    # Call the method
    season, episode = parser.parse_torrent_episode("Show.E05.mp4")

    # Verify the results
    assert season is None
    assert episode == "05"  # String value preserved
    mock_parse_title.assert_called_once_with("Show.E05.mp4")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_episode_none(mock_parse_title, parser):
    """Test parsing a file with no episode information."""
    # Set up the mock response
    mock_parse_title.return_value = {
        # No seasons or episodes
    }

    # Call the method
    season, episode = parser.parse_torrent_episode("Show.mp4")

    # Verify the results
    assert season is None
    assert episode is None
    mock_parse_title.assert_called_once_with("Show.mp4")


@patch("symlink_manager.services.parser.parse_title")
def test_parse_torrent_episode_multiple(mock_parse_title, parser):
    """Test parsing an episode with multiple seasons or episodes."""
    # Set up the mock response with multiple seasons and episodes
    mock_parse_title.return_value = {
        "seasons": ["01", "02"],
        "episodes": ["05", "06"],
    }

    # Call the method
    season, episode = parser.parse_torrent_episode("Show.S01E05-S02E06.mp4")

    # Verify it takes the first one of each, with original string type preserved
    assert season == "01"  # String value preserved
    assert episode == "05"  # String value preserved


# Tests for _determine_media_type method
def test_determine_media_type_movie(parser):
    """Test determining media type for a movie."""
    # Empty data should be a movie
    parsed_data = {}
    assert parser._determine_media_type(parsed_data) == "movie"

    # Data without seasons or episodes should be a movie
    parsed_data = {"title": "The Matrix", "year": 1999}
    assert parser._determine_media_type(parsed_data) == "movie"


def test_determine_media_type_show_with_seasons(parser):
    """Test determining media type for a show with seasons."""
    parsed_data = {"seasons": [1]}
    assert parser._determine_media_type(parsed_data) == "show"


def test_determine_media_type_show_with_episode(parser):
    """Test determining media type for a show with episodes."""
    parsed_data = {"episode": "01"}
    assert parser._determine_media_type(parsed_data) == "show"


# Tests for parse_media method
def test_parse_media_valid(parser):
    """Test parsing a valid media path."""
    media_path = "The Matrix (1999) {imdb-tt0133093}"
    result = parser.parse_media(media_path)

    assert result == {"title": "The Matrix",
                      "year": "1999", "imdb_id": "0133093"}


def test_parse_media_with_spaces(parser):
    """Test parsing a media path with extra spaces."""
    media_path = "The Matrix  (1999)  {imdb-tt0133093}"
    result = parser.parse_media(media_path)

    assert result == {"title": "The Matrix",
                      "year": "1999", "imdb_id": "0133093"}


def test_parse_media_invalid_format(parser):
    """Test parsing a media path with invalid format."""
    media_path = "The Matrix 1999"  # Missing the required format

    with pytest.raises(ValueError, match="Media path format not recognized"):
        parser.parse_media(media_path)


def test_parse_media_with_path_object(parser):
    """Test parsing a media path as a Path object."""
    media_path = Path("The Matrix (1999) {imdb-tt0133093}")
    result = parser.parse_media(media_path)

    assert result == {"title": "The Matrix",
                      "year": "1999", "imdb_id": "0133093"}


def test_parse_media_with_complex_title(parser):
    """Test parsing a media with a complex title containing parentheses."""
    media_path = "The Matrix (Directors Cut) (1999) {imdb-tt0133093}"
    result = parser.parse_media(media_path)

    # The regex should be non-greedy for the title part
    assert result == {
        "title": "The Matrix (Directors Cut)",
        "year": "1999",
        "imdb_id": "0133093",
    }


# Tests for extract_media_episode method
def test_extract_media_episode_valid(parser):
    """Test extracting episode information from a valid path."""
    media_file = "The.Show.S01E05.mp4"
    season, episode = parser.extract_media_episode(media_file)

    assert season == "01"
    assert episode == "05"


def test_extract_media_episode_lowercase(parser):
    """Test extracting episode information with lowercase s and e."""
    media_file = "The.Show.s01e05.mp4"
    season, episode = parser.extract_media_episode(media_file)

    assert season == "01"
    assert episode == "05"


def test_extract_media_episode_none(parser):
    """Test extracting episode information from a path with no episode info."""
    media_file = "The.Movie.mp4"
    season, episode = parser.extract_media_episode(media_file)

    assert season is None
    assert episode is None


def test_extract_media_episode_with_prefix(parser):
    """Test extracting episode info with text before the pattern."""
    media_file = "Prefix.Text.S01E05.mp4"
    season, episode = parser.extract_media_episode(media_file)

    assert season == "01"
    assert episode == "05"


def test_extract_media_episode_with_suffix(parser):
    """Test extracting episode info with text after the pattern."""
    media_file = "Show.S01E05.Suffix.Text.mp4"
    season, episode = parser.extract_media_episode(media_file)

    assert season == "01"
    assert episode == "05"


def test_extract_media_episode_with_path_object(parser):
    """Test extracting episode info from a Path object."""
    media_file = Path("Show.S01E05.mp4")
    season, episode = parser.extract_media_episode(media_file)

    assert season == "01"
    assert episode == "05"

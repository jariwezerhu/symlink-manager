import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import logging

# Import the classes to test - adjust paths as needed for your project structure
from symlink_manager.scanners.library_scanner import LibraryScanner, Categories
from symlink_manager.services import Parser


@pytest.fixture
def mock_parser():
    """Fixture for creating a mock Parser instance."""
    parser = MagicMock(spec=Parser)
    parser.parse_media.return_value = {
        "title": "Test Movie",
        "year": "2020",
        "imdb_id": "0123456",
    }
    parser.extract_media_episode.return_value = (None, None)
    return parser


@pytest.fixture
def mock_repository():
    """Fixture for mocking the Repository class."""
    repo_mock = MagicMock()
    repo_instance = MagicMock()
    repo_mock.return_value.__enter__.return_value = repo_instance
    return repo_mock, repo_instance


@pytest.fixture
def mock_session():
    """Fixture for mocking the Session factory."""
    return MagicMock()


@pytest.fixture
def categories():
    """Fixture for creating a Categories instance with default values."""
    return Categories()


@pytest.fixture
def custom_categories():
    """Fixture for creating a Categories instance with custom values."""
    return Categories(
        movies="custom_movies",
        shows="custom_shows",
        anime_movies="custom_anime_movies",
        anime_shows="custom_anime_shows",
    )


@pytest.fixture
def scanner(mock_parser):
    """Fixture for creating a LibraryScanner instance."""
    return LibraryScanner("/media/library", mock_parser)


# Tests for Categories class
class TestCategories:
    def test_categories_init_defaults(self, categories):
        """Test Categories initialization with default values."""
        assert categories.movies == "movies"
        assert categories.shows == "shows"
        assert categories.anime_movies == "anime_movies"
        assert categories.anime_shows == "anime_shows"

    def test_categories_init_custom(self, custom_categories):
        """Test Categories initialization with custom values."""
        assert custom_categories.movies == "custom_movies"
        assert custom_categories.shows == "custom_shows"
        assert custom_categories.anime_movies == "custom_anime_movies"
        assert custom_categories.anime_shows == "custom_anime_shows"

    def test_get_all_paths(self, categories):
        """Test get_all_paths method."""
        base_path = Path("/media/library")
        paths = categories.get_all_paths(base_path)

        assert len(paths) == 4
        assert paths["Movies"] == base_path / "movies"
        assert paths["Shows"] == base_path / "shows"
        assert paths["Anime Movies"] == base_path / "anime_movies"
        assert paths["Anime Shows"] == base_path / "anime_shows"


# Tests for LibraryScanner class
class TestLibraryScanner:
    def test_init(self, mock_parser):
        """Test LibraryScanner initialization."""
        scanner = LibraryScanner("/media/library", mock_parser)

        assert scanner.library_base == Path("/media/library")
        assert scanner.parser == mock_parser
        assert isinstance(scanner.categories, Categories)

    def test_init_with_custom_categories(self, mock_parser, custom_categories):
        """Test LibraryScanner initialization with custom categories."""
        scanner = LibraryScanner(
            "/media/library", mock_parser, custom_categories)

        assert scanner.library_base == Path("/media/library")
        assert scanner.parser == mock_parser
        assert scanner.categories == custom_categories

    def test_video_extensions(self, scanner):
        """Test the VIDEO_EXTENSIONS set."""
        assert isinstance(scanner.VIDEO_EXTENSIONS, set)
        assert ".mkv" in scanner.VIDEO_EXTENSIONS
        assert ".mov" in scanner.VIDEO_EXTENSIONS
        assert ".avi" in scanner.VIDEO_EXTENSIONS
        assert ".mp4" in scanner.VIDEO_EXTENSIONS
        assert ".wmv" in scanner.VIDEO_EXTENSIONS
        assert ".txt" not in scanner.VIDEO_EXTENSIONS

    @patch("pathlib.Path.glob")
    def test_get_media_files(self, mock_glob, scanner):
        """Test get_media_files method."""
        # Create individual mock files with proper configuration
        mock_movie1 = MagicMock(spec=Path)
        mock_movie1.name = "movie1.mp4"
        mock_movie1.suffix = ".mp4"  # Configure suffix as an attribute
        mock_movie1.is_file.return_value = True

        mock_movie2 = MagicMock(spec=Path)
        mock_movie2.name = "movie2.mkv"
        mock_movie2.suffix = ".mkv"
        mock_movie2.is_file.return_value = True

        mock_document = MagicMock(spec=Path)
        mock_document.name = "document.txt"
        mock_document.suffix = ".txt"
        mock_document.is_file.return_value = True

        mock_folder = MagicMock(spec=Path)
        mock_folder.name = "folder"
        mock_folder.is_file.return_value = False

        # Configure glob to return our mock files
        mock_files = [mock_movie1, mock_movie2, mock_document, mock_folder]
        mock_glob.return_value = mock_files

        # Call the method
        media_path = Path("/media/library/movies/Test Movie (2020)")
        files = scanner.get_media_files(media_path)

        # Verify
        mock_glob.assert_called_once_with("**/*")
        assert len(files) == 2  # Only mp4 and mkv should be included
        assert mock_movie1 in files
        assert mock_movie2 in files

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    @patch("pathlib.Path.is_dir")
    def test_get_media_paths(self, mock_is_dir, mock_iterdir, mock_exists, scanner):
        """Test get_media_paths method."""
        # Setup mocks
        media_paths = [
            MagicMock(spec=Path, name="Movie1 (2020) {imdb-tt1234567}"),
            MagicMock(spec=Path, name="Movie2 (2021) {imdb-tt7654321}"),
            MagicMock(spec=Path, name="not_a_directory.txt"),
        ]

        # All category paths exist
        mock_exists.return_value = True

        # Configure iterdir to return our mock paths for each category
        mock_iterdir.return_value = media_paths

        # First two paths are directories, third is a fi

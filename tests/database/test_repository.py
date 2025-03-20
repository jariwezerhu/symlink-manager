import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker

from symlink_manager.database import Base
from symlink_manager.database.repository import (
    Repository,
    EntityHandler,
    MediaHandler,
    MovieHandler,
    ShowHandler,
    MediaFileHandler,
    TorrentHandler,
)
from symlink_manager.media import Media, Movie, Show, Torrent, MediaFile


# -------------------- FIXTURES --------------------


@pytest.fixture(scope="function")
def test_engine():
    """Create a SQLite in-memory database engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_movie(test_session):
    """Create a sample Movie instance for testing."""
    movie = Movie(id="0133093", title="The Matrix", year=1999, anime=False)
    test_session.add(movie)
    test_session.flush()
    return movie


@pytest.fixture
def sample_show(test_session):
    """Create a sample Show instance for testing."""
    show = Show(id="0944947", title="Game of Thrones", year=2011, anime=False)
    test_session.add(show)
    test_session.flush()
    return show


@pytest.fixture
def sample_torrent(test_session):
    """Create a sample Torrent instance for testing."""
    torrent = Torrent(
        path="/downloads/matrix.torrent", torrent_title="The Matrix", torrent_year=1999
    )
    test_session.add(torrent)
    test_session.flush()
    return torrent


@pytest.fixture
def sample_media_file(test_session):
    """Create a sample MediaFile instance for testing."""
    media_file = MediaFile(
        target_path="/downloads/matrix/matrix.mkv",
        file_size=1500000000,
    )
    test_session.add(media_file)
    test_session.flush()
    return media_file


@pytest.fixture
def repository(test_session):
    """Create a Repository instance with a test session."""
    return Repository(test_session)


# Custom entity class for testing
class CustomEntity(Base):
    __tablename__ = "custom_entities"
    id = Column(Integer, primary_key=True)
    name = Column(String)


# -------------------- ENTITY HANDLER TESTS --------------------


class TestEntityHandler:
    """Tests for the base EntityHandler class."""

    @pytest.fixture
    def entity_handler(self, test_session):
        """Create a generic EntityHandler for testing."""
        return EntityHandler(test_session, Media)

    def test_add(self, entity_handler, sample_movie):
        """Test adding an entity."""
        # Since sample_movie is already in the session, let's create a new one
        movie = Movie(id="0133094", title="The Matrix Reloaded",
                      year=2003, anime=False)
        result = entity_handler.add(movie)
        assert result == movie
        assert entity_handler.get_by_id("0133094") == movie

    def test_get(self, entity_handler, sample_movie):
        """Test getting entities with conditions."""
        results = entity_handler.get(Media.title == "The Matrix")
        assert len(results) == 1
        assert results[0] == sample_movie

    def test_get_by_id(self, entity_handler, sample_movie):
        """Test getting an entity by ID."""
        result = entity_handler.get_by_id("0133093")
        assert result == sample_movie

    def test_get_all(self, entity_handler, sample_movie, sample_show):
        """Test getting all entities."""
        results = entity_handler.get_all()
        assert len(results) == 2
        assert sample_movie in results
        assert sample_show in results

    def test_update(self, entity_handler, sample_movie):
        """Test updating entity properties."""
        # Set a property to None to test conditional update
        sample_movie.title = None
        result = entity_handler.update(
            sample_movie, title="The Matrix Reloaded")
        assert result.title == "The Matrix Reloaded"

    def test_delete(self, entity_handler, sample_movie):
        """Test deleting an entity."""
        entity_handler.delete(sample_movie)
        assert entity_handler.get_by_id("0133093") is None

    def test_extract_attributes(self, entity_handler, sample_movie):
        """Test extracting attributes from an entity."""
        attrs = entity_handler._extract_attributes(sample_movie)
        assert "id" in attrs
        assert "title" in attrs
        assert "year" in attrs
        assert attrs["id"] == "0133093"


# -------------------- MEDIA HANDLER TESTS --------------------


class TestMediaHandler:
    """Tests for the MediaHandler class."""

    @pytest.fixture
    def media_handler(self, test_session):
        """Create a MediaHandler for testing."""
        return MediaHandler(test_session, Media)

    def test_add_new_media(self, media_handler):
        """Test adding a new media entity."""
        movie = Movie(id="0133099", title="New Movie", year=2020, anime=False)
        result = media_handler.add(movie)
        assert result == movie
        assert media_handler.get_by_id("0133099") == movie

    def test_add_existing_media(self, media_handler, sample_movie):
        """Test adding a media entity that already exists."""
        duplicate = Movie(id="0133093", title="Matrix Copy",
                          year=2000, anime=False)
        result = media_handler.add(duplicate)
        # Should return the existing entity, not the new one
        assert result == sample_movie
        assert result.title == "The Matrix"
        assert result.year == 1999

    def test_find_by_title(self, media_handler, sample_movie, sample_show):
        """Test finding media by title."""
        results = media_handler.find_by_title("Matrix")
        assert len(results) == 1
        assert results[0] == sample_movie

        results = media_handler.find_by_title("Game")
        assert len(results) == 1
        assert results[0] == sample_show


# -------------------- REPOSITORY TESTS --------------------


class TestRepository:
    """Tests for the Repository class."""

    def test_register_handler(self, repository, test_engine):
        """Test registering a new handler."""
        # Ensure CustomEntity is created in the database
        Base.metadata.create_all(test_engine)

        # Create a mock handler
        mock_handler = Mock()

        # Register it for the CustomEntity type
        repository.register_handler(CustomEntity, mock_handler)

        # Verify it was registered
        assert repository._handlers[CustomEntity] == mock_handler

    def test_get_handler_by_class(self, repository):
        """Test getting a handler by entity class."""
        handler = repository._get_handler(Media)
        assert isinstance(handler, MediaHandler)

    def test_get_handler_by_instance(self, repository, sample_movie):
        """Test getting a handler by entity instance."""
        handler = repository._get_handler(sample_movie)
        assert isinstance(handler, MovieHandler)

    def test_get_handler_inheritance(self, repository, sample_movie):
        """Test getting a handler for a parent class."""
        # Save a reference to the movie handler
        movie_handler = repository._handlers[Movie]

        # Delete the specific handler
        del repository._handlers[Movie]

        # Should fall back to Media handler
        handler = repository._get_handler(sample_movie)
        assert isinstance(handler, MediaHandler)

        # Restore the handler for other tests
        repository._handlers[Movie] = movie_handler

    def test_get_handler_not_found(self, repository):
        """Test getting a handler for an unregistered type."""

        class UnregisteredEntity:
            pass

        with pytest.raises(TypeError):
            repository._get_handler(UnregisteredEntity)

    def test_add(self, repository):
        """Test adding an entity."""
        movie = Movie(id="0133095", title="Another Matrix",
                      year=2005, anime=False)
        result = repository.add(movie)
        assert result == movie
        assert repository.get_by_id(Movie, "0133095") == movie

    def test_get(self, repository, sample_movie, sample_show):
        """Test getting entities with conditions."""
        results = repository.get(Media, Media.title == "The Matrix")
        assert len(results) == 1
        assert results[0] == sample_movie

    def test_get_unregistered_type(self, repository):
        """Test getting entities of an unregistered type."""

        class UnregisteredEntity:
            pass

        with pytest.raises(TypeError):
            repository.get(UnregisteredEntity)

    def test_get_by_id(self, repository, sample_movie):
        """Test getting an entity by ID."""
        result = repository.get_by_id(Movie, "0133093")
        assert result == sample_movie

    def test_get_by_id_unregistered_type(self, repository):
        """Test getting an entity by ID for an unregistered type."""

        class UnregisteredEntity:
            pass

        with pytest.raises(TypeError):
            repository.get_by_id(UnregisteredEntity, 1)

    def test_get_all(self, repository, sample_movie, sample_show):
        """Test getting all entities of a type."""
        movies = repository.get_all(Movie)
        assert len(movies) == 1
        assert movies[0] == sample_movie

        shows = repository.get_all(Show)
        assert len(shows) == 1
        assert shows[0] == sample_show

    def test_get_all_unregistered_type(self, repository):
        """Test getting all entities of an unregistered type."""

        class UnregisteredEntity:
            pass

        with pytest.raises(TypeError):
            repository.get_all(UnregisteredEntity)

    def test_find_media_by_title(self, repository, sample_movie, sample_show):
        """Test finding media by title."""
        results = repository.find_media_by_title("Matrix")
        assert len(results) == 1
        assert results[0] == sample_movie

    def test_find_media_by_title_no_handler(self, repository):
        """Test finding media by title when MediaHandler is not registered."""
        # Save a reference to the media handler
        media_handler = repository._handlers[Media]

        # Remove the Media handler
        del repository._handlers[Media]

        with pytest.raises(TypeError):
            repository.find_media_by_title("Matrix")

        # Restore the handler for other tests
        repository._handlers[Media] = media_handler

    def test_get_media_file_by_path(self, repository, sample_media_file):
        """Test getting a media file by path."""
        result = repository.get_media_file_by_path(
            "/downloads/matrix/matrix.mkv")
        assert result == sample_media_file

    def test_get_media_file_by_path_no_handler(self, repository):
        """Test getting a media file by path when MediaFileHandler is not registered."""
        # Save a reference to the handler
        media_file_handler = repository._handlers[MediaFile]

        # Remove the MediaFile handler
        del repository._handlers[MediaFile]

        with pytest.raises(TypeError):
            repository.get_media_file_by_path("/path/to/file")

        # Restore the handler for other tests
        repository._handlers[MediaFile] = media_file_handler

    def test_update(self, repository, sample_movie):
        """Test updating an entity."""
        # Set a property to None to test conditional update
        sample_movie.title = None

        result = repository.update(sample_movie, title="The Matrix Reloaded")
        assert result.title == "The Matrix Reloaded"

    def test_delete(self, repository, sample_movie):
        """Test deleting an entity."""
        repository.delete(sample_movie)
        assert repository.get_by_id(Movie, "0133093") is None

    def test_commit(self, repository, test_session):
        """Test committing changes."""
        # Mock the session commit method
        original_commit = test_session.commit
        test_session.commit = Mock()

        repository.commit()

        # Verify commit was called
        test_session.commit.assert_called_once()

        # Restore original commit method
        test_session.commit = original_commit

    def test_rollback(self, repository, test_session):
        """Test rolling back changes."""
        # Mock the session rollback method
        original_rollback = test_session.rollback
        test_session.rollback = Mock()

        repository.rollback()

        # Verify rollback was called
        test_session.rollback.assert_called_once()

        # Restore original rollback method
        test_session.rollback = original_rollback

    def test_close(self, repository, test_session):
        """Test closing the session."""
        # Mock the session close method
        original_close = test_session.close
        test_session.close = Mock()

        repository.close()

        # Verify close was called
        test_session.close.assert_called_once()

        # Restore original close method
        test_session.close = original_close

    def test_context_manager_success(self, test_engine, test_session):
        """Test context manager with successful operations."""
        # Create new session since we'll be replacing methods
        Session = sessionmaker(bind=test_engine)
        session = Session()

        # Mock the session methods
        original_commit = session.commit
        original_rollback = session.rollback
        original_close = session.close

        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()

        # Use the repository as a context manager
        with Repository(session) as repo:
            movie = Movie(
                id="0133096", title="The Matrix Revolutions", year=2003, anime=False
            )
            repo.add(movie)

        # Verify that commit was called, but not rollback
        session.commit.assert_called_once()
        session.rollback.assert_not_called()
        session.close.assert_called_once()

        # Restore original methods
        session.commit = original_commit
        session.rollback = original_rollback
        session.close = original_close
        session.close()

    def test_context_manager_exception(self, test_engine):
        """Test context manager with an exception."""
        # Create new session since we'll be replacing methods
        Session = sessionmaker(bind=test_engine)
        session = Session()

        # Mock the session methods
        original_commit = session.commit
        original_rollback = session.rollback
        original_close = session.close

        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()

        # Use the repository as a context manager with an exception
        with pytest.raises(ValueError):
            with Repository(session) as repo:
                raise ValueError("Test exception")

        # Verify that rollback was called, but not commit
        session.commit.assert_not_called()
        session.rollback.assert_called_once()
        session.close.assert_called_once()

        # Restore original methods
        session.commit = original_commit
        session.rollback = original_rollback
        session.close = original_close
        session.close()

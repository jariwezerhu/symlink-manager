from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy.orm import Session

from symlink_manager.media import Media, MediaFile, Movie, Show, Torrent

from .database import Base

# Type variable for SQLAlchemy models
T = TypeVar("T", bound=Base)


class EntityHandler(Generic[T]):
    """Base handler for entity operations"""

    def __init__(self, session: Session, model_class: Type[T]):
        """Initialize handler with session and model class.

        Args:
            session: SQLAlchemy database session
            model_class: The SQLAlchemy model class this handler works with
        """
        self.logger = getLogger(self.__class__.__name__)
        self.session = session
        self.model_class = model_class

    def add(self, entity: T) -> T:
        """Add entity to the session.

        Args:
            entity: The entity instance to add

        Returns:
            T: The added entity instance
        """
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, *conditions) -> List[T]:
        """Get all entities matching the specified conditions.

        Example usage:
            # Get all torrents with no media_id
            torrents = torrent_handler.get(Torrent.media_id == None)

            # Get all media files with specific season
            files = media_file_handler.get(MediaFile.season == "01")

            # Multiple conditions (AND)
            results = handler.get(Entity.attr1 == value1, Entity.attr2 > value2)

        Args:
            *conditions: SQLAlchemy filter expressions to apply

        Returns:
            List[T]: List of entities matching all conditions
        """
        query = self.session.query(self.model_class)

        if conditions:
            query = query.filter(*conditions)

        return query.all()

    def get_by_id(self, id_value: Any) -> Optional[T]:
        """Get entity by primary key.

        Args:
            id_value: The primary key value to look up

        Returns:
            Optional[T]: The entity if found, None otherwise
        """
        return self.session.get(self.model_class, id_value)

    def get_all(self) -> List[T]:
        """Get all entities.

        Returns:
            List[T]: List of all entities of this type
        """
        return self.session.query(self.model_class).all()

    def update(self, entity: T, **kwargs) -> T:
        """Update entity properties only if they are currently None.

        Args:
            entity: The entity to update
            **kwargs: Attribute name-value pairs to update

        Returns:
            T: The updated entity
        """
        for key, value in kwargs.items():
            current_value = getattr(entity, key, None)
            if current_value is None:
                setattr(entity, key, value)

        self.logger.debug(f"Updated {entity}")
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity.

        Args:
            entity: The entity to delete
        """
        self.logger.info(f"Removed {T}")
        self.session.delete(entity)
        self.session.flush()

    def _extract_attributes(self, entity: T) -> Dict[str, Any]:
        """Extract model attributes from an entity for updates.

        Excludes SQLAlchemy internal attributes and None values.

        Args:
            entity: Entity to extract attributes from

        Returns:
            Dict of attribute name-value pairs suitable for updates
        """
        if not entity:
            return {}

        attrs = {}
        for key, value in entity.__dict__.items():
            # Skip SQLAlchemy internal attributes and None values
            if not key.startswith("_") and value is not None:
                attrs[key] = value

        return attrs


class MediaHandler(EntityHandler[Media]):
    """Handler for Media entities"""

    def add(self, entity: T) -> T:
        existing = self.get_by_id(entity.id)
        if existing:
            self.logger.debug(f"Skipping existing media: {existing}")
            return existing
        else:
            self.logger.info(f"Indexing new media: {entity}")
            return super().add(entity)

    def find_by_title(self, title: str) -> List[Media]:
        """Find media by title.

        Args:
            title: Title to search for (case-insensitive)

        Returns:
            List[Media]: List of media entities matching the title
        """
        return (
            self.session.query(self.model_class)
            .filter(self.model_class.title.ilike(f"%{title}%"))
            .all()
        )


class MovieHandler(MediaHandler):
    """Handler for Movie entities"""

    pass


class ShowHandler(MediaHandler):
    """Handler for Show entities"""

    pass


class MediaFileHandler(EntityHandler[MediaFile]):
    """Handler for MediaFile entities"""

    def add(self, entity: MediaFile) -> MediaFile:
        existing = self.get_by_path(entity.symlink_path or entity.target_path)
        if existing:
            self.logger.debug(f"Updating existing media file: {existing}")
            update_attrs = self._extract_attributes(entity)
            self.update(existing, **update_attrs)
            return existing
        else:
            return super().add(entity)

    def get_by_path(self, path: Union[Path, str]) -> Optional[MediaFile]:
        """Find a media file by its path.

        Args:
            path: The path to search for (either target_path or symlink_path)

        Returns:
            Optional[MediaFile]: The media file if found, None otherwise
        """
        path_str = str(path)
        return (
            self.session.query(MediaFile)
            .filter(
                (MediaFile.target_path == path_str)
                | (MediaFile.symlink_path == path_str)
            )
            .first()
        )

    def update(self, entity: MediaFile, **kwargs) -> MediaFile:
        """Override update to also update associated Torrent's media_id."""
        # Apply normal updates
        result = super().update(entity, **kwargs)

        # Check if we've linked this file to both a torrent and a media
        if entity.torrent and entity.media:
            # Get the torrent and update its media_id if not set
            entity.torrent.media_id = entity.media_id
            self.session.flush()

        return result


class TorrentHandler(EntityHandler[Torrent]):
    """Handler for Torrent entities"""

    def add(self, entity: Torrent) -> Torrent:
        existing = self.get_by_path(entity.path)
        if existing:
            self.logger.debug(f"Skipping existing torrent: {existing}")
            return existing
        else:
            self.logger.info(f"Indexing torrent: {entity.path}")
            return super().add(entity)

    def get_by_path(self, path: Union[Path, str]) -> Optional[Torrent]:
        """Find a torrent by its path.

        Args:
            path: The path to search for

        Returns:
            Optional[Torrent]: The torrent if found, None otherwise
        """
        path_str = str(path)
        return self.session.query(Torrent).filter((Torrent.path == path_str)).first()

    def update(self, entity: Torrent, **kwargs) -> Torrent:
        """Override update to also update associated MediaFiles' media_id.

        Args:
            entity: The Torrent entity to update
            **kwargs: Attribute name-value pairs to update

        Returns:
            Torrent: The updated Torrent entity
        """
        # Track if media_id is being updated
        old_media_id = entity.media_id

        # Apply the normal update logic from parent class
        result = super().update(entity, **kwargs)

        # Check if media_id was updated from None to a value
        if old_media_id is None and entity.media_id is not None:
            # Update all associated MediaFiles that don't have a media_id yet
            self._propagate_media_id_to_files(entity)

        return result

    def _propagate_media_id_to_files(self, torrent: Torrent) -> None:
        """Propagate torrent's media_id to all its MediaFiles that don't have a media_id.

        Args:
            torrent: The Torrent entity with the updated media_id
        """
        if not torrent.media_id:
            return

        for media_file in torrent.files:
            media_file.media_id = torrent.media_id
            self.session.flush()


class Repository:
    """
    Generic repository that handles multiple entity types.
    Uses specialized handlers for type-specific operations.

    Example usage:
        # Create a repository
        repo = Repository(session)

        # Add a new movie
        movie = Movie(id="0133093", title="The Matrix", year=1999, anime=False)
        repo.add(movie)

        # Get a movie by ID
        matrix = repo.get_by_id(Movie, "0133093")

        # Using the context manager
        with Repository(session) as repo:
            movie = Movie(id="0133093", title="The Matrix",
                          year=1999, anime=False)
            repo.add(movie)
            # Transaction automatically committed if no exceptions occur
    """

    def __init__(self, session: Session):
        """Initialize repository with session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self._handlers: Dict[Type, EntityHandler] = {}

        # Register default handlers
        self.register_handler(Media, MediaHandler(session, Media))
        self.register_handler(Movie, MovieHandler(session, Movie))
        self.register_handler(Show, ShowHandler(session, Show))
        self.register_handler(Torrent, TorrentHandler(session, Torrent))
        self.register_handler(MediaFile, MediaFileHandler(session, MediaFile))

    def register_handler(self, entity_type: Type, handler: EntityHandler) -> None:
        """Register handler for entity type.

        Args:
            entity_type: The entity class
            handler: The handler instance for this entity type
        """
        self._handlers[entity_type] = handler

    def _get_handler(self, entity: Any) -> EntityHandler:
        """Get appropriate handler for entity.

        Args:
            entity: Entity instance or class

        Returns:
            EntityHandler: The appropriate handler for this entity type

        Raises:
            TypeError: If no handler is registered for this entity type
        """
        if isinstance(entity, type):
            # If entity is a class
            handler = self._handlers.get(entity)
        else:
            # If entity is an instance
            handler = self._handlers.get(type(entity))

        if not handler:
            # Try to find handler for any parent class
            entity_type = entity if isinstance(entity, type) else type(entity)
            for cls in entity_type.__mro__[1:]:
                handler = self._handlers.get(cls)
                if handler:
                    break

        if not handler:
            entity_name = (
                entity.__name__ if isinstance(
                    entity, type) else type(entity).__name__
            )
            raise TypeError(
                f"No handler registered for entity type: {entity_name}")

        return handler

    # Generic operations that work with any entity type
    def add(self, entity: T) -> T:
        """Add entity to the database.

        Args:
            entity: The entity instance to add

        Returns:
            T: The added entity instance
        """
        handler = self._get_handler(entity)
        result = handler.add(entity)
        self.session.flush()
        return result

    def get(self, entity_type: Type[T], *conditions) -> List[T]:
        """Get entities of the specified type matching the given conditions.

        Example usage:
            # Get all torrents with no media_id
            torrents = repo.get(Torrent, Torrent.media_id == None)

            # Get all media files with specific season
            files = repo.get(MediaFile, MediaFile.season == "01")

            # Multiple conditions (AND)
            results = repo.get(Entity, Entity.attr1 == value1, Entity.attr2 > value2)

        Args:
            entity_type: The entity class
            *conditions: SQLAlchemy filter expressions to apply

        Returns:
            List[T]: List of entities matching all conditions

        Raises:
            TypeError: If no handler is registered for this entity type
        """
        handler = self._handlers.get(entity_type)
        if not handler:
            raise TypeError(
                f"No handler registered for entity type: {
                    entity_type.__name__}"
            )
        return handler.get(*conditions)

    def get_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[Media]:
        """Get entity by ID and type.

        Args:
            entity_type: The entity class
            id_value: The primary key value

        Returns:
            Optional[T]: The entity if found, None otherwise

        Raises:
            TypeError: If no handler is registered for this entity type
        """
        handler = self._handlers.get(entity_type)
        if not handler:
            raise TypeError(
                f"No handler registered for entity type: {
                    entity_type.__name__}"
            )
        return handler.get_by_id(id_value)

    def get_all(self, entity_type: Type[T]):
        """Get all entities of the specified type.

        Args:
            entity_type: The entity class

        Returns:
            List[T]: List of all entities of this type

        Raises:
            TypeError: If no handler is registered for this entity type
        """
        handler = self._handlers.get(entity_type)
        if not handler:
            raise TypeError(
                f"No handler registered for entity type: {
                    entity_type.__name__}"
            )
        return handler.get_all()

    def find_media_by_title(self, title: str) -> List[Media]:
        """Find media by title.

        Args:
            title: Title to search for (case-insensitive)

        Returns:
            List[Media]: List of media entities matching the title

        Raises:
            TypeError: If MediaHandler is not registered
        """
        handler = self._handlers.get(Media)
        if not handler or not isinstance(handler, MediaHandler):
            raise TypeError("MediaHandler not registered")
        return handler.find_by_title(title)

    def get_media_file_by_path(self, path: Union[Path, str]) -> Optional[MediaFile]:
        """Get a media file by its path.

        Args:
            path: The path to search for (either target_path or symlink_path)

        Returns:
            Optional[MediaFile]: The media file if found, None otherwise

        Raises:
            TypeError: If MediaFileHandler is not registered
        """
        handler = self._handlers.get(MediaFile)
        if not handler or not isinstance(handler, MediaFileHandler):
            raise TypeError("MediaFileHandler not registered")
        return handler.get_by_path(path)

    def update(self, entity: T, **kwargs) -> T:
        """Update entity properties.

        Args:
            entity: The entity to update
            **kwargs: Attribute name-value pairs to update

        Returns:
            T: The updated entity
        """
        handler = self._get_handler(entity)
        result = handler.update(entity, **kwargs)
        self.session.flush()
        return result

    def delete(self, entity: T) -> None:
        """Delete entity.

        Args:
            entity: The entity to delete
        """
        handler = self._get_handler(entity)
        handler.delete(entity)
        self.session.flush()

    def commit(self) -> None:
        """Commit changes to the database."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback changes in case of error."""
        self.session.rollback()

    def close(self) -> None:
        """Close the database session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Enable context manager pattern for transaction handling."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle transaction completion or rollback on context exit.

        Args:
            exc_type: Exception type if an exception was raised, None otherwise
            exc_val: Exception value if an exception was raised, None otherwise
            exc_tb: Exception traceback if an exception was raised, None otherwise

        Returns:
            bool: False to propagate exceptions, True to suppress
        """
        try:
            if exc_type is not None:
                # An exception occurred, rollback the transaction
                self.rollback()
            else:
                # No exception, commit the transaction
                self.commit()
        finally:
            self.close()
        # Don't suppress exceptions
        return False

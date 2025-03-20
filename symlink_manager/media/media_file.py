from typing import Optional, Union
from pathlib import Path

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from symlink_manager.database import Base


class MediaFile(Base):
    __tablename__ = "mediafiles"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    media_id = Column(
        String,
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=True,
        doc="Reference to the parent Media entity",
    )
    torrent_id = Column(
        Integer,
        ForeignKey("torrents.id", ondelete="CASCADE"),
        nullable=True,
        doc="Reference to the Torrent that provided this file",
    )

    # File path information
    symlink_path = Column(
        String, nullable=True, doc="String representation of path to library symlink"
    )
    target_path = Column(
        String, nullable=False, doc="String representation of path to torrent file"
    )

    # Metadata
    file_size = Column(Integer, nullable=False,
                       doc="Size of the file in bytes")
    season = Column(
        String,
        nullable=True,
        doc="String representing season number (i.e. 01). Only applicable for shows",
    )
    episode = Column(
        String,
        nullable=True,
        doc="String representing episode number (i.e. 01). Only applicable for shows",
    )

    # Relationships
    media = relationship("Media", back_populates="files",
                         doc="Parent media entity")
    torrent = relationship(
        "Torrent", back_populates="files", doc="Parent torrent entity"
    )

    # Indexes for faster querying
    __table_args__ = (
        Index("idx_mediafile_media_id", "media_id"),
        Index("idx_mediafile_torrent_id", "torrent_id"),
    )

    @classmethod
    def create(
        cls,
        target_path: str,
        file_size: int,
        media_id: Optional[str] = None,
        torrent_id: Optional[int] = None,
        symlink_path: Optional[str] = None,
        season: Optional[str] = None,
        episode: Optional[str] = None,
    ) -> "MediaFile":
        """Factory method to create a MediaFile.

        Args:
            target_path: Path to the torrent file (required)
            file_size: Size of the file in bytes (required)
            media_id: Reference to the parent Media entity
            torrent_id: Reference to the Torrent
            symlink_path: Path to library symlink
            season: Season number (for shows)
            episode: Episode number (for shows)

        Returns:
            New MediaFile instance
        """
        return cls(
            target_path=target_path,
            file_size=file_size,
            media_id=media_id,
            torrent_id=torrent_id,
            symlink_path=symlink_path,
            season=season,
            episode=episode,
        )

    def get_path(self) -> Optional[Path]:
        """
        Return the appropriate filename for this media file.

        Returns:
            Path object representing the filename, or None if media association is missing

        The format is:
        - For movies: {title} ({year}) {imdb-tt{id}}.{suffix}
        - For shows: {title} ({year}) - s{season}e{episode}.{suffix}
        """
        # Check if the media file is associated with a Media entity
        if not self.media:
            return None

        # Get the file suffix from the target path
        suffix = Path(self.target_path).suffix

        if self.episode:
            # Format with season and episode
            filename = f"{self.media.title} ({self.media.year}) - s{self.season}e{
                self.episode
            }{suffix}"
        else:
            # For movies, use the Media title, year, and ID plus suffix
            filename = f"{self.media.title} ({self.media.year}) {{imdb-tt{
                self.media.id
            }}}{suffix}"

        # Return just the filename as a Path object
        return Path(filename)

    def __repr__(self):
        return f"<MediaFile(id={self.id}, media_id={self.media_id}, torrent_id={self.torrent_id})>"

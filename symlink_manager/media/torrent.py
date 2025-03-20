from pathlib import Path
from typing import Optional, Union

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from symlink_manager.database import Base


class Torrent(Base):
    __tablename__ = "torrents"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    torrent_title = Column(String, nullable=False,
                           doc="Parsed movie/show title")
    torrent_year = Column(Integer, nullable=True, doc="Parsed movie/show year")

    # Foreign key to Media
    media_id = Column(
        String,
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=True,
        doc="Reference to the parent Media entity",
    )

    # Path information
    path = Column(String, nullable=False, doc="Path to the torrent")

    # Relationships
    media = relationship("Media", back_populates="torrents",
                         doc="Parent media entity")

    files = relationship(
        "MediaFile",
        back_populates="torrent",
        cascade="all, delete-orphan",
        doc="Files included in this torrent",
    )

    # Indexes for query optimization
    __table_args__ = (Index("idx_torrent_media_id", "media_id"),)

    @classmethod
    def create(
        cls, path: Union[Path, str], title: str, year: Optional[int]
    ) -> "Torrent":
        return cls(path=path, torrent_title=title, torrent_year=year)

    def __repr__(self):
        return f"<Torrent(id={self.id}, media_id={self.media_id}, path={self.path})>"

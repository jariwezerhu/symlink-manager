from typing import Union
from pathlib import Path

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from symlink_manager.database import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(String, primary_key=True, doc="IMDb ID for the show/movie")
    title = Column(String, nullable=False, doc="Title as reported by IMDb")
    year = Column(Integer, nullable=False, doc="Year as reported by IMDb")
    anime = Column(Boolean, nullable=False,
                   doc="Boolean if media is anime or not")
    media_type = Column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": "media",
                       "polymorphic_on": media_type}

    torrents = relationship("Torrent", back_populates="media")
    files = relationship("MediaFile", back_populates="media")

    @classmethod
    def create(
        cls, kind: str, imdb_id: str, title: str, year: str, anime: bool
    ) -> Union["Movie", "Show"]:
        media_type = Movie if kind == "movie" else Show
        return media_type(
            id=imdb_id,
            title=title,
            year=year,
            anime=anime,
        )

    def get_path(
        self, library_base: Union[Path, str], separate_anime: bool = True
    ) -> Path:
        """Return the base path for this media in the library"""
        if isinstance(self, Movie):
            category = "anime_movies" if self.anime and separate_anime else "movies"
        else:
            category = "anime_shows" if self.anime and separate_anime else "shows"

        media_name = f"{self.title} ({self.year}) {{imdb-tt{self.id}}}"
        return Path(library_base) / category / media_name

    def __str__(self):
        return f"{self.media_type}: {self.title} ({self.year}) {{{self.id}}}"

    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.id}', title='{self.title}', year={self.year})"


class Movie(Media):
    __tablename__ = "movies"

    imdb_id = Column(String, ForeignKey("media.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "movie",
    }


class Show(Media):
    __tablename__ = "shows"

    imdb_id = Column(String, ForeignKey("media.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "show",
    }

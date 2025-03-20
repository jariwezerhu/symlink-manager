# Symlink Manager

A Python-based utility for managing symlinks between torrent downloads and a structured media library.

## Overview

Symlink Manager helps organize your media collection by creating a well-structured library of symbolic links to your torrent downloads. It scans both your torrent download directory and existing media library, matches media files with metadata from IMDb, and creates properly named symbolic links organized by media type and attributes.

## Features

- **Automatic scanning** of torrent and media library directories
- **Metadata retrieval** from IMDb for accurate media information
- **Intelligent matching** between torrents and media metadata
- **Structured organization** with configurable categories (movies, shows, anime)
- **Symbolic link management** preserving disk space while maintaining organization

## System Requirements

- Python 3.10 or higher
- Linux-based OS (for symbolic link support)
- Read/write access to media folders

## Installation

### From PyPI

```bash
pip install symlink-manager
```

### From Source

```bash
git clone https://github.com/jari/symlink-manager.git
cd symlink-manager
pip install .
```

## Configuration

The system uses the following directory structure:

- **Torrent Base**: Directory containing downloaded torrents
- **Library Base**: Root directory for the organized media library
  - `movies/`: Regular movies
  - `shows/`: TV shows
  - `anime_movies/`: Anime movies
  - `anime_shows/`: Anime TV shows

## Usage

### Basic Setup

```python
from symlink_manager.database import create_tables, Session
from symlink_manager.scanners import LibraryScanner, TorrentScanner
from symlink_manager.services import Parser, Resolver

# Initialize database
create_tables()

# Create service components
parser = Parser()
resolver = Resolver()

# Create scanners
torrent_scanner = TorrentScanner("/path/to/torrents", parser, resolver)
library_scanner = LibraryScanner("/path/to/media/library", parser)

# Perform initial scan
library_scanner.full_scan()
torrent_scanner.full_scan()
torrent_scanner.add_missing_media_to_torrents()
```

### Creating Symlinks

```python
from symlink_manager.database import Repository, Session
from symlink_manager.media import MediaFile
from symlink_manager.symlinker import Symlinker

# Create category paths
category_paths = {
    "movies": "/path/to/library/movies",
    "shows": "/path/to/library/shows",
    "anime_movies": "/path/to/library/anime_movies",
    "anime_shows": "/path/to/library/anime_shows"
}

# Create symlinker
symlinker = Symlinker("/path/to/library", category_paths, separate_anime=True)

# Get media files to link
with Repository(Session()) as repo:
    media_files = repo.get_all(MediaFile)
    for media_file in media_files:
        symlinker.create_symlink(media_file)
```

## Core Components

### Models

- **Media**: Base class for all media types with common attributes
  - **Movie**: Specific implementation for movies
  - **Show**: Specific implementation for TV shows
- **MediaFile**: Represents individual media files with path information
- **Torrent**: Represents downloaded torrents and their contents

### Services

- **Parser**: Extracts metadata from directory and file names
- **Resolver**: Retrieves detailed media information from IMDb
- **Symlinker**: Creates symbolic links from torrent files to the media library

### Scanners

- **LibraryScanner**: Scans and indexes the organized media library
- **TorrentScanner**: Scans and indexes downloaded torrents

## Database Schema

The system uses a SQLite database with the following tables:
- `media`: Base table for media entities
- `movies`: Movie-specific data
- `shows`: TV show-specific data
- `mediafiles`: Individual media files
- `torrents`: Torrent download information

## License

MIT License

## Author

Created by Jari (jariwezer@gmail.com)

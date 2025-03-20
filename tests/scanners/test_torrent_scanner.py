import os
from pathlib import Path
import pytest

# Import your TorrentScanner from its module.
from symlink_manager.scanners.torrent_scanner import TorrentScanner

# --- Fake Classes and Helpers --- #


class FakeParser:
    def __init__(self, torrent_info=None, episode_info=(None, None)):
        self.torrent_info = torrent_info or {
            "title": "TestTitle",
            "year": 2020,
            "kind": "movie",
        }
        self.episode_info = episode_info

    def parse_torrent(self, torrent_path):
        # Simulate parsing by returning a copy of self.torrent_info.
        return self.torrent_info

    def parse_torrent_episode(self, file_path):
        # Return episode info (season, episode).
        return self.episode_info


class FakeResolver:
    def __init__(self, imdb_id="tt1234567", media_info=None):
        self.imdb_id = imdb_id
        # Include 'kind' and 'anime' keys by default.
        self.media_info = media_info or {
            "title": "TestTitle",
            "year": 2020,
            "imdb_id": imdb_id,
            "kind": "show",
            "anime": False,
        }

    def get_imdb_id(self, title, year, kind):
        return self.imdb_id

    def get_media(self, imdb_id):
        return self.media_info


# Dummy repository and related dummy classes used in tests.
class DummyRepository:
    def __init__(self):
        self.added_items = []
        self.updated = {}

    def add(self, obj):
        self.added_items.append(obj)
        if not hasattr(obj, "id"):
            obj.id = len(self.added_items)
        return obj

    def update(self, obj, **kwargs):
        self.updated[obj.path] = kwargs

    def get_all(self, model):
        # Return dummy torrents; adjust as needed.
        return [
            DummyTorrent(path="/fake/path1"),
            DummyTorrent(path="/fake/path2", media_id="existing"),
        ]

    def get_by_id(self, model, id):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class DummyTorrent:
    def __init__(self, path, media_id=None, id=1):
        self.path = path
        self.media_id = media_id
        self.id = id


# Patch Repository and Session in the module where TorrentScanner is defined.
@pytest.fixture(autouse=True)
def patch_repository(monkeypatch):
    from symlink_manager.scanners import (
        torrent_scanner,
    )  # import the module where TorrentScanner is defined

    # Patch Repository using the module's __dict__
    monkeypatch.setitem(
        torrent_scanner.__dict__, "Repository", lambda session: DummyRepository()
    )
    # Optionally patch Session if needed.
    monkeypatch.setitem(torrent_scanner.__dict__, "Session", lambda: None)


# --- Tests --- #


def test_get_torrent_files(tmp_path):
    # Create a temporary directory simulating a torrent folder.
    torrent_dir = tmp_path / "torrent"
    torrent_dir.mkdir()

    # Create valid video files.
    valid_file = torrent_dir / "video1.mkv"
    valid_file.write_text("dummy content")
    # Create invalid extension file.
    invalid_file = torrent_dir / "document.txt"
    invalid_file.write_text("dummy content")
    # Create a subdirectory (should be skipped).
    subdir = torrent_dir / "subdir"
    subdir.mkdir()
    # Create a valid video file inside subdir if recursion is enabled.
    nested_file = subdir / "video2.mp4"
    nested_file.write_text("dummy content")

    fake_parser = FakeParser()
    fake_resolver = FakeResolver()
    scanner = TorrentScanner(torrent_dir, fake_parser, fake_resolver)

    # Test non-recursive: only the top-level valid file should be returned.
    files_non_recursive = scanner.get_torrent_files(
        torrent_dir, recursive=False)
    assert valid_file in files_non_recursive
    assert nested_file not in files_non_recursive

    # Test recursive: both valid_file and nested_file should be returned.
    files_recursive = scanner.get_torrent_files(torrent_dir, recursive=True)
    assert valid_file in files_recursive
    assert nested_file in files_recursive
    # The invalid file should not be included.
    for f in files_recursive:
        assert f.suffix.lower() in TorrentScanner.VIDEO_EXTENSIONS


def test_get_torrent_paths(tmp_path):
    # Create a temporary base directory with mixed content.
    base_dir = tmp_path / "torrents"
    base_dir.mkdir()
    # Create directories (valid torrent directories).
    dir1 = base_dir / "torrent1"
    dir1.mkdir()
    dir2 = base_dir / "torrent2"
    dir2.mkdir()
    # Create a file (should be skipped).
    file_in_base = base_dir / "not_a_dir.txt"
    file_in_base.write_text("dummy content")

    fake_parser = FakeParser()
    fake_resolver = FakeResolver()
    scanner = TorrentScanner(base_dir, fake_parser, fake_resolver)

    paths = list(scanner.get_torrent_paths())
    assert dir1 in paths
    assert dir2 in paths
    assert file_in_base not in paths


def test_get_torrent_info(tmp_path):
    # Set up a fake torrent directory with a valid video file.
    torrent_dir = tmp_path / "torrent"
    torrent_dir.mkdir()
    video_file = torrent_dir / "movie.mp4"
    video_file.write_text("dummy content")

    fake_parser = FakeParser(
        torrent_info={"title": "MyMovie", "year": 2021, "kind": "movie"}
    )
    fake_resolver = FakeResolver()
    scanner = TorrentScanner(torrent_dir, fake_parser, fake_resolver)

    info = scanner.get_torrent_info(torrent_dir)
    # Expect a dictionary with the torrent info and a non-empty list of files.
    assert info is not None
    assert info["title"] == "MyMovie"
    assert info["year"] == 2021
    assert info["kind"] == "movie"
    assert isinstance(info["files"], list)
    assert len(info["files"]) >= 1


def test_get_torrent_info_no_valid_files(tmp_path, caplog):
    # Create a torrent directory with no valid video files.
    torrent_dir = tmp_path / "torrent"
    torrent_dir.mkdir()
    (torrent_dir / "file.txt").write_text("dummy content")

    fake_parser = FakeParser()
    fake_resolver = FakeResolver()
    scanner = TorrentScanner(torrent_dir, fake_parser, fake_resolver)

    info = scanner.get_torrent_info(torrent_dir)
    # Expect info to be None because there are no video files.
    assert info is None
    # Optionally, check for a warning log message.
    assert any(
        "No valid torrent files" in record.message for record in caplog.records)


def test_index_torrent(tmp_path):
    # Create dummy files with known file sizes.
    torrent_dir = tmp_path / "torrent"
    torrent_dir.mkdir()
    video_file1 = torrent_dir / "video1.mp4"
    video_file1.write_bytes(b"\x00" * 100)
    video_file2 = torrent_dir / "video2.mp4"
    video_file2.write_bytes(b"\x00" * 200)

    fake_parser = FakeParser(
        torrent_info={"title": "TestMovie", "year": 2020, "kind": "movie"}
    )
    fake_resolver = FakeResolver()
    scanner = TorrentScanner(torrent_dir, fake_parser, fake_resolver)

    # Use the index_torrent method directly. For movies, the largest file (video_file2) should be selected.
    scanner.index_torrent(
        torrent_path=torrent_dir,
        files=[video_file1, video_file2],
        kind="movie",
        title="TestMovie",
        year=2020,
    )
    # Since we use DummyRepository, the test ensures no exception is raised.
    # You can extend this test to verify DummyRepository.added_items if needed.


def test_add_missing_media_to_torrents(tmp_path, caplog, monkeypatch):
    # Ensure INFO messages are captured.
    caplog.set_level("INFO")

    # Patch Media.create to return a dummy media object.
    from symlink_manager.media import Media

    monkeypatch.setattr(
        Media, "create", lambda **kwargs: type("DummyMedia", (), kwargs)()
    )

    fake_parser = FakeParser(
        torrent_info={"title": "TestShow", "year": 2020, "kind": "show"}
    )
    fake_resolver = FakeResolver(
        imdb_id="tt7654321",
        media_info={
            "title": "TestShow",
            "year": 2020,
            "imdb_id": "tt7654321",
            "kind": "show",  # Provide required key
            "anime": False,  # Provide required key
        },
    )
    scanner = TorrentScanner(tmp_path, fake_parser, fake_resolver)

    # Call add_missing_media_to_torrents.
    scanner.add_missing_media_to_torrents()

    # Check logs to verify that torrents were processed and linked.
    messages = [record.message for record in caplog.records]
    assert any("Linked torrent" in message for message in messages)

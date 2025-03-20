import sys

from symlink_manager.config import Config
from symlink_manager.database import create_tables
from symlink_manager.logger import configure_logging
from symlink_manager.scanners import LibraryScanner, TorrentScanner
from symlink_manager.services import Parser, Resolver
from symlink_manager.services import Symlinker
from symlink_manager.database import Repository, Session
from symlink_manager.media import Torrent


def run_initial_scan(
    torrent_scanner: TorrentScanner,
    library_scanner: LibraryScanner,
    parser: Parser,
    resolver: Resolver,
):
    library_scanner.full_scan()
    torrent_scanner.full_scan()
    torrent_scanner.add_missing_media_to_torrents()


def main():
    config = Config()

    configure_logging(config.get_logging_level())
    create_tables(drop_existing=True)

    parser = Parser()
    resolver = Resolver()
    torrent_scanner = TorrentScanner(
        config.get_torrents_path(), parser, resolver)
    library_scanner = LibraryScanner(config.get_library_path(), parser)
    symlinker = Symlinker(config.get_library_path(),
                          config.get_separate_anime())

    run_initial_scan(torrent_scanner, library_scanner, parser, resolver)
    with Repository(Session()) as repo:
        torrents = repo.get_all(Torrent)
        for torrent in torrents:
            sorted_media_files = sorted(
                torrent.files, key=lambda file: file.file_size, reverse=True
            )
            for media_file in sorted_media_files:
                if not media_file.symlink_path:
                    symlinker.create_symlink(media_file)


if __name__ == "__main__":
    sys.exit(main())

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md file if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="symlink-manager",
    version="0.1.0",
    description="Module for handling media file symlinks between torrents and media library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jari",
    author_email="jariwezer@gmail.com",
    url="https://github.com/jariwezerhu/symlink-manager",
    project_urls={
        "Bug Tracker": "https://github.com/jariwezerhu/symlink-manager/issues",
        "Source Code": "https://github.com/jariwezerhu/symlink-manager",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "sqlalchemy>=1.4.0",
        "cinemagoer>=2023.0.0",
        "parsett",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Multimedia :: Video",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.10",  # Balance between modern features and adoption
    keywords="media, torrent, symlink, imdb, file management",
    license="MIT",
)

from pathlib import Path

from file_metadata import FileMetadata, FILE_EXTENSIONS


class DirMetadata:
    def __init__(self, path: Path):
        self.path = path

        self._paths: list[Path] = []
        self._file_metadata: list[FileMetadata] = []

        for p in path.glob("*.*"):
            if not p.is_file():
                continue

            if p.suffix.lower() not in FILE_EXTENSIONS:
                continue

            self._paths.append(p)

        n_paths = len(self._paths)
        if not n_paths:
            raise ValueError(f'directory "{path}" is empty')

        print(f" --> found {n_paths} media file{'s' if n_paths > 0 else ''}")

        if n_paths <= 3:
            # Always generate metadata if folder contains less than 3 files
            self._file_metadata = [FileMetadata(p) for p in self._paths]
        else:
            # Add first, middle and last files for metadata generation
            for index, p in enumerate(self._paths):
                if index in [0, n_paths // 2, n_paths - 1]:
                    self._file_metadata.append(FileMetadata(p))

    @property
    def file_metadata(self):
        return self._file_metadata

    @property
    def file_paths(self):
        return self._file_metadata

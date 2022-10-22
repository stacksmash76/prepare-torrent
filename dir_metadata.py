from pathlib import Path

from file_metadata import FileMetadata, FILE_EXTENSIONS


class DirMetadata:
    def __init__(self, path: Path):
        self.path = path

        self.paths: list[Path] = []
        self.file_metadata: list[FileMetadata] = []

        for p in path.glob("*.*"):
            if not p.is_file():
                continue

            if p.suffix.lower() not in FILE_EXTENSIONS:
                continue

            self.paths.append(p)

        n_paths = len(self.paths)
        if not n_paths:
            raise ValueError(f'directory "{path}" is empty')

        print(f" --> found {n_paths} media file{'s' if n_paths > 0 else ''}")

        # Sort paths according to ASC file name
        self.paths = sorted(self.paths)

        if n_paths <= 3:
            # Always generate metadata if folder contains less than 3 files
            self.file_metadata = [FileMetadata(p) for p in self.paths]
        else:
            # Add first, middle and last files for metadata generation
            for index, p in enumerate(self.paths):
                if index in [0, n_paths // 2, n_paths - 1]:
                    self.file_metadata.append(FileMetadata(p))

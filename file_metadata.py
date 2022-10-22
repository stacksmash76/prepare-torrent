import time
from pathlib import Path

from config import Config
from mediainfo import MediaInfoParser

FILE_EXTENSIONS = [".mkv", ".mp4", ".avi"]


class FileMetadata:
    def __init__(self, path: Path):
        self.path = path.absolute()

        if Config.sanitize_filename:
            self._sanitize_filename()

        self.mediainfo = MediaInfoParser(self.path)

        self.duration = 0.0
        try:
            self.duration = self.mediainfo.get_video_duration()
        except ValueError as e:
            print(f"\nfailed to obtain video duration for file: {self.path.name}")
            print(f" --> exception: {e}\n")

    def _sanitize_filename(self) -> None:
        new_name = self.path.name.strip()\
            .replace(" ", ".")\
            .replace(".-.", ".")

        # Nothing to do here
        if new_name == self.path.name:
            return

        if Config.sanitize_filename_prompt:
            prompt = Config.binary_choice(
                "The specified filename can be sanitized:\n"
                f" --> Current:   {self.path.name}\n"
                f" --> Suggested: {new_name}\n"
                f"Do you wish to change the filename? (y/n)\n"
            )

            # The user decided not to sanitize the filename, stop
            if not prompt:
                return

        # Move the file
        self.path = self.path.replace(self.path.with_name(new_name))

        # Sleep a bit for the FS changes to be propagated properly
        # (might be an issue on some filesystems)
        time.sleep(0.01)

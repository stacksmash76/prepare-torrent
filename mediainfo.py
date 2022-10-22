from pathlib import Path
from pymediainfo import MediaInfo

from config import Config


class MediaInfoParser:
    def __init__(self, path: Path):
        self.media_info = MediaInfo.parse(
            filename=str(path),
            library_file=Config.path_mediainfo_library
        )
        self.text = str(MediaInfo.parse(
            filename=str(path),
            library_file=Config.path_mediainfo_library,
            output="",
            full=False
        )).strip()

        # Replace full path with relative path
        parent = str(path.parent.absolute())
        # Sanity check
        if len(parent) > 3:
            self.text = self.text.replace(parent + "/", "").replace(parent, "")

    # throws a ValueError exception on error
    # note: the duration is in miliseconds
    def get_video_duration(self) -> float:
        video_tracks = self.media_info.video_tracks
        if not video_tracks:
            raise ValueError("mediainfo is missing a video track")

        for t in video_tracks:
            if t.duration:
                return float(t.duration)

        raise ValueError("failed to obtain video track duration")

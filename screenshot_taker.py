import os
import subprocess
from pathlib import Path
from typing import Optional

from config import Config
from dir_metadata import DirMetadata
from file_metadata import FileMetadata


def ms_to_hhmmss(msec: float) -> str:
    step = msec / 1000
    seconds = int(step % 60)
    minutes = int((step / 60) % 60)
    hours = int((step / 3600) % 24)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


class ScreenshotTaker:
    def __init__(
        self,
        file_metadata: Optional[FileMetadata] = None,
        dir_metadata: Optional[DirMetadata] = None,
    ):
        if not file_metadata and not dir_metadata:
            raise AttributeError("file_metadata and dir_metadata mustn't be None")
        elif file_metadata and dir_metadata:
            raise AttributeError(
                "file_metadata and dir_metadata mustn't be specified at the same time"
            )

        self.created_image_files: list[Path] = []

        self.file_metadata = file_metadata
        self.dir_metadata = dir_metadata

        self.is_single_file = self.file_metadata is not None

        found = False
        for i in range(0, 500):
            name = ".screens" + (f"{i:03}" if i > 0 else "")

            self.screenshots_dir = (
                self.file_metadata.path.with_name(name)
                if self.is_single_file else (self.dir_metadata.path / name)
            )
            if not self.screenshots_dir.exists():
                found = True
                break
            elif self.screenshots_dir.is_dir():
                n_children = len(os.listdir(self.screenshots_dir))
                if not n_children:
                    found = True
                    break

        if not found:
            raise RuntimeError("failed to find a suitable screenshot directory")

    def generate(self):
        self.screenshots_dir.mkdir(exist_ok=True)

        n_screenshots = Config.screenshots_n_preprocess
        if self.is_single_file:
            self._generate_screenshots(
                file=self.file_metadata,
                it_from=0,
                it_to=n_screenshots
            )
        else:
            # Partition indices into 3 parts
            n_parts = len(self.dir_metadata.file_metadata)
            r, k = n_screenshots % n_parts, n_screenshots // n_parts

            # Iterate over available files
            for i, file_metadata in enumerate(self.dir_metadata.file_metadata):
                self._generate_screenshots(
                    file=file_metadata,
                    it_from=0 if i == 0 else k * i + r,
                    it_to=k * (i + 1) + r
                )

    def cleanup(self) -> None:
        # Delete temporary files
        if not Config.screenshots_delete_after_use:
            return

        print("cleaning up leftover screenshot files and removing .screens dir")
        try:
            for f in self.created_image_files:
                f.unlink(missing_ok=True)
            self.screenshots_dir.rmdir()
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f"failed to remove .screens dir: {e}")

    def _generate_screenshots(self, file: FileMetadata, it_from: int, it_to: int) -> None:
        if file.duration <= 0:
            print(f'skipping screenshots for "{file.path.name}": video_duration <= 0')
            return

        duration = file.duration
        if Config.screenshots_no_spoilers:
            duration /= 2

        print(f'generating screenshots for "{file.path.name}"')
        print(f" --> considering duration {ms_to_hhmmss(duration)} (divided into {it_to - it_from} pieces)")

        # Gather conditional ffmpeg args
        # conditional_args: list[str] = []

        # TODO: tonemapping?
        # -vf "zscale=transfer=linear,tonemap=hable,zscale=transfer=bt709"
        # scene_filter = Config.screenshots_ffmpeg_scene_filter
        # if scene_filter is not None:
        #    conditional_args += ["-vf", f"select='gt(scene,{scene_filter})'"]

        for i in range(it_from + 1, it_to + 1):
            msec = int((i * duration) // (it_to + 1))
            print(f" --> {i}/{Config.screenshots_n_preprocess} ({ms_to_hhmmss(msec)})")

            output_file = self.screenshots_dir / f"pre_{i:03}.png"
            self.created_image_files.append(output_file)

            _output = subprocess.run(
                executable="ffmpeg",
                args=[
                    # overwrite files without asking
                    "-y",
                    # throw an error if something goes wrong
                    "-loglevel", "level+error",
                    # take a screenshot starting at this timestamp
                    "-ss", f"{msec}ms",
                    # specify input file
                    "-i", str(file.path),
                    # only I-frames
                    #"-skip_frame", "nokey",
                    # add conditional args
                    # *conditional_args,
                    # take a screenshot over 1 frame
                    "-frames:v", "1",
                    # transparent quality, i.e. don't re-encode
                    "-q:v", "10",
                    # output as png
                    "-c:v", "png",
                    # specify output file
                    str(output_file),
                ],
                check=True,
            )

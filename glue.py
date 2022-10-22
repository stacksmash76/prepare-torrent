import time
import json
import asyncio
import pyimgbox
from torf import Torrent
from pathlib import Path
from typing import Optional

from config import Config
from screenshot_taker import ScreenshotTaker
from screenshot_processor import ScreenshotProcessor
from dir_metadata import DirMetadata
from file_metadata import FileMetadata, FILE_EXTENSIONS


def get_imgbox_history_db() -> tuple[dict, Optional[Path]]:
    if not Config.screenshots_imgbox_history:
        return {}, None

    try:
        db_path = Path(Config.screenshots_imgbox_history).expanduser()
        if db_path.exists():
            if not db_path.is_file():
                raise RuntimeError("screenshots_imgbox_history is not a file")

            with db_path.open() as fp:
                db = json.load(fp=fp)
        else:
            db = {}

        return db, db_path
    except Exception as e:
        print(f" --> couldn't acquire imgbox history file: {e}")
        return {}, None


class Glue:
    def __init__(self, path: str):
        self.media_dir: Optional[DirMetadata] = None
        self.media_file: Optional[FileMetadata] = None

        print(f'processing "{path}"')

        self.path = Path(path).expanduser().resolve(strict=True)
        if not self.path.exists():
            raise AttributeError("path doesn't exist")

        if self.path.is_dir():
            print(f" --> the path was resolved to a directory")

            media_dir = DirMetadata(self.path)
            if len(media_dir.file_metadata) == 1:
                self.media_file = media_dir.file_metadata[0]
            else:
                self.media_dir = media_dir
        elif self.path.is_file():
            print(f" --> the path was resolved to a file")
            self.media_file = FileMetadata(self.path)
        else:
            raise ValueError("given path is neither a file nor a directory")

        if self.media_file is not None:
            self.screenshot_taker = ScreenshotTaker(file_metadata=self.media_file)
        elif self.media_dir is not None:
            self.screenshot_taker = ScreenshotTaker(dir_metadata=self.media_dir)

        self.screenshot_submissions: list[pyimgbox.Submission] = []

    async def _upload_to_imgbox(self, paths: list[str]) -> None:
        suffix = "s" if len(paths) > 1 else ""
        print(f"uploading {len(paths)} screenshot{suffix} to imgbox.com")

        async with pyimgbox.Gallery(
            comments_enabled=False,
            adult=bool(Config.screenshots_imgbox_mark_adult),
            thumb_width=int(Config.screenshots_imgbox_thumb_width)
        ) as gallery:
            async for submission in gallery.add(paths):
                if not submission['success']:
                    print(f" --> failed to upload \"{submission['filename']}\": {submission['error']}")
                else:
                    self.screenshot_submissions.append(submission)

    def generate_screenshots(self) -> None:
        if self.screenshot_taker is None:
            return

        try:
            self.screenshot_taker.generate()

            processor = ScreenshotProcessor(self.screenshot_taker.screenshots_dir)
            processor.process()

            paths = [str(screenshot.path) for screenshot in processor.screenshots]
            if not paths:
                print("no screenshots to upload")
                return

            asyncio.run(self._upload_to_imgbox(paths))
            if self.screenshot_submissions:
                db, db_path = get_imgbox_history_db()

                print("imgbox submissions:")
                for i, submission in enumerate(self.screenshot_submissions):
                    filename, edit_url = submission["filename"], submission["edit_url"]
                    if submission["success"]:
                        print(f"{' ':2}#{i + 1:02} {filename}: {edit_url}")
                    else:
                        print(f"{' ':2}ERROR {filename}: {edit_url}")

                    if edit_url in db:
                        db[edit_url].append(submission["filepath"])
                    else:
                        db[edit_url] = [submission["filepath"]]

                if db_path is not None:
                    print(f"updating imgbox history db")
                    with db_path.open("w") as fp:
                        json.dump(db, fp=fp)

                    print(" --> done!")
        finally:
            self.screenshot_taker.cleanup()

    @staticmethod
    def _get_torrent_name(s: str) -> str:
        for ext in FILE_EXTENSIONS:
            s = s.removesuffix(ext)
        return s

    def create_torrent(self) -> None:
        assert self.media_file is not None or self.media_dir is not None

        file_path = Path(Config.torrent_output_dir).expanduser().resolve(strict=True)
        if not file_path.is_dir():
            raise ValueError("config.torrent_output_dir is not a directory!")

        print(f'creating torrent and saving to dir: "{file_path}"')

        t = Torrent(
            trackers=[Config.tracker_announce_url],
            randomize_infohash=True,
            private=True,
            comment=":)",
        )
        if self.media_file is not None:
            t.path = str(self.media_file.path)
            t.name = self._get_torrent_name(str(self.media_file.path.name))
        else:
            t.name = self._get_torrent_name(str(self.path.name))
            t.filepaths = [str(p.path) for p in self.media_dir.file_paths]

        torrent_filename = file_path / (t.name + ".torrent")
        print(f' --> generated torrent filename: "{torrent_filename.name}"')

        overwrite = False
        if torrent_filename.exists():
            prompt = Config.binary_choice(
                f"A .torrent file with the same already exists. \n"
                "Do you want to overwrite it? (y/n)\n"
            )
            if prompt:
                overwrite = True
            else:
                raise ValueError(
                    "aborting torrent creation process - .torrent file already exists."
                )

        print("hashing .torrent file. this might take a while...")

        t_start = time.time()

        def print_cb(_torrent, _filepath, pieces_done, pieces_total):
            elapsed = time.time() - t_start
            print(
                f" --> {pieces_done / pieces_total * 100:3.0f}% done ({elapsed:.2f}s)"
            )

        if Config.torrent_hash_cpu_threads is not None:
            print(f" --> using {Config.torrent_hash_cpu_threads} threads per cpu core")

        t.generate(
            threads=Config.torrent_hash_cpu_threads, callback=print_cb, interval=1
        )
        t.write(str(torrent_filename), overwrite=overwrite)

        print(f" --> done!")

    def create_description(self) -> None:
        print("generating description")

        result = ""
        if self.media_file is not None:
            result += f"[mediainfo]\n{self.media_file.mediainfo.text}\n[/mediainfo]\n\n"
        elif self.media_dir is not None:
            for f in self.media_dir.file_metadata:
                result += f"[mediainfo]\n{f.mediainfo.text}\n[/mediainfo]\n\n"

        result += "[screens]\n\n"
        for submission in self.screenshot_submissions:
            web_url, thumbnail_url = submission["web_url"], submission["thumbnail_url"]
            result += f"[url={web_url}][img]{thumbnail_url}[/img][/url]\n"

        print("=" * 24 + "[ DESCRIPTION ]" + "=" * 24)
        print(result)
        print("=" * 63)

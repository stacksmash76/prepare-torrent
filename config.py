from typing import Optional


class Config:
    #
    # Path to the MediaInfo library
    #
    # Use this only if pymedialibrary cannot detect your MediaInfo installation
    # e.g. "C:/MediaInfo/MediaInfo.dll" (just a pseudo-example)
    path_mediainfo_library: Optional[str] = None
    #
    # Sanitize filenames
    #
    # Currently this replaces all spaces with dots
    # and removes whitespace from beginning and end of filename (if needed)
    #
    sanitize_filename: bool = False
    #
    # Whether the script should prompt a user input in order to decide
    # whether an action is necessary
    #
    # Only valid if sanitize_filename is set to True
    sanitize_filename_prompt: bool = True
    #
    # Your tracker announce URL
    #
    tracker_announce_url: str = "https://announce.tracker/your_key"
    #
    # Output directory for .torrent files
    #
    # "." means current directory. Useful if you want your client to auto-add your torrent
    # Note: The directory must exist.
    torrent_output_dir: str = "."
    #
    # How many threads per CPU core should be used
    #
    torrent_hash_cpu_threads: int = 4
    #
    # If no spoilers is enabled, then screenshots are taken from first half of the movie or tv show
    # otherwise screenshots are taken at regular intervals from the whole movie or tv show
    #
    # Note: This uses the same implementation as gg-bot.
    screenshots_no_spoilers: bool = True
    #
    # Whether screenshots should be analyzed and evaluated based on
    # a combination of file size, BRISQUE image quality and
    # sharpness estimation metrics.
    #
    # Note: Requires a few "heavier" python packages.
    screenshots_analyze: bool = True
    #
    # Width of imgbox.com thumbnails
    #
    screenshots_imgbox_thumb_width: int = 300
    #
    # Mark imgbox.com galleries as 'adult content'.
    #
    screenshots_imgbox_mark_adult: bool = False
    # Compute screenshot scoring based on theoretical FS limit of 10MB.
    # Otherwise use max local/empirical screenshot size.
    #
    # See screenshot_analyzer.py for more info.
    screenshots_analysis_theoretical_fs: bool = False
    #
    # Number of screenshots to take for preprocessing
    #
    # Note: Pick a higher number than you want to upload
    screenshots_n_preprocess: int = 15
    #
    # Number of images to remove based on their file size
    # (both on lower and higher bound; symetrically)
    #
    # Note: Set to 0 to disable. However, I recommend keeping this value to 3.
    screenshots_n_outlier_prunes: int = 3
    #
    # Number of screenshot to upload
    #
    screenshots_n_upload: int = 3
    #
    # ffmpeg Scene filter
    #
    # See https://jdhao.github.io/2021/12/25/ffmpeg-extract-key-frame-video/#extract-scene-changing-frames
    # Note: setting this variable to None means the filter won't be applied
    # Note: currently unused
    screenshots_ffmpeg_scene_filter: float = 0.4
    #
    # Delete screenshots after they're not needed anymore
    #
    screenshots_delete_after_use: bool = True
    #
    # Save imgbox.com submissions to a JSON file
    #
    # Note: Must be a valid *file* path.
    # e.g. /path/to/imgbox_history.json
    screenshots_imgbox_history: Optional[str] = None

    @staticmethod
    def binary_choice(description: str) -> bool:
        status = None
        while status is None:
            prompt = input(description).lower()
            if prompt in ["y", "yes"]:
                status = True
            elif prompt in ["n", "no"]:
                status = False

        return status

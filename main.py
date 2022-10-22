import argparse
from pathlib import Path

from glue import Glue
from config import Config

if __name__ == "__main__":
    print(f"cwd: {Path.cwd()}")

    parser = argparse.ArgumentParser(prog="prepare-torrent")
    parser.add_argument(
        "--sanitize-file-name",
        action=argparse.BooleanOptionalAction,
        help='Sanititize file names which contain spaces or ".-."',
        dest="sanitize_file_name",
    )
    parser.add_argument(
        "--sanitize-file-name-prompt",
        action=argparse.BooleanOptionalAction,
        help="Toggles the prompt dialog if --sanitize-file-name is enabled",
        dest="sanitize_file_name_prompt",
    )
    parser.add_argument(
        "--announce-url",
        type=str,
        help="Tracker announce URL",
        metavar="https://torrent.tracker/announce?apikey=12345",
    )
    parser.add_argument(
        "--torrent-save-dir",
        type=str,
        help="Directory where to save the generated .torrent file",
        metavar="/path/to/save/dir/",
    )
    parser.add_argument(
        "--torrent-hash-threads",
        type=int,
        metavar="N",
        help="Number of threads per CPU core to use when hashing .torrent files",
    )
    parser.add_argument(
        "--ss-analyze",
        action=argparse.BooleanOptionalAction,
        help="Analyzes screenshots according to file size, image quality and sharpness metrics",
        dest="ss_analyze",
    )
    parser.add_argument(
        "--ss-no-spoilers",
        action=argparse.BooleanOptionalAction,
        help="Toggles the prompt dialog if --sanitize-file-name is enabled",
        dest="ss_no_spoilers",
    )
    parser.add_argument(
        "--ss-n-preprocess",
        type=int,
        metavar="N",
        help="Number of screenshots for ffmpeg to take to be used for (pre)processing",
    )
    parser.add_argument(
        "--ss-n-outlier-prunes",
        type=int,
        metavar="N",
        help="Maximum number of outlier screenshots to prune from the upper and lower bounds (symetrically)",
    )
    parser.add_argument(
        "--ss-n-upload",
        type=int,
        metavar="N",
        help="Number of screenshots to upload (after analyzing them and selecting the best)",
    )
    parser.add_argument(
        "--ss-delete-after-use",
        action=argparse.BooleanOptionalAction,
        help="Delete screenshots from the .screens folder when the analysis is finished",
        dest="ss_delete_after_use",
    )
    parser.add_argument(
        "input",
        help="The file or directory which to prepare for torrent creation",
    )

    args = parser.parse_args()
    if args.sanitize_file_name is not None:
        Config.sanitize_filename = args.sanitize_file_name

    if args.sanitize_file_name_prompt is not None:
        Config.sanitize_filename_prompt = args.sanitize_file_name_prompt

    if args.announce_url is not None:
        Config.tracker_announce_url = args.announce_url

    if args.torrent_save_dir is not None:
        Config.torrent_output_dir = args.torrent_save_dir

    if args.torrent_hash_threads is not None:
        Config.torrent_hash_cpu_threads = args.torrent_hash_threads

    if args.ss_analyze is not None:
        Config.screenshots_analyze = args.ss_analyze

    if args.ss_no_spoilers is not None:
        Config.screenshots_no_spoilers = args.ss_no_spoilers

    if args.ss_n_preprocess is not None:
        Config.screenshots_n_preprocess = args.ss_n_preprocess

    if args.ss_n_outlier_prunes is not None:
        Config.screenshots_n_outlier_prunes = args.ss_n_outlier_prunes

    if args.ss_n_upload is not None:
        Config.screenshots_n_upload = args.ss_n_upload

    if args.ss_delete_after_use is not None:
        Config.screenshots_delete_after_use = args.ss_delete_after_use

    glue = Glue(path=args.input)
    glue.generate_screenshots()
    glue.create_torrent()
    glue.create_description()

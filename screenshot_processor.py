import math
import statistics
from pathlib import Path
from dataclasses import dataclass
from multiprocessing import cpu_count, Pool

from config import Config


SQRT2 = math.sqrt(2.0)
TEN_MB = 10 * 1024 * 1024


@dataclass
class ScreenshotMetadata:
    path: Path
    file_size: int
    max_file_size: int


@dataclass
class ImageScore:
    screenshot: ScreenshotMetadata
    fs_score: float
    quality_score: float
    sharpness_score: float

    def total_score(self) -> float:
        return self.fs_score + self.quality_score + self.sharpness_score

    def __str__(self) -> str:
        return f"{self.fs_score:.02f}% FS, {self.quality_score:.02f}% quality, {self.sharpness_score:.02f}% sharpness"


def analyze_screenshot(screenshot: ScreenshotMetadata) -> ImageScore:
    # See https://stackoverflow.com/questions/57565234/pil-not-always-using-3-channels-for-png
    # NOTE: PIL.Image.open is a lazy evaluation. This line is needed to force to load content.
    import brisque
    from PIL import Image
    from sharpness import DOM

    image = Image.open(screenshot.path).convert("RGB")
    image.load()

    # If image is wider than 1280px resize it to
    # (w=1280px, h=<calculated based on aspect ratio>)
    if image.size[0] > 1280:
        new_height = int(float(image.size[1]) * float(1280 / float(image.size[0])))
        image = image.resize((1280, new_height), Image.Resampling.LANCZOS)

    # 25%  file size       0 < fs < max_file_size
    if Config.screenshots_analysis_theoretical_fs is True:
        fs_score = 25.0 * (screenshot.file_size / (10.0 * 1024.0 * 1024.0))
    else:
        fs_score = 25.0 * (screenshot.file_size / screenshot.max_file_size)

    # The perfect brisque metric is 0, hence we need to
    # inverse this for meaningful scoring.
    # 55%  brisque metric  0 < min(100, score) < 100
    brisque_metric = 100.0 - min(100.0, max(0.0, brisque.score(image)))
    quality_score = 55.0 * (brisque_metric / 100.0)

    # 20%  sharpness       0 < score < sqrt(2)
    sharpness_score = 20.0 * (DOM().get_sharpness(str(screenshot.path)) / SQRT2)

    return ImageScore(
        screenshot=screenshot,
        fs_score=fs_score,
        quality_score=quality_score,
        sharpness_score=sharpness_score
    )


class ScreenshotProcessor:
    def __init__(self, screenshots_dir: Path):
        self.max_file_size = 0
        self.screenshots: list[ScreenshotMetadata] = []

        if screenshots_dir.is_file():
            self._input_dir = screenshots_dir.parent
        else:
            self._input_dir = screenshots_dir

    def _preprocess(self) -> None:
        pre_images: list[tuple[Path, int]] = []
        pre_image_sizes: list[int] = []
        for p in self._input_dir.glob("pre_*.png"):
            sz = p.stat().st_size
            if sz >= TEN_MB:
                print(f' --> image "{p.name}" is larger than 10MB. skipping...')
                continue

            if sz > self.max_file_size:
                self.max_file_size = sz

            pre_images.append((p, sz))
            pre_image_sizes.append(sz)

        if not pre_images:
            raise ValueError("no screenshots found for processing")

        print(f"pre-processing {len(pre_images)} screenshots")

        img_mean = statistics.mean(pre_image_sizes)
        cut_off = statistics.stdev(pre_image_sizes) * 1.25

        lower, upper = img_mean - cut_off, img_mean + cut_off

        n_lower_removals, n_upper_removals = 0, 0
        n_outlier_prunes = Config.screenshots_n_outlier_prunes

        # Sort according to size, so we remove top-n/top-m outliers first
        pre_images = sorted(pre_images, key=lambda x: -x[1])
        for p, sz in pre_images:
            if sz < lower and n_lower_removals < n_outlier_prunes:
                n_lower_removals += 1
            elif sz > upper and n_upper_removals < n_outlier_prunes:
                n_upper_removals += 1
            else:
                self.screenshots.append(
                    ScreenshotMetadata(
                        path=p, file_size=sz, max_file_size=self.max_file_size
                    )
                )

        if n_lower_removals > 0:
            suffix = "s" if n_lower_removals > 1 else ""
            print(f" --> removed {n_lower_removals} lower bound outlier{suffix}")

        if n_upper_removals > 0:
            suffix = "s" if n_upper_removals > 1 else ""
            print(f" --> removed {n_upper_removals} upper bound outlier{suffix}")

    def process(self) -> None:
        self._preprocess()

        top_k = Config.screenshots_n_upload
        if not Config.screenshots_analyze:
            self.screenshots = sorted(self.screenshots, key=lambda x: -x.file_size)[:top_k]

            print(f"top-{top_k} screenshot results (to be uploaded):")
            for i, screenshot in enumerate(self.screenshots):
                print(f"{' ':2}#{i + 1:02}: {screenshot.path.name}")

            return

        # Leave a bit of processing power for the rest of the system as well
        n_cpu_count = max(2, int(cpu_count() * 0.85))
        print(f" --> parallelizing visual metric scoring to {n_cpu_count} processes")

        pool = Pool(n_cpu_count)
        scores = pool.map(analyze_screenshot, self.screenshots)

        print(f" --> finished analyzing data")
        print(f"top-{top_k} screenshot results (to be uploaded):")

        self.screenshots = []

        # Sort in DESC ordering
        scores = sorted(scores, key=lambda x: -x.total_score())
        for i, score in enumerate(scores[:top_k]):
            print(f"{' ':2}#{i + 1:02}: {score.screenshot.path.name}: {score.total_score():.02f} points")
            print(f"{' ':7}{score}")

            self.screenshots.append(score.screenshot)

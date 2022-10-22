# Introduction
prepare-torrent is a tool for creating media torrent files, generating their MediaInfo metadata, and taking best-effort screenshots.

_Please note that prepare-torrent is **experimental** beta software, subject to breaking changes._

What differentiates prepare-torrent from other tools is its reliance on pre-processing and analysis of screenshots to pick the best ones. It does so by utilizing a custom image scoring algorithm.

## How screenshot analysis works
The algorithm consists of three components:
1. The BRISQUE image quality assesment algorithm (from the paper ["No-Reference Image Quality Assessment in the Spatial Domain"](https://ieeexplore.ieee.org/document/6272356/))
2. A sharpness estimation algorithm (from the paper ["Sharpness Estimation for Document and Scene Images"](https://ieeexplore.ieee.org/document/6460868))
3. Image file size (stemming from the premise that larger files contain more data which compression didn't trivially eliminate)


How the screenshot process works for a single file:
0. A `.screens` directory is created in the folder where the torrent data is located (required because of `ffmpeg`)
1. Video duration is determined by MediaInfo
   - If `Config.screenshots_no_spoilers` is configured to `True`, then the duration is cut in half and only the first part is considered
2. The considered video duration is divided into `Config.screenshots_n_preprocess` parts (intervals), i.e. the number of screenshots to be taken.
3. The screenshots are then taken at the intervals generated in step 2. using the command: `ffmpeg -y -loglevel level+error -ss $TIMESTAMP -i $INPUT_FILE -frames:v 1 -q:v 10 -c:v png $TEMP_OUTPUT_FILE.png`
where `$TIMESTAMP`, `$INPUT_FILE` and `$TEMP_OUTPUT_FILE` are variables.
4. The taken images' file sizes are collected and their mean and standard deviations are computed.
5. The files are sorted by file size in *descending* order.
6. If any of the file sizes deviates more or less than `SD * 1.25`, then they are taken out of consideration as long as the number of taken-out-consideration screenshots is smaller than `Config.screenshots_n_outlier_prunes`.
7. Then, the image scoring process is parallelized into `number of CPU cores * 0.85` processes (expressed as a whole non-decimal number).
   1. A score of the image's file size is calculated using the formula:
      - If `Config.screenshots_analysis_theoretical_fs` is set to `True`: `25 * (file_size_in_bytes / 10_megabytes_in_bytes)`
      - If `Config.screenshots_analysis_theoretical_fs` is set to `False`: `25 * (file_size_in_bytes / maximal_file_size_from_screens_dir)`
   2. (For computational purposes) The image is resized down to 1280px in case it's larger than 1280px (while preserving aspect ratio)
   3. The BRISQUE score is computed on the image using the formula `55 * ((100 - min(100, max(0, brisque(image)))) / 100)` (Note: The perfect BRISQUE score is 0)
   4. The sharpness score is computed using the formula `20 * (sharpness(full_image) / sqrt(2))` (Note: The maximal value of the sharpness metric is sqrt(2))
8. The final score is computed by adding the 3 component scores together. The maximum score is 100 (unless `Config.screenshots_analysis_theoretical_fs` is set to `True`). **In short, the BRISQUE score contributes 55%, the sharpness score 20% and the file size 25% to the final score.**
9. After the final score has been computed, then we pick the top-`K` results to upload. (`K` here being `Config.screenshots_n_upload`)
10. After the process has finished (regardless of success/error), the images from the `.screens` folder are wiped and the directory is deleted.

This process is virtually the same for multiple files except:
   - Three files are sampled for screenshots instead of one (the first, the "middle file" and the last file; in no particular order!)
   - The screenshot intervals are computed in rolling order (the timestamp of the next screenshot _always_ progresses, even between files)

Considering such an analysis might be computationally expensive on low-power CPUs, the analysis can be disabled by setting `Config.screenshots_analyze` to `False`.

## Installation
1. `wget https://github.com/stacksmash76/prepare-torrent/archive/refs/heads/master.zip && unzip master.zip && rm master.zip`
2. `cd prepare-torrent-master`
3. If you wish to have the analysis feature, you will have to install around 100MB of Python packages using `pip install -r requirements.txt`
   - Otherwise, you can go by with only doing `pip install pyimgbox==1.0.5 pymediainfo==5.1.0 torf==4.0.4`, which take less than a megabyte of space. In that case, you will have to set `Config.screenshots_analyze` to `False`.
4. Configure your default options in `prepare-torrent/config.py` (if you want to override them on a per-case basis, you can do so via the command line)

### Server
- In my home directory, I have a directory called `_created_torrents` which is used to keep .torrent files
- In my `config.py` file, I have `torrent_output_dir` set to `/home/user/_created_torrents`, so torrents are automatically put there
- In my .bashrc file (located at `/home/user/.bashrc`), I have:
```alias prepare-torrent="/usr/bin/python3 /home/user/prepare-torrent/main.py"```

### Client
- In a directory on my local computer, I have a synchronization script to pull torrent files from my server:
```bash
#!/bin/bash
# The following command pull .torrent files from /home/user/_created_torrents/
# which is located on my server, to the current working local directory
rsync -avP --include="*.torrent" SERVER:/home/user/_created_torrents/ .
# The following command removes all .torrent files from /home/user/_created_torrents/
# after the files were synchronized between server and client.
ssh SERVER rm -rf /home/user/_created_torrents/*.torrent
```

# Workflow
When I want to create a torrent file, I simply do `prepare-torrent /path/to/directory_or_file/` on the server, followed by the pull script from my local computer.
You can override default options from `config.py` using the command line. See `prepare-torrent -h` for more info.

If you wish to upload images behind a VPN, then I suggest running prepare-torrent through a VPN tunnel, such as [vopono](https://github.com/jamesmcm/vopono)

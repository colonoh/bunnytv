import subprocess
from pathlib import Path


FILENAME = "BigBuckBunny_640x360.m4v"


def convert():
    Path("output").mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "ffmpeg",
            "-re",
            "-i",
            "BigBuckBunny_640x360.m4v",
            "-codec",
            "copy",
            "-hls_time",
            "2",
            "-hls_flags",
            "delete_segments",
            "-hls_list_size",
            "5",
            "output/stream.m3u8",
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    print(result.stderr)

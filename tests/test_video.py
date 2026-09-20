"""The video workflow uses local media for its reproducible checks."""

import json
import shutil
import subprocess

import pytest

from sports_stats_analyzer.video import VideoError, extract_frames, youtube_video_id


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=78rS30sszUM", "78rS30sszUM"),
        ("https://youtu.be/78rS30sszUM?t=22", "78rS30sszUM"),
        ("https://m.youtube.com/shorts/78rS30sszUM", "78rS30sszUM"),
    ],
)
def test_youtube_video_id(url, expected):
    assert youtube_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=78rS30sszUM",
        "https://youtube.com.evil.example/watch?v=78rS30sszUM",
        "https://www.youtube.com/playlist?list=78rS30sszUM",
        "https://www.youtube.com/watch?v=wrong",
    ],
)
def test_youtube_video_id_rejects_invalid_source(url):
    with pytest.raises(VideoError):
        youtube_video_id(url)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg ausente")
def test_extract_frames_uses_local_video_and_writes_manifest(tmp_path):
    video = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=64x64:r=2:d=2",
            "-c:v",
            "mpeg4",
            str(video),
        ],
        check=True,
    )
    output = tmp_path / "frames"
    result = extract_frames(video, output, every_s=1)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result["frame_count"] == 2
    assert [frame["time_s"] for frame in manifest["frames"]] == [0, 1]
    assert all((output / f"t{second:06d}s.jpg").is_file() for second in (0, 1))

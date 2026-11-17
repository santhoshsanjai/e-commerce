"""Product videos: MP4 or WebM, checked by their first bytes rather than the file name.

Videos are stored as uploaded and served from the CDN, which answers the browser's range
requests, so a video starts playing before it has fully downloaded.
"""

from dataclasses import dataclass

from fastapi import status

from app.core.exceptions import AppError

# MP4 "brands" (bytes 8-12 of the ftyp box) that browsers play. QuickTime (.mov, brand "qt  ")
# is left out: Chrome and Firefox often can't play it.
MP4_BRANDS = {
    b"isom",
    b"iso2",
    b"iso4",
    b"iso5",
    b"iso6",
    b"mp41",
    b"mp42",
    b"avc1",
    b"M4V ",
    b"M4VP",
    b"dash",
    b"mmp4",
    b"3gp4",
    b"3gp5",
}


@dataclass(frozen=True)
class VideoKind:
    mime_type: str
    extension: str


def check_video(head: bytes) -> VideoKind:
    """Identify a video from its first 64 bytes, or refuse it."""
    if len(head) >= 12 and head[4:8] == b"ftyp":
        if head[8:12] in MP4_BRANDS:
            return VideoKind("video/mp4", "mp4")
        if head[8:12] == b"qt  ":
            raise AppError(
                "unsupported_video",
                "This is a QuickTime (.mov) video. Export or convert it to MP4 and upload again.",
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
    if head[:4] == b"\x1a\x45\xdf\xa3" and b"webm" in head[:64]:
        return VideoKind("video/webm", "webm")
    raise AppError(
        "unsupported_video",
        "Upload the video as an MP4 or WebM file.",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    )

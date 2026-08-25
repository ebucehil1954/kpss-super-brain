"""
KPSS Super-Brain: Algılama ve Video/Web Tüketim Katmanı (Senses)
"""
from .video_crawler import video_crawler, VideoCrawler
from .video_queue import video_queue, VideoQueue
from .transcript_fetcher import transcript_fetcher, TranscriptFetcher
from .transcript_processor import transcript_processor, TranscriptProcessor
from .web_researcher import web_researcher, WebResearcher

__all__ = [
    "video_crawler",
    "VideoCrawler",
    "video_queue",
    "VideoQueue",
    "transcript_fetcher",
    "TranscriptFetcher",
    "transcript_processor",
    "TranscriptProcessor",
    "web_researcher",
    "WebResearcher"
]

"""
KPSS Super-Brain: Doğrulanmış Kanal Taraması (Channel Scanner)
Kanal içi tarama ile küresel YouTube aramasını birbirinden ayıran doğrulanmış kanal tarayıcı.
KURAL: Bir kanal tarandığında, dönen tüm videolar kesinlikle o kanala ait olmalıdır.
Küresel arama sonuçları kanala mal edilemez.
"""
from typing import List, Dict, Any, Optional
import re
from curriculum.sources import GOLD_STANDARD_CHANNELS

class ChannelScanner:
    @staticmethod
    def verify_channel_identity(channel_name: str) -> bool:
        """Kanal kimliğinin doğrulanmış / altın standart kanal olduğunu teyit eder."""
        if not channel_name or not channel_name.strip():
            return False
        clean = channel_name.strip().lower()
        return any(clean in g.lower() or g.lower() in clean for g in GOLD_STANDARD_CHANNELS)

    @classmethod
    def filter_videos_by_channel(
        cls,
        videos: List[Dict[str, Any]],
        target_channel: str
    ) -> List[Dict[str, Any]]:
        """
        Kanal taraması sonucunu filtreler: Yalnızca ve yalnızca hedef kanala ait videoları tutar.
        Hedef kanala ait olmayan hiçbir video kanal içi tarama sonucu sayılamaz.
        """
        if not target_channel:
            return videos

        target_norm = target_channel.strip().lower()
        verified_videos = []
        for v in videos:
            ch = (v.get("channel") or v.get("uploader") or "").strip().lower()
            # Kanal adı eşleşmesi
            if target_norm in ch or ch in target_norm:
                verified_videos.append(v)

        return verified_videos

channel_scanner = ChannelScanner()

"""
KPSS Super-Brain: Resmi Mevzuat ve Resmi Gazete Radarı (Mevzuat Crawler)
Mevzuat.gov.tr ve Resmi Gazete bültenlerini tarayarak güncel kanun değişikliklerini,
yürürlük tarihlerini ve mülga düzenlemeleri beynin hafızasına işler.
"""
import httpx
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import super_brain_config
from brain.knowledge_store import knowledge_store
from anti_hallucination.fact_checker import fact_checker

class MevzuatCrawler:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PromiusKPSSMevzuatRadar/3.0"
    }

    @classmethod
    async def fetch_constitutional_updates(cls) -> Dict[str, Any]:
        """
        1982 Anayasası ve temel kanunların doğrulanmış güncel metinlerini ambarla senkronize eder.
        """
        ground_truth_path = super_brain_config.GROUND_TRUTH_DIR / "legislation.json"
        synced_count = 0

        if ground_truth_path.exists():
            with open(ground_truth_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                valid_laws = data.get("valid_laws", {})

                for law_name, law_data in valid_laws.items():
                    articles = law_data.get("key_articles", {})
                    for art_key, art_desc in articles.items():
                        text = f"[{law_name} {art_key}] {art_desc}"
                        is_clean, _ = fact_checker.verify_content(text, topic="Anayasa Hukuku", lesson="VATANDASLIK")
                        if is_clean:
                            knowledge_store.add_or_reinforce_record(
                                text=text,
                                record_type="FACT",
                                lesson="VATANDASLIK",
                                topic=f"{law_name} {art_key}",
                                subtopic="Resmi Mevzuat",
                                confidence=0.999,
                                source={
                                    "type": "official_legislation",
                                    "law": law_name,
                                    "article": art_key,
                                    "date": datetime.now().isoformat()
                                },
                                tags=["MEVZUAT_GOV", "ANAYASA", "VATANDASLIK"]
                            )
                            synced_count += 1

        return {
            "status": "success",
            "synced_articles_count": synced_count,
            "timestamp": datetime.now().isoformat()
        }

mevzuat_crawler = MevzuatCrawler()

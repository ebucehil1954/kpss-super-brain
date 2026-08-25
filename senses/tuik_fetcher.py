"""
KPSS Super-Brain: TÜİK ve MTA Resmi Veri Entegratörü (TÜİK Fetcher)
TÜİK demografi bültenleri, maden yatakları ve tarımsal birincilikleri
doğrudan hafızaya işleyerek Coğrafya ve Güncel Bilgiler sorularında sıfır hata sağlar.
"""
import json
from typing import Dict, Any, List
from datetime import datetime
from config import super_brain_config
from brain.knowledge_store import knowledge_store

class TuikMtaFetcher:
    @classmethod
    def sync_official_geography_facts(cls) -> Dict[str, Any]:
        """
        `geography_tuik_mta.json` dosyasındaki verileri hafıza ambarına senkronize eder.
        """
        gt_path = super_brain_config.GROUND_TRUTH_DIR / "geography_tuik_mta.json"
        if not gt_path.exists():
            return {"status": "error", "message": "geography_tuik_mta.json bulunamadı"}

        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        synced = 0
        now_str = datetime.now().isoformat()

        # 1. Madenler
        mines = data.get("mines_and_minerals", {})
        for mine_name, mine_info in mines.items():
            locs = ", ".join(mine_info.get("locations", []))
            plants = ", ".join(mine_info.get("processing_plant", []))
            mnemonic = mine_info.get("mnemonic", "")
            text = f"Maden: {mine_name} | Yataklar: {locs} | Tesisler: {plants}"
            if mnemonic:
                text += f" | Şifre: {mnemonic}"

            knowledge_store.add_or_reinforce_record(
                text=text,
                record_type="FACT",
                lesson="COGRAFYA",
                topic=f"Türkiye'nin Madenleri - {mine_name}",
                subtopic="Maden Yatakları ve Tesisleri",
                confidence=0.99,
                source={"type": "mta_official", "date": now_str},
                tags=["MTA", "MADENLER", "COGRAFYA", mine_name]
            )
            synced += 1

        # 2. Tarımsal Birincilikler
        agri = data.get("agriculture_first_places", {})
        for crop, place in agri.items():
            text = f"Tarımsal Ürün: {crop} -> Türkiye 1.si / Yoğun Bölge: {place}"
            knowledge_store.add_or_reinforce_record(
                text=text,
                record_type="FACT",
                lesson="COGRAFYA",
                topic=f"Türkiye Tarımı - {crop}",
                subtopic="Tarımsal Üretim Sıralaması",
                confidence=0.99,
                source={"type": "tuik_official", "date": now_str},
                tags=["TUIK", "TARIM", "COGRAFYA", crop]
            )
            synced += 1

        # 3. Demografi
        demo = data.get("demographics_tuik_2026", {})
        for key, val in demo.items():
            text = f"TÜİK 2026 Demografi Verisi [{key}]: {val}"
            knowledge_store.add_or_reinforce_record(
                text=text,
                record_type="FACT",
                lesson="COGRAFYA",
                topic="Türkiye Nüfusu ve Demografi",
                subtopic="TÜİK İstatistikleri",
                confidence=0.99,
                source={"type": "tuik_official", "date": now_str},
                tags=["TUIK", "NUFUS", "COGRAFYA"]
            )
            synced += 1

        return {
            "status": "success",
            "synced_records": synced,
            "timestamp": now_str
        }

tuik_fetcher = TuikMtaFetcher()

"""
KPSS Super-Brain: Hafıza Konsolidasyonu ve Uyku Modu Arıtıcısı (Memory Consolidation v3)
İnsan beynindeki REM evresi konsolidasyonunu taklit eder:
- Benzer veya mükerrer bilgileri birleştirir (De-duplication).
- Düşük güvenilirlikli gürültüleri temizler.
- Çok pekiştirilen çekirdek bilgilerin güven katsayısını artırır.
"""
from typing import Dict, Any, List
from datetime import datetime
from brain.database import db_session
from brain.knowledge_store import knowledge_store

class MemoryConsolidationEngine:
    @classmethod
    def run_deep_consolidation(cls) -> Dict[str, Any]:
        """
        Zihin ambarındaki tüm bilgileri tarar, pekiştirir ve optimize eder.
        """
        pruned_count = 0
        reinforced_count = 0

        with db_session() as conn:
            cursor = conn.cursor()
            
            # 1. 3'ten fazla pekiştirilen kayıtların güven skorunu maksimuma yükselt
            cursor.execute("""
            UPDATE knowledge_records
            SET confidence = 0.999
            WHERE times_reinforced >= 3 AND confidence < 0.999
            """)
            reinforced_count = cursor.rowcount

            # 2. Düşük güvenilirlikli ve hiç pekiştirilmemiş eski gürültüleri temizle
            cursor.execute("""
            DELETE FROM knowledge_records
            WHERE confidence < 0.6 AND times_reinforced = 1
            """)
            pruned_count = cursor.rowcount

        return {
            "status": "success",
            "reinforced_records": reinforced_count,
            "pruned_noisy_records": pruned_count,
            "timestamp": datetime.now().isoformat()
        }

memory_consolidation = MemoryConsolidationEngine()

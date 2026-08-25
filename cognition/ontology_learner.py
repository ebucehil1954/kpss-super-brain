"""
KPSS Super-Brain: Otomatik Ontoloji ve Bilgi Grafiği Genişletici (Ontology Learner v3)
Öğrenilen her yeni ders videosundan veya metinden kavramları, hukuki ilişkileri,
ön koşulları ve kronolojik bağları çıkararak Knowledge Graph'i dinamik olarak büyütür.
"""
import re
import json
import httpx
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.knowledge_graph import kpss_knowledge_graph

class OntologyLearner:
    @classmethod
    async def extract_and_expand_graph(
        cls,
        text: str,
        lesson: str,
        topic: str
    ) -> Dict[str, Any]:
        """
        Metinden yeni düğüm (Node) ve kenar (Edge) ilişkilerini çıkarır ve Bilgi Grafiğine ekler.
        """
        prompt = f"""
Sen Bilgi Grafiği ve Ontoloji Mühendisisin.
Aşağıdaki KPSS metninden temel varlıkları (Entity/Düğüm) ve aralarındaki ilişkileri (Edge/Kenar) çıkar.

DERS: {lesson}
KONU: {topic}

METİN:
\"\"\"{text[:2000]}\"\"\"

ÇIKTI FORMATI (SADECE GEÇERLİ JSON):
{{
  "nodes": [
    {{
      "id": "BENZERSİZ_DÜĞÜM_KODU (Örn: TAR_ISLAHAT_FERMANI)",
      "label": "Görünür İsim",
      "type": "HISTORICAL_EVENT veya LAW_REGULATION veya GEOGRAPHY_TOPIC",
      "properties": {{"ozellik_adi": "deger"}}
    }}
  ],
  "edges": [
    {{
      "source": "KAYNAK_DÜĞÜM_ID",
      "target": "HEDEF_DÜĞÜM_ID",
      "relation": "TEMPORAL_PRECEDES veya PREREQUISITE_OF veya REGULATED_BY",
      "weight": 1.0
    }}
  ]
}}
"""
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(
                    f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": super_brain_config.MAIN_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1}
                    }
                )
                if res.status_code == 200:
                    data = json.loads(res.json().get("response", "{}"))
                    nodes = data.get("nodes", [])
                    edges = data.get("edges", [])
                    
                    # Grafiğe ekle
                    for n in nodes:
                        n["lesson"] = lesson
                    kpss_knowledge_graph.batch_add(nodes, edges)
                    return {"nodes_added": len(nodes), "edges_added": len(edges)}
        except Exception:
            pass

        return {"nodes_added": 0, "edges_added": 0}

ontology_learner = OntologyLearner()

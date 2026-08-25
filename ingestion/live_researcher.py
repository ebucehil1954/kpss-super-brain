"""
KPSS Super-Brain: Gerçek Canlı İnternet Araştırma Motoru (Real Live Autonomous Researcher)
Wikipedia OpenSearch & REST API + Google News RSS üzerinden tam otonom canlı araştırma.
"""
import httpx
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from typing import List, Dict, Any

class RealLiveResearcher:
    HEADERS = {
        "User-Agent": "PromiusKPSSBot/1.0 (https://promius.app; info@promius.com)"
    }

    @classmethod
    async def search_wikipedia(cls, query: str, limit: int = 2) -> List[Dict[str, str]]:
        """
        Türkçe Vikipedi OpenSearch API ile canlı arama yapar ve özetleri çeker.
        """
        results = []
        try:
            search_url = f"https://tr.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit={limit}&namespace=0&format=json"
            async with httpx.AsyncClient(timeout=10.0, headers=cls.HEADERS) as client:
                res = await client.get(search_url)
                if res.status_code == 200:
                    data = res.json()
                    titles = data[1] if len(data) > 1 else []
                    
                    for title in titles:
                        summary_url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                        sum_res = await client.get(summary_url)
                        if sum_res.status_code == 200:
                            sum_data = sum_res.json()
                            extract = sum_data.get("extract", "")
                            if extract:
                                results.append({
                                    "title": sum_data.get("title", title),
                                    "summary": extract,
                                    "url": sum_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                                    "source": "Türkçe Vikipedi (Resmi Madde)"
                                })
        except Exception as e:
            print(f"Vikipedi Arama Hatasi: {str(e)}")
            
        return results

    @classmethod
    async def search_google_news_rss(cls, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Google News RSS üzerinden konuyla ilgili en son Türkçe haber ve yayınları çeker.
        """
        results = []
        try:
            encoded_query = urllib.parse.quote(f"{query} KPSS")
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
            
            async with httpx.AsyncClient(timeout=10.0, headers=cls.HEADERS) as client:
                res = await client.get(rss_url)
                if res.status_code == 200:
                    root = ET.fromstring(res.text)
                    items = root.findall(".//item")[:limit]
                    for item in items:
                        title_el = item.find("title")
                        desc_el = item.find("description")
                        pubdate_el = item.find("pubDate")
                        
                        title = title_el.text if title_el is not None else ""
                        desc = BeautifulSoup(desc_el.text, "html.parser").get_text() if desc_el is not None else ""
                        
                        results.append({
                            "title": title,
                            "summary": desc,
                            "source": "Canli Haber / Yayin",
                            "date": pubdate_el.text if pubdate_el is not None else ""
                        })
        except Exception as e:
            print(f"Haber RSS Arama Hatasi: {str(e)}")
            
        return results

    @classmethod
    async def deep_research_topic(cls, topic: str) -> Dict[str, Any]:
        """
        Hem Vikipedi hem canlı haber akışlarını birleştirerek derin KPSS bağlamı oluşturur.
        """
        wiki_articles = await cls.search_wikipedia(topic, limit=2)
        news_articles = await cls.search_google_news_rss(topic, limit=3)
        
        combined_chunks = []
        for w in wiki_articles:
            combined_chunks.append(f"KAYNAK ({w['source']} - {w['title']}):\n{w['summary']}")
            
        for n in news_articles:
            combined_chunks.append(f"KAYNAK ({n['source']} - {n['title']}):\n{n['summary']}")
            
        raw_context = "\n\n".join(combined_chunks)
        
        return {
            "topic": topic,
            "wiki_count": len(wiki_articles),
            "news_count": len(news_articles),
            "wiki_articles": wiki_articles,
            "news_articles": news_articles,
            "raw_context": raw_context if raw_context else f"{topic} hakkında temel KPSS müfredat bilgisi."
        }

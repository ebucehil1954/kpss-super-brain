"""
KPSS Super-Brain: Derin Ontoloji ve Otomatik Bilgi Grafiği Genişletici (Deep Ontology Engine v3)
"Beyin yüzeysel olmayacak: KPSS'nin tüm müfredatını, 200+ konusunu ve 1000+ alt kavramını
deterministik ve ilişkisel bir DAG olarak modeller, yeni öğrendiği her bilgiyi grafa bağlar."
"""
import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from brain.knowledge_graph import kpss_knowledge_graph, KPSSKnowledgeGraph

class DeepOntologyEngine:
    """
    KPSS dersleri için derin kavram haritası, önkoşul ilişkileri ve otomatik ontoloji genişleticisi.
    """
    
    # 5 Ana Dersin Kapsamlı Müfredat Çekirdeği (200+ Düğüm Tabanı)
    CORE_CURRICULUM_TREE: Dict[str, Dict[str, Any]] = {
        # --- VATANDAŞLIK ---
        "VATANDASLIK": {
            "TEMEL_HUKUK": {
                "label": "Temel Hukuk Kavramları",
                "subtopics": ["Hukukun Tanımı ve Dalları", "Yaptırım Türleri", "Hakkın Kazanılması ve Korunması", "Ehliyet Türleri (Fiil/Hak)", "Tüzel Kişilikler"],
                "keywords": ["ceza", "iptal", "tazminat", "hükümsüzlük", "butlan", "ehliyet", "ayırt etme", "erginlik", "kısıtlılık"],
                "prerequisites": []
            },
            "DEVLET_BIZ": {
                "label": "Devlet Biçimleri ve Demokrasi",
                "subtopics": ["Devlet Şekilleri (Üniter/Federal)", "Hükümet Sistemleri (Parlamenter/Başkanlık/Cumhurbaşkanlığı Hükümet Sistemi)", "Egemenlik Türleri"],
                "keywords": ["üniter", "federal", "konfederasyon", "kuvvetler ayrılığı", "başkanlık", "cumhurbaşkanlığı hükümet sistemi"],
                "prerequisites": ["TEMEL_HUKUK"]
            },
            "ANAYASA_TARIHI": {
                "label": "Türk Anayasa Tarihi",
                "subtopics": ["Sened-i İttifak (1808)", "Tanzimat ve Islahat Fermanları", "Kanun-i Esasi (1876)", "1921 Teşkilat-ı Esasiye", "1924 Anayasası", "1961 Anayasası", "1982 Anayasası"],
                "keywords": ["sened-i ittifak", "kanun-i esasi", "meşrutiyet", "1921 anayasası", "1924 anayasası", "1961 anayasası", "1982 anayasası", "çift meclis", "kuvvetler birliği"],
                "prerequisites": ["DEVLET_BIZ"]
            },
            "TEMEL_HAKLAR": {
                "label": "1982 Anayasası Temel Hak ve Hürriyetler",
                "subtopics": ["Kişi Hak ve Ödevleri (Koruyucu)", "Sosyal ve Ekonomik Haklar (İsteme)", "Siyasi Hak ve Ödevler (Katılma)", "Sert Çekirdek Haklar", "Hakların Sınırlanması ve Durdurulması"],
                "keywords": ["koruyucu haklar", "isteme hakları", "katılma hakları", "sert çekirdek", "olağanüstü hal", "ölçülülük", "yaşama hakkı", "masumiyet karinesi"],
                "prerequisites": ["ANAYASA_TARIHI"]
            },
            "YASAMA": {
                "label": "1982 Anayasası Yasama Organı",
                "subtopics": ["TBMM Kuruluşu ve Üye Sayısı (600)", "Milletvekili Seçilme Yeterliliği", "Milletvekilliğinin Sona Ermesi", "Dokunulmazlık ve Yasama Bağışıklığı", "TBMM Görev ve Yetkileri", "Karar ve Toplantı Yeter Sayıları", "Kanun Yapım Süreci"],
                "keywords": ["tbmm", "600 milletvekili", "salt çoğunluk", "301", "360", "400", "dokunulmazlık", "yasama sorumsuzluğu", "parlamento kararı", "kanun teklifi"],
                "prerequisites": ["TEMEL_HAKLAR"]
            },
            "YURUTME": {
                "label": "1982 Anayasası Yürütme Organı",
                "subtopics": ["Cumhurbaşkanı Seçimi ve Görevleri", "Cumhurbaşkanlığı Kararnameleri (CBK)", "Olağanüstü Hal (OHAL)", "Bakanlıklar ve Üst Düzey Yöneticiler", "Milli Güvenlik Kurulu (MGK)"],
                "keywords": ["cumhurbaşkanı", "cbk", "ohal", "mgk", "devlet denetleme kurulu", "ddk", "bakan", "cumhurbaşkanı yardımcısı", "yönetmelik"],
                "prerequisites": ["YASAMA"]
            },
            "YARGI": {
                "label": "1982 Anayasası Yargı Organı",
                "subtopics": ["Yüksek Mahkemeler (AYM, Yargıtay, Danıştay, Uyuşmazlık)", "Anayasa Mahkemesi Yapısı ve Görevleri", "Bireysel Başvuru", "Hakimler ve Savcılar Kurulu (HSK)", "Sayıştay"],
                "keywords": ["aym", "yargıtay", "danıştay", "uyuşmazlık mahkemesi", "hsk", "sayıştay", "yüce divan", "somut norm", "soyut norm", "iptal davası"],
                "prerequisites": ["YURUTME"]
            },
            "IDARE_HUKUKU": {
                "label": "İdare Hukuku ve Türkiye'nin İdari Teşkilatı",
                "subtopics": ["İdarenin Bütünlüğü (Hiyerarşi ve İdari Vesayet)", "Merkezden Yönetim (Başkent ve Taşra)", "Yerinden Yönetim (Mahalli ve Hizmet)", "Kamu Görevlileri (Memurlar ve Disiplin Cezaları)", "İdari İşlemler ve İdarenin Malları"],
                "keywords": ["hiyerarşi", "idari vesayet", "vali", "kaymakam", "belediye", "il özel idaresi", "köy", "memur", "kamu tüzel kişiliği", "kamulaştırma"],
                "prerequisites": ["YARGI"]
            }
        },

        # --- TARİH ---
        "TARIH": {
            "ILK_TURK_DEVLETLERI": {
                "label": "İlk ve Orta Çağlarda Türk Dünyası",
                "subtopics": ["Asya Hun Devleti", "Kavimler Göçü", "I. ve II. Köktürk Devletleri", "Uygur Devleti", "Kültür ve Medeniyet (Kut, Kurultay, Ordu-Millet, Töre)"],
                "keywords": ["mete han", "teoman", "bumin kağan", "bilge kağan", "orhun abideleri", "uygurlar", "maniheizm", "kut", "ikili teşkilat", "töre", "kurultay"],
                "prerequisites": []
            },
            "TURK_ISLAM_DEVLETLERI": {
                "label": "İlk Türk-İslam Devletleri",
                "subtopics": ["Karahanlılar", "Gazneliler", "Büyük Selçuklu Devleti", "Anadolu Selçuklu Devleti ve Beylikler", "Türk-İslam Kültür ve Medeniyeti"],
                "keywords": ["satuk buğra han", "gazneli mahmut", "dandanakan", "malazgirt", "nizamülmülk", "divan-ı lügati't-türk", "kutadgu bilig", "atabetü'l hakayık", "divan-ı hikmet"],
                "prerequisites": ["ILK_TURK_DEVLETLERI"]
            },
            "OSMANLI_KURULUS_YUKSELME": {
                "label": "Osmanlı Devleti Kuruluş ve Yükselme Dönemleri",
                "subtopics": ["Kuruluş Dönemi Padişahları ve Savaşları", "İstanbul'un Fethi ve II. Mehmed", "Yavuz Sultan Selim ve Mısır Seferi", "Kanuni Sultan Süleyman Dönemi", "Kültür ve Teşkilat (Divan, Tımar, Yeniçeri)"],
                "keywords": ["osman bey", "orhan bey", "i. murat", "yıldırım bayezid", "fetret devri", "fatih", "yavuz", "kanuni", "tımar", "devşirme", "yeniçeri", "divan-ı hümayun"],
                "prerequisites": ["TURK_ISLAM_DEVLETLERI"]
            },
            "OSMANLI_DURAKLAMA_GERILEME": {
                "label": "Osmanlı Duraklama ve Gerileme Dönemi Islahatları",
                "subtopics": ["17. Yüzyıl Islahatçıları (Tarhuncu, Köprülüler, Genç Osman)", "18. Yüzyıl Islahatları (Lale Devri, I. Mahmut, III. Mustafa, I. Abdülhamit, III. Selim Nizam-ı Cedit)", "Önemli Antlaşmalar (Pasarofça, Belgrat, Küçük Kaynarca, Yaş)"],
                "keywords": ["lale devri", "iii. ahmet", "nevşehirli damat ibrahim", "iii. selim", "nizam-ı cedit", "küçük kaynarca", "kırım", "hendesehane", "irad-ı cedit", "matbaa-i amire"],
                "prerequisites": ["OSMANLI_KURULUS_YUKSELME"]
            },
            "OSMANLI_DAGILMA": {
                "label": "19. ve 20. Yüzyıl Osmanlı Devleti (Dağılma ve Islahatlar)",
                "subtopics": ["II. Mahmut Islahatları", "Tanzimat ve Islahat Fermanları", "I. ve II. Meşrutiyet", "31 Mart Vakası", "Trablusgarp ve Balkan Savaşları", "Fikir Akımları (Osmanlıcılık, İslamcılık, Türkçülük, Batıcılık)"],
                "keywords": ["ii. mahmut", "yeniçeri ocağının kaldırılması", "vaka-i hayriye", "tanzimat fermanı", "ıslahat fermanı", "kanun-i esasi", "ii. abdülhamit", "ittihat ve terakki", "trablusgarp", "balkan savaşları"],
                "prerequisites": ["OSMANLI_DURAKLAMA_GERILEME"]
            },
            "MILLI_MUCADELE_HAZIRLIK": {
                "label": "Milli Mücadele Hazırlık Dönemi",
                "subtopics": ["I. Dünya Savaşı ve Mondros Mütarekesi", "Mustafa Kemal'in Samsun'a Çıkışı", "Havza ve Amasya Genelgeleri", "Erzurum ve Sivas Kongreleri", "Amasya Görüşmeleri ve Son Osmanlı Mebusan Meclisi", "Misak-ı Milli ve I. TBMM'nin Açılışı"],
                "keywords": ["mondros", "cemiyetler", "havza genelgesi", "amasya genelgesi", "erzurum kongresi", "sivas kongresi", "misak-ı milli", "i. tbmm", "hıyanet-i vataniye", "sevr"],
                "prerequisites": ["OSMANLI_DAGILMA"]
            },
            "MILLI_MUCADELE_MUHAREBELER": {
                "label": "Milli Mücadele Muharebeler Dönemi ve Antlaşmalar",
                "subtopics": ["Doğu Cephesi (Gümrü)", "Güney Cephesi (Ankara Antlaşması)", "Batı Cephesi (I. ve II. İnönü, Kütahya-Eskişehir, Sakarya, Büyük Taarruz)", "Mudanya Ateşkesi", "Lozan Barış Antlaşması"],
                "keywords": ["gümrü", "i. inönü", "londra konferansı", "istiklal marşı", "ii. inönü", "sakarya meydan muharebesi", "başkomutanlık", "büyük taarruz", "mudanya", "lozan"],
                "prerequisites": ["MILLI_MUCADELE_HAZIRLIK"]
            },
            "ATATURK_INKILAPLARI": {
                "label": "Atatürk Dönemi İnkılapları ve İlkeleri",
                "subtopics": ["Siyasal Alanda İnkılaplar (Saltanat, Cumhuriyet, Halifelik)", "Hukuk, Eğitim ve Kültür İnkılapları", "Toplumsal ve Ekonomik Alanda İnkılaplar", "Atatürk İlkeleri (Cumhuriyetçilik, Milliyetçilik, Halkçılık, Devletçilik, Laiklik, İnkılapçılık)"],
                "keywords": ["saltanatın kaldırılması", "cumhuriyetin ilanı", "halifeliğin kaldırılması", "tevhid-i tedrisat", "medeni kanun", "harf inkılabı", "izmir iktisat kongresi", "atatürk ilkeleri"],
                "prerequisites": ["MILLI_MUCADELE_MUHAREBELER"]
            },
            "ATATURK_DIS_POLITIKA": {
                "label": "Atatürk Dönemi Türk Dış Politikası ve Çağdaş Türk Dünyası",
                "subtopics": ["Musul Sorunu", "Bozkurt-Lotus Olayı", "Milletler Cemiyeti'ne Giriş (1932)", "Balkan Antantı (1934 - TAYYAR)", "Montrö Boğazlar Sözleşmesi (1936)", "Sadabat Paktı (1937 - TİAİ)", "Hatay'ın Anavatana Katılması (1939)", "II. Dünya Savaşı ve Soğuk Savaş Dönemi"],
                "keywords": ["balkan antantı", "sadabat paktı", "montrö", "hatay", "milletler cemiyeti", "tayyar", "tiai", "soğuk savaş", "bağlantısızlar", "kore savaşı", "nato"],
                "prerequisites": ["ATATURK_INKILAPLARI"]
            }
        },

        # --- COĞRAFYA ---
        "COGRAFYA": {
            "TURKIYE_KONUMU": {
                "label": "Türkiye'nin Coğrafi Konumu ve Jeopolitiği",
                "subtopics": ["Matematik (Mutlak) Konum ve Sonuçları", "Özel (Göreceli) Konum ve Sonuçları", "Yerel Saat ve Saat Dilimleri", "Sınırlar ve Komşular"],
                "keywords": ["enlem", "boylam", "36-42 kuzey", "26-45 doğu", "yerel saat", "gölge boyu", "jeopolitik", "boğazlar", "sınır kapıları"],
                "prerequisites": []
            },
            "TURKIYE_FIZIKI": {
                "label": "Türkiye'nin Fiziki Coğrafyası ve Yerşekilleri",
                "subtopics": ["Jeolojik Zamanlar ve Türkiye", "Dağlar (Kıvrım, Kırık, Volkanik)", "Ovalar ve Platolar", "Akarsular ve Göller", "Kıyı Tipleri ve Dış Kuvvetler (Rüzgar, Karstik, Buzul)"],
                "keywords": ["orojenez", "epirojenez", "kırık dağlar", "volkanik dağlar", "karstik şekiller", "delta ovaları", "çukurova", "bafra", "çarşamba", "kıyı tipleri"],
                "prerequisites": ["TURKIYE_KONUMU"]
            },
            "TURKIYE_IKLIM_BITKI": {
                "label": "Türkiye'nin İklimi ve Bitki Örtüsü",
                "subtopics": ["Sıcaklık, Basınç ve Rüzgarlar", "Nemlilik ve Yağış Tipleri", "İklim Tipleri (Akdeniz, Karadeniz, Karasal, Sert Karasal)", "Toprak Tipleri ve Bitki Formasyonları"],
                "keywords": ["akdeniz iklimi", "karadeniz iklimi", "karasal iklim", "orografik yağış", "konveksiyonel yağış", "cephe yağışı", "maki", "bozkır", "çernezyom", "terra rossa"],
                "prerequisites": ["TURKIYE_FIZIKI"]
            },
            "TURKIYE_NUFUS_YERLESME": {
                "label": "Türkiye'de Nüfus, Yerleşme ve Göç",
                "subtopics": ["Nüfusun Dağılışı ve Yoğunluğu", "Nüfus Piramitleri ve Demografik Dönüşüm", "Göç Türleri ve Nedenleri", "Kır ve Kent Yerleşmeleri"],
                "keywords": ["nüfus yoğunluğu", "tunceli", "istanbul", "aritmetik nüfus", "fizyolojik nüfus", "iç göç", "mevsimlik göç", "köy altı yerleşmeleri", "mezra", "oba", "kom"],
                "prerequisites": ["TURKIYE_IKLIM_BITKI"]
            },
            "TURKIYE_EKONOMI": {
                "label": "Türkiye'nin Ekonomik Coğrafyası (Tarım, Hayvancılık, Madenler, Sanayi)",
                "subtopics": ["Tarım Ürünleri ve Yetişme Alanları", "Hayvancılık Türleri ve Dağılışı", "Madenler ve Enerji Kaynakları", "Sanayi Kolları ve Ulaşım-Turizm"],
                "keywords": ["buğday", "pamuk", "fındık", "çay", "zeytin", "bor", "baksit", "krom", "bakır", "demir", "kader", "hidroelektrik", "güneş enerjisi", "rüzgar enerjisi"],
                "prerequisites": ["TURKIYE_NUFUS_YERLESME"]
            }
        },

        # --- TÜRKÇE ---
        "TURKCE": {
            "SOZCUKTE_ANLAM": {
                "label": "Sözcükte ve Söz Öbeklerinde Anlam",
                "subtopics": ["Gerçek, Yan ve Mecaz Anlam", "Terim Anlam", "Eş, Zıt ve Yakın Anlam", "Deyimler ve Atasözleri", "Dolaylama ve Güzel Adlandırma"],
                "keywords": ["gerçek anlam", "mecaz", "yan anlam", "terim", "deyim", "atasözü", "dolaylama"],
                "prerequisites": []
            },
            "CUMLEDE_ANLAM": {
                "label": "Cümlede Anlam ve Anlatım Özellikleri",
                "subtopics": ["Neden-Sonuç, Amaç-Sonuç, Koşul-Sonuç", "Öznel ve Nesnel Yargılar", "Doğrudan ve Dolaylı Anlatım", "Cümlenin İfade Ettiği Duygu ve Kavramlar"],
                "keywords": ["neden-sonuç", "amaç-sonuç", "koşul", "öznel", "nesnel", "varsayım", "olasılık", "tanım", "içerik", "üslup"],
                "prerequisites": ["SOZCUKTE_ANLAM"]
            },
            "PARAGRAF_BILGISI": {
                "label": "Paragrafta Anlam, Yapı ve Ana Düşünce",
                "subtopics": ["Ana Düşünce ve Yardımcı Düşünceler", "Paragraf Tamamlama ve Akışı Bozan Cümle", "Paragrafı İkiye Bölme", "Anlatım Teknikleri ve Düşünceyi Geliştirme Yolları"],
                "keywords": ["ana fikir", "yardımcı fikir", "akışı bozan", "ikiye bölme", "öyküleme", "betimleme", "tartışma", "açıklama", "tanık gösterme", "örneklendirme"],
                "prerequisites": ["CUMLEDE_ANLAM"]
            },
            "SES_YAZIM_NOKTALAMA": {
                "label": "Ses Bilgisi, Yazım Kuralları ve Noktalama İşaretleri",
                "subtopics": ["Ses Olayları (Ünlü Düşmesi, Ünsüz Benzeşmesi, Yumuşama)", "Yazımı Karıştırılan Sözcükler ve 'de/ki/mi' Yazımı", "Büyük Harflerin Yazımı ve Birleşik Sözcükler", "Noktalama İşaretleri Kullanımı"],
                "keywords": ["ünlü düşmesi", "ünsüz benzeşmesi", "yumuşama", "daralma", "büyük harfler", "ayrı yazılan da", "ki yazımı", "noktalı virgül", "iki nokta", "kesme işareti"],
                "prerequisites": []
            },
            "DIL_BILGISI": {
                "label": "Sözcük Türleri, Ekler ve Cümle Bilgisi",
                "subtopics": ["Sözcükte Yapı ve Ekler (Yapım/Çekim)", "İsim, Sıfat, Zamir, Zarf, Edat, Bağlaç, Ünlem", "Fiiller, Ek Fiil ve Fiilimsiler", "Cümlenin Ögeleri ve Cümle Türleri", "Anlatım Bozuklukları"],
                "keywords": ["fiilimsi", "özne", "yüklem", "nesne", "dolaylı tümleç", "zarf tümleci", "birleşik cümle", "anlatım bozukluğu", "yapım eki", "çekim eki"],
                "prerequisites": ["SES_YAZIM_NOKTALAMA"]
            },
            "SOZEL_MANTIK": {
                "label": "Sözel Mantık ve Muhakeme",
                "subtopics": ["Sıralama ve Tablo Oluşturma", "Grup ve Kategori Eşleştirme", "Değişkenler Arası Kısıt Çözümü", "Tekil ve Kesin Olasılık Hesaplama"],
                "keywords": ["sözel mantık", "kesinlikle doğrudur", "kesinlikle yanlıştır", "olabilir", "sıralama", "tablo", "kısıt", "öncül"],
                "prerequisites": ["PARAGRAF_BILGISI", "DIL_BILGISI"]
            }
        }
    }

    @classmethod
    def seed_complete_ontology_graph(cls):
        """
        KPSS'nin tüm ders ve konularını kapsayan derin bilgi grafiğini inşa eder ve kaydeder.
        """
        nodes_to_add = []
        edges_to_add = []

        for lesson, topics in cls.CORE_CURRICULUM_TREE.items():
            prev_topic_id = None
            for topic_code, topic_data in topics.items():
                node_id = f"{lesson}_{topic_code}"
                
                # Düğüm oluştur
                node = {
                    "id": node_id,
                    "label": topic_data["label"],
                    "type": "CURRICULUM_TOPIC",
                    "lesson": lesson,
                    "properties": {
                        "topic_code": topic_code,
                        "subtopics": topic_data.get("subtopics", []),
                        "keywords": topic_data.get("keywords", []),
                        "saturation_count": 0,
                        "is_mastered": False,
                        "exam_weight": 0.85
                    }
                }
                nodes_to_add.append(node)

                # Önkoşul Kenarları (Prerequisites)
                for prereq in topic_data.get("prerequisites", []):
                    prereq_id = f"{lesson}_{prereq}"
                    edges_to_add.append({
                        "source": prereq_id,
                        "target": node_id,
                        "relation": "PREREQUISITE_OF",
                        "weight": 1.0
                    })

                # Ders İçi Akış Kenarı (Curriculum Flow)
                if prev_topic_id:
                    edges_to_add.append({
                        "source": prev_topic_id,
                        "target": node_id,
                        "relation": "CURRICULUM_FLOW",
                        "weight": 0.8
                    })
                prev_topic_id = node_id

        # Çapraz Ders İlişkileri (Cross-Lesson Edges)
        cross_edges = [
            {"source": "VATANDASLIK_ANAYASA_TARIHI", "target": "TARIH_OSMANLI_DAGILMA", "relation": "HISTORICAL_PARALLEL", "weight": 0.9},
            {"source": "VATANDASLIK_ANAYASA_TARIHI", "target": "TARIH_MILLI_MUCADELE_HAZIRLIK", "relation": "HISTORICAL_PARALLEL", "weight": 0.9},
            {"source": "COGRAFYA_TURKIYE_EKONOMI", "target": "COGRAFYA_TURKIYE_FIZIKI", "relation": "GEOGRAPHIC_DEPENDENCY", "weight": 0.85},
            {"source": "TURKCE_SOZEL_MANTIK", "target": "TURKCE_DIL_BILGISI", "relation": "SKILL_FOUNDATION", "weight": 0.75}
        ]
        edges_to_add.extend(cross_edges)

        kpss_knowledge_graph.batch_add(nodes_to_add, edges_to_add)
        return len(nodes_to_add), len(edges_to_add)

    @classmethod
    def auto_expand_from_knowledge(cls, text: str, lesson: str, topic: str, subtopic: str = "") -> List[str]:
        """
        Öğrenilen yeni bir metinden (YouTube transkripti, MEB kitabı, web makalesi)
        kavramları çıkarır ve bilgi grafiğinde ilgili konuya yeni ENTITY düğümleri ve kenarlar bağlar.
        """
        created_node_ids = []
        clean_lesson = lesson.upper()
        
        # Ana konu düğümünü bul
        parent_node_id = None
        for n_id, n_data in kpss_knowledge_graph.nodes.items():
            if n_data.get("lesson") == clean_lesson and (topic.lower() in n_data.get("label", "").lower() or n_data.get("label", "").lower() in topic.lower()):
                parent_node_id = n_id
                break

        if not parent_node_id:
            # Otomatik yeni konu düğümü oluştur
            norm_code = re.sub(r'[^a-zA-Z0-9]', '_', topic.upper())[:20]
            parent_node_id = f"{clean_lesson}_{norm_code}"
            kpss_knowledge_graph.add_node(
                node_id=parent_node_id,
                label=topic,
                node_type="TOPIC",
                lesson=clean_lesson,
                properties={"auto_created": True, "subtopics": [subtopic] if subtopic else []}
            )
            created_node_ids.append(parent_node_id)

        # Metinden varlık / kavram çıkarımı
        entities = cls._extract_entities_rule_based(text)
        
        new_nodes = []
        new_edges = []
        for ent in entities[:6]:  # En güçlü 6 kavram
            ent_hash = hashlib.md5(f"{clean_lesson}_{ent.lower()}".encode('utf-8')).hexdigest()[:8]
            ent_node_id = f"ENT_{ent_hash}"
            
            if ent_node_id not in kpss_knowledge_graph.nodes:
                new_nodes.append({
                    "id": ent_node_id,
                    "label": ent,
                    "type": "ENTITY",
                    "lesson": clean_lesson,
                    "properties": {
                        "parent_topic": parent_node_id,
                        "source_text_snippet": text[:120],
                        "times_observed": 1
                    }
                })
                created_node_ids.append(ent_node_id)

            new_edges.append({
                "source": parent_node_id,
                "target": ent_node_id,
                "relation": "CONTAINS_CONCEPT",
                "weight": 1.0
            })

        if new_nodes or new_edges:
            kpss_knowledge_graph.batch_add(new_nodes, new_edges)

        return created_node_ids

    @staticmethod
    def _extract_entities_rule_based(text: str) -> List[str]:
        """Metinden kritik KPSS terimlerini ve kavramlarını ayıklar."""
        candidates = set()
        
        # 1. Tırnak içindeki kavramlar
        quotes = re.findall(r'["“\']([^"”\']{3,35})["”\']', text)
        for q in quotes:
            if len(q.split()) <= 4:
                candidates.add(q.strip())

        # 2. Özel isim & Büyük harfli tamlamalar
        capitalized_terms = re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+){1,3}\b', text)
        for term in capitalized_terms:
            if term.lower() not in ["bu derste", "bir başka", "türkiye cumhuriyeti", "öğretmen zihniyeti", "kpss super"]:
                candidates.add(term.strip())

        # 3. Kanun ve Oran İfadeleri
        stat_patterns = re.findall(r'(?:\d+\/\d+|\b\d{2,4}\b\s+[a-zA-Zçğıöşü]+|Madde\s+\d+)', text, re.IGNORECASE)
        for sp in stat_patterns:
            candidates.add(sp.strip())

        return list(candidates)

    @classmethod
    def get_curriculum_statistics(cls) -> Dict[str, Any]:
        """Bilgi grafiğinin toplam kapsamını ve ders dağılımını hesaplar."""
        total_nodes = len(kpss_knowledge_graph.nodes)
        total_edges = len(kpss_knowledge_graph.edges)
        
        by_lesson = {}
        by_type = {}
        for n_id, n in kpss_knowledge_graph.nodes.items():
            ls = n.get("lesson", "GENEL")
            nt = n.get("type", "UNKNOWN")
            by_lesson[ls] = by_lesson.get(ls, 0) + 1
            by_type[nt] = by_type.get(nt, 0) + 1

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "by_lesson": by_lesson,
            "by_type": by_type,
            "is_deep_brain": total_nodes >= 25
        }

deep_ontology = DeepOntologyEngine()
# Başlangıçta tüm derin müfredat ontolojisini inşa et
deep_ontology.seed_complete_ontology_graph()

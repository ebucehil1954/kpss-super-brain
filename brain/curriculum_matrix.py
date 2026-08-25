"""
KPSS Super-Brain: Resmi ÖSYM Müfredatı ve Konu Hakimiyet Matrisi (Curriculum Mastery Matrix)
"Basit yüzeysel öğrenme yetersizdir: Her resmi konu başlığı için en az 3-4 farklı öğretmenin ders videosu
tüketilip karşılaştırmalı sentezi yapılmadan konu uzmanlığı tamamlanmış sayılamaz."
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from brain.database import db_session

class CurriculumMatrixEngine:
    """
    Resmi ÖSYM KPSS Genel Kültür & Genel Yetenek Müfredat Kataloğu ve Konu Hakimiyet Takipçisi.
    """

    # 1. RESMİ ÖSYM KPSS MÜFREDAT KAPSAMI (Tam ve Eksiksiz Katalog)
    OFFICIAL_CURRICULUM: Dict[str, Dict[str, Dict[str, Any]]] = {
        # === GENEL KÜLTÜR: TARİH (27 SORU) ===
        "TARIH": {
            "ILK_TURK_DEVLETLERI": {
                "name": "İslamiyet Öncesi Türk Tarihi ve Kültür-Medeniyeti",
                "exam_question_weight": "1-2 Soru",
                "subtopics": ["Orta Asya Kültür Merkezleri", "İskitler (Sakalar)", "Asya Hun Devleti", "Kavimler Göçü", "I. ve II. Göktürk Devletleri", "Uygur Devleti", "Diğer Türk Boyları (Avarlar, Hazarlar, Peçenekler, Kıpçaklar, Kumanlar)", "Devlet Yönetimi (Kut, İkili Teşkilat, Kurultay)", "Ordu, Hukuk (Töre), Din ve İnanış, Yazı, Dil ve Edebiyat"],
                "target_videos": 4
            },
            "ILK_TURK_ISLAM_DEVLETLERI": {
                "name": "İlk Türk-İslam Devletleri ve Kültür-Medeniyeti",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Talas Savaşı ve Türklerin İslamlaşması", "Karahanlılar", "Gazneliler", "Büyük Selçuklu Devleti", "Mısır'da Kurulan Türk Devletleri (Tolunoğulları, İhşidiler, Eyyubiler, Memlükler)", "İlk Türk-İslam Edebi Eserleri (Kutadgu Bilig, Divanü Lugati't-Türk, Atabetü'l Hakayık, Divan-ı Hikmet)", "Devlet Teşkilatı, Hassa Ordusu, İkta Sistemi, Taşra ve Adalet Teşkilatı"],
                "target_videos": 4
            },
            "ANADOLU_SELCOKLU_BEYLIKLER": {
                "name": "Türkiye (Anadolu) Selçuklu Devleti ve Beylikler Dönemi",
                "exam_question_weight": "1 Soru",
                "subtopics": ["I. Dönem Anadolu Türk Beylikleri (Danişmentliler, Saltuklular, Mengücekliler, Artuklular, Çaka)", "Anadolu Selçuklu Siyasi Tarihi ve Haçlı Seferleri", "Kösedağ Savaşı ve Moğol İstilası", "II. Dönem Türk Beylikleri (Karesi, Germiyan, Candaroğulları, Aydınoğulları, Saruhanoğulları)", "Anadolu Selçuklu Ticaret Politikaları, Ahilik Teşkilatı ve Mimari Eserler"],
                "target_videos": 4
            },
            "OSMANLI_KURULUS_YUKSELME": {
                "name": "Osmanlı Devleti Kuruluş ve Yükselme Dönemleri",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["Kuruluş Dönemi Padişahları ve Gaza Politikası", "İskan ve İstimalet Politikaları", "Ankara Savaşı ve Fetret Devri", "İstanbul'un Fethi ve II. Mehmed (Fatih) Dönemi Kanunnameleri", "II. Bayezid Dönemi ve Cem Sultan Olayı", "I. Selim (Yavuz) ve Mısır Seferi (Hilafetin Geçişi)", "Kanuni Sultan Süleyman Dönemi ve Deniz Zaferleri"],
                "target_videos": 4
            },
            "OSMANLI_KULTUR_MEDENIYET": {
                "name": "Osmanlı Kültür ve Medeniyeti (En Kritik Alan)",
                "exam_question_weight": "3-4 Soru",
                "subtopics": ["Merkez Teşkilatı (Padişah, Şehzade Eğitimi, Divan-ı Hümayun ve Üyeleri)", "Taşra Teşkilatı (Eyalet, Sancak, Kaza, Köy, Salyaneli/Salyanesiz Eyaletler)", "Toprak Sistemi (Dirlik - Has, Zeamet, Tımar, Paşmaklık, Malikane, Vakıf)", "Ordu Teşkilatı (Kapıkulu Askerleri, Tımarlı Sipahiler, Eyalet Askerleri, Donanma)", "Hukuk Sistemi (Şer'i ve Örfi Hukuk, Kadılık)", "Maliye ve Vergi Türleri (Öşür, Haraç, Cizye, Ağnam, Çiftbozan, İltizam Sistemi)", "Eğitim, Bilim, Mimari, Hat, Minyatür ve Musiki"],
                "target_videos": 4
            },
            "OSMANLI_DURAKLAMA_GERILEME": {
                "name": "17. ve 18. Yüzyıl Osmanlı Devleti (Duraklama, Gerileme ve Islahatlar)",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["17. Yüzyıl İç İsyanları (Celali, Yeniçeri, Eyalet)", "17. Yüzyıl Islahatçıları (Tarhuncu Ahmed, Köprülüler, II. Osman, IV. Murat Koçi Bey Risalesi)", "18. Yüzyıl Lale Devri Islahatları ve III. Ahmet", "I. Mahmut, III. Mustafa, I. Abdülhamit Islahatları", "III. Selim Dönemi ve Nizam-ı Cedit Islahatları", "Önemli Antlaşmalar (Kasr-ı Şirin, Karlofça, Pasarofça, Belgrad, Küçük Kaynarca, Yaş, Ziştovi)"],
                "target_videos": 4
            },
            "OSMANLI_DAGILMA_19YY": {
                "name": "19. ve 20. Yüzyıl Osmanlı Devleti (Dağılma Dönemi Islahatları)",
                "exam_question_weight": "3 Soru",
                "subtopics": ["II. Mahmut Islahatları (Yeniçeri Ocağının Kaldırılması - Vaka-i Hayriye, Muhtarlık, Bakanlıklar, Takvim-i Vekayi)", "Tanzimat Fermanı (1839) ve Hukukun Üstünlüğü", "Islahat Fermanı (1856) ve Gayrimüslim Hakları", "I. Meşrutiyet (1876) ve Kanun-i Esasi", "II. Abdülhamit Dönemi (İstibdat, Eğitim, Hicaz Demiryolu)", "II. Meşrutiyet (1908), 31 Mart Vakası (1909) ve 1909 Anayasa Değişiklikleri", "Fikir Akımları (Osmanlıcılık, İslamcılık, Türkçülük, Batıcılık, Adem-i Merkeziyetçilik)"],
                "target_videos": 4
            },
            "TRABLUSGARP_BALKAN_1DUNYA": {
                "name": "Trablusgarp, Balkan ve I. Dünya Savaşı Dönemi",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Trablusgarp Savaşı (Mustafa Kemal'in İlk Askeri Başarısı, Uşi Antlaşması)", "I. ve II. Balkan Savaşları (Bükreş, İstanbul, Atina Antlaşmaları)", "I. Dünya Savaşı Nedenleri ve Osmanlı'nın Savaşa Girişi", "Taarruz Cepheleri (Kafkas, Kanal)", "Savunma Cepheleri (Çanakkale, Hicaz-Yemen, Irak-Kut'ül Amare, Suriye-Filistin)", "Yardım Cepheleri (Galiçya, Romanya, Makedonya)", "Mondros Ateşkes Antlaşması (7. ve 24. Maddeler) ve Gizli Antlaşmalar"],
                "target_videos": 4
            },
            "MILLI_MUCADELE_HAZIRLIK": {
                "name": "Milli Mücadeleye Hazırlık Dönemi (Genelgeler ve Kongreler)",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Cemiyetler (Milli Varlık Düşmanı ve Yararlı Cemiyetler)", "Mustafa Kemal'in Samsun'a Çıkışı (19 Mayıs 1919) ve Samsun Raporu", "Havza Genelgesi (İlk Protesto ve Miting Çağrısı)", "Amasya Genelgesi (Milli Mücadelenin Amaç, Gerekçe ve Yöntemi)", "Erzurum Kongresi (Milli Sınırlar, Temsil Heyeti)", "Sivas Kongresi (Cemiyetlerin Birleştirilmesi, İrade-i Milliye Gazetesi)", "Amasya Görüşmeleri ve Protokolleri", "Son Osmanlı Mebusan Meclisi ve Misak-ı Milli Kararları", "İstanbul'un İtilaf Devletlerince Resmen İşgali"],
                "target_videos": 4
            },
            "BIRINCI_TBMM_DONEMI": {
                "name": "I. TBMM Dönemi ve Ayaklanmalar (1920-1923)",
                "exam_question_weight": "2 Soru",
                "subtopics": ["I. TBMM'nin Açılışı, Yapısı, Özellikleri (Kurucu, İhtilalci, Güçler Birliği)", "I. TBMM Çıkardığı İlk Kanunlar (Ağnam Resmi, Hıyanet-i Vataniye, Firariler)", "TBMM'ye Karşı Çıkan İsyanlar ve Bastırılması (İstiklal Mahkemeleri)", "Sevr Barış Antlaşması (Hükümleri ve Geçersizliği)", "1921 Anayasası (Teşkilat-ı Esasiye)"],
                "target_videos": 4
            },
            "KURTULUS_SAVASI_MUHAREBELER": {
                "name": "Kurtuluş Savaşı Muharebeler Dönemi ve Diplomatik Antlaşmalar",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Doğu Cephesi (Kazım Karabekir ve Gümrü Antlaşması)", "Güney Cephesi (Kuvayı Milliye Kahramanlıkları, Ankara Antlaşması)", "Batı Cephesi: I. İnönü Savaşı (Sonuçları: MİLAD / TALİM - Moskova, İstiklal Marşı, Londra, Afganistan, Teşkilat-ı Esasiye)", "II. İnönü Savaşı ve İtalyanların Çekilmesi", "Kütahya-Eskişehir Muharebeleri ve Maarif Kongresi", "Tekalif-i Milliye Emirleri ve Başkomutanlık Kanunu", "Sakarya Meydan Muharebesi ve Sonuçları (Kars ve Ankara Antlaşmaları)", "Büyük Taarruz ve Başkomutanlık Meydan Muharebesi", "Mudanya Ateşkes Antlaşması", "Lozan Barış Antlaşması (Sınırlar, Boğazlar, Kapitülasyonlar, Borçlar, Patrikhane, Azınlıklar)"],
                "target_videos": 4
            },
            "ATATURK_INKILAPLARI_VE_ILKELERI": {
                "name": "Atatürk Dönemi İnkılapları ve Atatürk İlkeleri",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Siyasal Alanda İnkılaplar (Saltanatın Kaldırılması, Ankara'nın Başkent Oluşu, Cumhuriyetin İlanı, Halifeliğin Kaldırılması, Çok Partili Hayat Denemeleri - CHF, TCF, SCF, Şeyh Sait ve Menemen Olayları)", "Hukuk Alanında İnkılaplar (1924 Anayasası, Medeni Kanun, Ceza ve Ticaret Kanunları)", "Eğitim ve Kültür Alanında İnkılaplar (Tevhid-i Tedrisat, Medreselerin Kapatılması, Harf İnkılabı, Millet Mektepleri, Türk Tarih ve Dil Kurumları, Üniversite Reformu)", "Toplumsal ve Ekonomik Alanda İnkılaplar (Kılık-Kıyafet, Tekke ve Zaviyelerin Kapatılması, Soyadı Kanunu, İzmir İktisat Kongresi, Kabotaj Kanunu, Teşvik-i Sanayi, I. Beş Yıllık Sanayi Planı)", "6 Temel İlke (Cumhuriyetçilik, Milliyetçilik, Halkçılık, Devletçilik, Laiklik, İnkılapçılık)"],
                "target_videos": 4
            },
            "ATATURK_DIS_POLITIKA": {
                "name": "Atatürk Dönemi Türk Dış Politikası (1923-1938)",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Dış Politikanın Esasları (Yurtta Sulh Cihanda Sulh, Tam Bağımsızlık)", "1923-1930 Dönemi (Yabancı Okullar, Nüfus Mübadelesi, Musul Meselesi, Bozkurt-Lotus Olayı)", "1930-1938 Dönemi (Milletler Cemiyeti'ne Giriş 1932, Balkan Antantı 1934 - TAYYAR, Montrö Boğazlar Sözleşmesi 1936, Sadabat Paktı 1937 - TİAİ, Hatay'ın Bağımsızlığı ve Anavatana Katılması 1939)"],
                "target_videos": 4
            },
            "CAGDAS_TURK_DUNYA_TARIHI": {
                "name": "Çağdaş Türk ve Dünya Tarihi (20. ve 21. Yüzyıl)",
                "exam_question_weight": "3 Soru",
                "subtopics": ["İki Savaş Arası Dönem (1929 Dünya Ekonomik Buhranı - Kara Perşembe, Totaliter Rejimler)", "II. Dünya Savaşı (Mihver ve Müttefik Devletler, Türkiye'nin Savaş Diplomasisi, Kahire ve Adana Görüşmeleri, Yalta ve Potsdam Konferansları)", "Soğuk Savaş Dönemi (Truman Doktrini, Marshall Planı, NATO ve Varşova Paktı, Kore Savaşı ve Türkiye'nin NATO'ya Girişi, Bağlantısızlar Hareketi, Kıbrıs Meselesi ve EOKA)", "Yumuşama (Detant) Dönemi ve Çatışmalar (Küba Füze Krizi, Vietnam Savaşı, İslam İşbirliği Teşkilatı, ASALA Terörü, 1974 Kıbrıs Barış Harekatı)", "Küreselleşen Dünya (SSCB'nin Dağılması ve Türk Cumhuriyetleri - TİKA, TÜRKSOY, Körfez Savaşları, Bosna ve Kosova Savaşları, AB Süreci)"],
                "target_videos": 4
            }
        },

        # === GENEL KÜLTÜR: COĞRAFYA (18 SORU) ===
        "COGRAFYA": {
            "TURKIYE_KONUMU_JEOPOLITIK": {
                "name": "Türkiye'nin Coğrafi Konumu ve Jeopolitik Önemi",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Matematik (Mutlak) Konum ve Sonuçları (36°-42° Kuzey, 26°-45° Doğu, Güneş Işınları, Çizgisel Hız, Yerel Saat, Saat Dilimleri, Gölge Boyu)", "Özel (Göreceli) Konum ve Sonuçları (Üç Tarafı Denizlerle Çevrili Olma, Ortalama Yükselti, Kıtalararası Köprü)", "Türkiye'nin Kara ve Deniz Sınırları, Sınır Kapıları ve Komşuları", "Jeopolitik Güç Unsurları ve Küresel/Bölgesel Etkisi"],
                "target_videos": 4
            },
            "TURKIYE_FIZIKI_VE_YERSEKILLERI": {
                "name": "Türkiye'nin Fiziki Özellikleri, Jeolojik Yapısı ve Yer Şekilleri",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Jeolojik Zamanlar (I, II, III, IV. Zaman Olayları ve Türkiye'nin Genç Oluşumlu Yapısı)", "İç Kuvvetler: Orojenez (Kıvrım Dağları - Toroslar/Kuzey Anadolu, Kırık Dağları - Ege Horst/Graben Sistemi), Epirojenez (Türkiye'nin Toptan Yükselmesi), Volkanizma (Volkanik Dağlar - Ağrı, Süphan, Nemrut, Tendürek, Erciyes, Hasan Dağı, Kula Volkanları), Depremler (KAF, DAF, BAF Fay Hatları)", "Dış Kuvvetler: Akarsu Aşınım ve Birikim Şekilleri (Vadiler, Peri Bacaları, Kırgabayır, Delta Ovaları - Çukurova, Bafra, Çarşamba, Silifke, Dikili, Menemen, Selçuk, Balat)", "Karstik Şekiller (Lapya, Dolin, Uvala, Polye, Mağara, Travertenler, Obruklar)", "Buzul Şekilleri ve Rüzgar Şekilleri", "Kıyı Tipleri (Boyuna, Enine, Dalmaçya, Rias, Limanlı Kıyılar; Haliç ve Fiyort Yokluğu Sebepleri)", "Platolar (Lav, Karstik, Aşınım, Tabaka Düzlüğü Platoları)"],
                "target_videos": 4
            },
            "TURKIYE_SU_VARLIGI": {
                "name": "Türkiye'nin Su Varlığı (Akarsular, Göller, Yeraltı Suları)",
                "exam_question_weight": "1-2 Soru",
                "subtopics": ["Akarsuların Genel Özellikleri, Rejimleri, Havzaları (Açık/Kapalı Havza), Aşındırma Gücü ve Hidroelektrik Potansiyeli", "Doğal Göller: Tektonik (Tuz, İznik, Sapanca, Manyas, Beyşehir, Eğirdir), Karstik (Salda, Kestel, Elmalı), Volkanik (Nemrut, Meke Tuzlası, Gölcük), Buzul (Sirk) Gölleri", "Set Gölleri: Heyelan Set (Tortum, Sera, Abant, Yedigöller), Volkanik Set (Van, Çıldır, Erçek, Nazik, Balık), Alüvyal Set (Köyceğiz, Bafa, Eymir, Mogan), Kıyı Set / Lagün (Büyükçekmece, Küçükçekmece, Terkos/Durusu)", "Barajlar ve Yeraltı Suları (Artezyen, Karstik-Voklüz, Gayzer Yokluğu, Fay Kaynakları ve Jeotermal)"],
                "target_videos": 4
            },
            "TURKIYE_IKLIM_VE_BITKI": {
                "name": "Türkiye'nin İklimi, Sıcaklık, Basınç, Yağış ve Bitki Örtüsü",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Sıcaklığı Etkileyen Faktörler (Enlem, Yükselti, Karasallık-Denizellik, Bakı, Rüzgarlar)", "Basınç Merkezleri (İzlanda Dinamik Alçak, Sibirya Termik Yüksek, Azor Dinamik Yüksek, Basra Termik Alçak)", "Rüzgarlar (Kayıp Sakal: Karayel, Yıldız, Poyraz, Samyeli/Keşişleme, Kıble, Lodos, Föhn Rüzgarı, Meltemler)", "Nemlilik ve Yağış Tipleri (Konveksiyonel - İç Anadolu Kırkikindi, Orografik/Yamaç - Karadeniz/Toroslar, Cephe/Frontal - Akdeniz İklimi)", "İklim Tipleri: Akdeniz, Karadeniz, Karasal (Step), Sert Karasal (Erzurum-Kars)", "Toprak Tipleri: Zonal (Terra Rossa, Kahverengi Orman, Çernezyom, Bozkır), İntrazonal (Halomorfik, Hidromorfik, Kalsimorfik - Vertisol/Dönen Toprak, Rendzina), Azonal (Alüvyal, Kolüvyal, Litosol, Regosol)", "Bitki Formasyonları: Ağaç (Orman Dağılışı), Çalı (Maki, Garig, Psödomaki), Ot (Bozkır, Alpin Çayır), Endemik ve Relikt Bitkiler"],
                "target_videos": 4
            },
            "TURKIYE_NUFUS_VE_YERLESME": {
                "name": "Türkiye'de Nüfus, Yerleşme ve Göç Politikaları",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["Nüfus Sayımları Tarihçesi ve Nüfus Artış Hızı Grafikleri (TÜİK En Güncel Verileri)", "Nüfusun Yaş, Cinsiyet, Sektörel ve Eğitim Dağılımı (Nüfus Piramitleri Analizi)", "Nüfusun Alansal Dağılışı (Seyrek ve Yoğun Nüfuslu Yöreler ve Nedenleri: Yıldız Dağları, Menteşe, Teke-Taşeli, Hakkari, Tuz Gölü Çevresi)", "Türkiye'de Göçler: İç Göç (Nedenleri, Sonuçları, Mevsimlik Göç), Dış Göç (İşçi Göçü, Beyin Göçü, Sığınmacı/Mülteci Göçü)", "Yerleşme Tipleri: Kır ve Kent Yerleşmeleri, Köy Altı Yerleşmeleri (Sürekli: Çiftlik, Mahalle, Mezra, Divan; Geçici: Yayla, Kom, Ağıl, Oba, Dam, Dalyan)"],
                "target_videos": 4
            },
            "TURKIYE_TARIM_VE_HAYVANCILIK": {
                "name": "Türkiye'de Tarım ve Hayvancılık",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["Tarımı Etkileyen Faktörler (Sulama, Gübreleme, Tohum Islahı, Makineleşme, Destekleme Alımları)", "Tarım Ürünlerinin Coğrafi Dağılışı ve Üretim Lideri İller (TÜİK Güncel): Tahıllar (Buğday, Arpa, Mısır, Pirinç), Baklagiller (Mercimek, Nohut, Fasulye), Sanayi Bitkileri (Pamuk, Tütün, Şeker Pancarı, Çay, Haşhaş, Keten-Kenevir, Ayçiçeği, Zeytin), Meyveler (Fındık, Üzüm, İncir, Turunçgiller, Elma, Kayısı, Antep Fıstığı, Muz)", "Hayvancılık Türleri: Küçükbaş (Koyun, Kıl Keçisi, Tiftik Keçisi), Büyükbaş (Sığır, Manda), Kümes Hayvancılığı, Arıcılık (Muğla, Ordu, Kars, Adana), İpek Böcekçiliği (Diyarbakır, Bursa), Balıkçılık ve Kültür Balıkçılığı"],
                "target_videos": 4
            },
            "TURKIYE_MADENLER_VE_ENERJI": {
                "name": "Türkiye'nin Madenleri ve Enerji Kaynakları",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Metalik ve Metal Dışı Madenler Çıkarım ve İşleme Tesisleri (Demir - Divriği/Hekimhan -> Karabük/Ereğli/İskenderun, Bakır - Murgul/Küre/Ergani -> Samsun, Boksit/Alüminyum - Seydişehir, Bor - Balıkesir/Kütahya/Eskişehir/Bursa, Krom - Fethiye/Guleman -> Antalya/Elazığ, Kurşun-Çinko, Mermer, Zımpara Taşı, Fosfat - Mazıdağı, Asbest, Lületaşı, Oltutaşı, Feldispat)", "Tükenebilir Enerji Kaynakları: Taşkömürü (Zonguldak/Çatalağzı), Linyit (Afşin-Elbistan, Soma, Yatağan, Seyitömer), Petrol (Batman-Raman, Rafineriler: Batman, Aliağa, Kırıkkale, İpraş), Doğalgaz (Hamitabat, Ovaakça, Ambarlı, Sakarya Gaz Sahası), Nükleer Enerji (Akkuyu, Sinop)", "Yenilenebilir Enerji Kaynakları: Hidroelektrik (GAP Barajları, Keban, Karakaya, Atatürk, Deriner, Ilısu), Güneş Enerjisi (Güneydoğu ve Akdeniz Potansiyeli, Karapınar GES), Rüzgar Enerjisi (İzmir, Balıkesir, Çanakkale, Manisa), Jeotermal Enerji (Denizli-Sarayköy, Aydın-Germencik), Biyokütle"],
                "target_videos": 4
            },
            "TURKIYE_SANAYI_ULASIM_TURIZM_PROJELER": {
                "name": "Sanayi, Ulaşım, Ticaret, Turizm ve Bölgesel Kalkınma Projeleri",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Sanayi Kollarının Kuruluş Yeri Faktörleri (Hammaddeye Yakınlık, Enerjiye Yakınlık, Pazara Yakınlık, Ulaşım, İşgücü)", "Ulaşım Sistemleri: Karayolu, Demiryolu (Liman Bağlantıları ve Tren Ulaşımı Olmayan İller: Çanakkale, Muğla, Antalya, Sinop, Trabzon, Rize, Artvin), Denizyolu (En Büyük İhracat ve İthalat Limanları), Havayolu", "Dış Ticaret (İhracat ve İthalatta İlk Sıradaki Ülkeler ve Ürün Grupları)", "Turizm Değerleri (UNESCO Dünya Miras Listesi Varlıkları: Göbeklitepe, Efes, Hierapolis, Kapadokya, Çatalhöyük, Divriği, Safranbolu, Nemrut, Afrodisias, Arslantepe, Gordion vb.)", "Bölgesel Kalkınma Projeleri: GAP (Güneydoğu Anadolu), DOKAP (Doğu Karadeniz), DAP (Doğu Anadolu), ZBK (Zonguldak-Bartın-Karabük), KOP (Konya Ovası Projesi - Mavi Tünel), YHGP (Yeşilırmak Havzası)"],
                "target_videos": 4
            }
        },

        # === GENEL KÜLTÜR: VATANDAŞLIK & GÜNCEL (15 SORU) ===
        "VATANDASLIK": {
            "TEMEL_HUKUK_KAVRAMLARI": {
                "name": "Temel Hukuk Kavramları ve Hukukun Dalları",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["Toplumsal Düzen Kuralları (Din, Ahlak, Görgü, Hukuk)", "Hukuk Kurallarının Özellikleri ve Yaptırım (Müeyyide) Türleri: Ceza, Cebri İcra, Tazminat (Maddi/Manevi), İptal, Hükümsüzlük (Yokluk, Butlan - Mutlak/Nisbi, Askıda Hükümsüzlük)", "Hukukun Dalları: Kamu Hukuku (Anayasa, İdare, Ceza, Vergi, Yargılama, İcra-İflas, Devletler Umumi), Özel Hukuk (Medeni, Borçlar, Ticaret, Devletler Hususi), Karma Hukuk (İş, Çevre, Bankacılık, Hava)", "Hak Kavramı: Hakkın Kazanılması (İyiniyet - Medeni m. 3), Hakkın Kullanılması ve Sınırları (Dürüstlük Kuralı / Hakkın Kötüye Kullanılması Yasağı - Medeni m. 2), Hakkın Korunması (Meşru Müdafaa, Zaruret Hali / Iztırar, Kuvvet Kullanma)", "Kişiler Hukuku: Gerçek Kişilik (Başlangıcı - Tam ve Sağ Doğum, Sona Ermesi - Ölüm, Ölüm Karinesi, Birlikte Ölüm, Gaiplik Süreleri), Ehliyetler (Hak Ehliyeti, Fiil Ehliyeti ve Şartları: Ayırt Etme Gücü, Erginlik, Kısıtlı Olmama), Ehliyet Türleri (Tam Ehliyetliler, Sınırlı Ehliyetliler, Sınırlı Ehliyetsizler, Tam Ehliyetsizler)", "Hısımlık Türleri (Kan Hısımlığı - Altsoy/Üstsoy, Yansoy; Kayın Hısımlığı; Evlat Edinme; Derece Hesaplama)", "Tüzel Kişiler (Kişi Toplulukları: Dernek, Şirket; Mal Toplulukları: Vakıf, Üniversite)"],
                "target_videos": 4
            },
            "DEVLET_BICIMLERI_HUKUMET_SISTEMLERI": {
                "name": "Devlet Biçimleri, Demokrasi ve Hükümet Sistemleri",
                "exam_question_weight": "1 Soru",
                "subtopics": ["Devletin Unsurları (İnsan / Millet, Ülke / Toprak, Egemenlik)", "Yapılarına Göre Devletler: Basit (Üniter Devlet), Birleşik (Federasyon / Federal Devlet, Konfederasyon)", "Egemenliğin Kaynağına Göre: Monarşi (Mutlak/Meşruti), Oligarşi, Teokrasi, Cumhuriyet", "Kuvvetler İlişkisine Göre Hükümet Sistemleri: Kuvvetler Birliği (Meclis Hükümeti Sistemi, Mutlak Monarşi, Diktatörlük), Kuvvetler Ayrılığı (Parlamenter Sistem, Başkanlık Sistemi, Yarı-Başkanlık Sistemi, Türkiye'deki Cumhurbaşkanlığı Hükümet Sistemi Özellikleri)", "Demokrasi Türleri (Doğrudan, Yarı Doğrudan - Referandum, Halk Girişimi, Halk Vetosu, Temsilcinin Azli, Temsili Demokrasi)", "Seçim İlkeleri (Genel Oy, Eşit Oy, Gizli Oy, Açık Sayım-Döküm, Serbest Oy, Tek Dereceli Seçim)"],
                "target_videos": 4
            },
            "TURK_ANAYASA_TARIHI": {
                "name": "Türk Anayasa Tarihi (1808 Sened-i İttifak'tan 1982'ye)",
                "exam_question_weight": "1 Soru",
                "subtopics": ["Sened-i İttifak (1808) ve Padişah Yetkilerinin İlk Kez Sınırlandırılması", "Tanzimat Fermanı (1839) ve Islahat Fermanı (1856)", "Kanun-i Esasi (1876 - İlk Türk Anayasası, Çift Meclis: Heyet-i Mebusan / Heyet-i Ayan, 1909 Değişiklikleri)", "1921 Anayasası (Teşkilat-ı Esasiye - Yumuşak ve Çerçeve Anayasa, Meclis Hükümeti Sistemi, 1923 Değişiklikleri)", "1924 Anayasası (Katı ve Kazuistik, Karma Hükümet Sistemi, Çoğunlukçu Demokrasi, 1928, 1934, 1937 Laiklik Değişiklikleri)", "1961 Anayasası (Geniş Haklar, Çift Meclis: Millet Meclisi ve Cumhuriyet Senatosu, Anayasa Mahkemesi, MGK ve DPT'nin Kurulması, Çoğulcu Demokrasi, 1971-1973 Değişiklikleri)", "1982 Anayasası'nın Hazırlanışı, Temel Nitelikleri ve 2017 Anayasa Değişiklikleri Özeti"],
                "target_videos": 4
            },
            "1982_TEMEL_ILKELER_VE_HAKLAR": {
                "name": "1982 Anayasası Temel İlkeleri ve Temel Hak ve Hürriyetler",
                "exam_question_weight": "1-2 Soru",
                "subtopics": ["Anayasanın Değiştirilemez Maddeleri (Madde 1-2-3 ve 4. Madde Güvencesi)", "Cumhuriyetin Nitelikleri (Demokratik, Laik, Sosyal, Hukuk Devleti, İnsan Haklarına Saygılı, Atatürk Milliyetçiliğine Bağlı)", "Temel Hak ve Hürriyetlerin Sınırlanması Şartları (Madde 13: Kanunla, Anayasanın Sözüne ve Ruhuna Uygun, Demokratik Toplum Düzeninin Gereklerine Uygun, Laik Cumhuriyetin Gereklerine Uygun, Ölçülülük İlkesine Uygun, Hakkın Özüne Dokunulamaz)", "Temel Hak ve Hürriyetlerin Durdurulması (Madde 15: Savaş, Seferberlik veya OHAL Durumlarında, Milletlerarası Hukuktan Doğan Yükümlülükler İhlal Edilmemek Kaydıyla)", "Sert Çekirdek Haklar (Dokunulamaz Alan: Yaşama Hakkı / Maddi-Manevi Varlık, Masumiyet Karinesi, Suç ve Cezaların Geçmişe Yürümezliği, Din, Vicdan, Düşünce ve Kanaatlerin Açıklanmaya Zorlanamaması)", "Jellinek Hak Tasnifi: 1. Kişisel Hak ve Ödevler (Koruyucu / Negatif Statü: Yaşam, Konut Dokunulmazlığı, Mülkiyet vb.), 2. Sosyal ve Ekonomik Haklar (İsteme / Pozitif Statü: Eğitim, Çalışma, Sağlık, Konut, Sendika, Grev vb.), 3. Siyasi Haklar ve Ödevler (Katılma / Aktif Statü: Vatandaşlık, Seçme-Seçilme, Siyasi Parti Kurma/Üye Olma, Vergi, Vatan Hizmeti, Dilekçe/Bilgi Edinme/Kamu Denetçisine Başvuru)"],
                "target_videos": 4
            },
            "1982_YASAMA_ORGANI": {
                "name": "1982 Anayasası Yasama Organı (TBMM ve Kanun Yapım Süreci)",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["TBMM Kuruluşu ve Milletvekili Sayısı (600)", "Milletvekili Seçilme Yeterliliği Şartları (18 Yaş, En Az İlkokul Mezuniyeti, Askerlikle İlişiği Olmama, Kısıtlı Olmama, Taksirli Suçlar Hariç 1 Yıldan Fazla Hapis Yatmama vb.)", "Milletvekili Seçimleri (5 Yılda Bir, Seçimlerin Yenilenmesi Kararı: TBMM 3/5 - 360 veya Cumhurbaşkanı; Seçimlerin Geriye Bırakılması: Yalnızca SAVAŞ Sebebiyle TBMM Kararıyla 1 Yıl)", "Milletvekilliğinin Sona Ermesi Halleri (Meclis Kararı Gerekenler: İstifa - Basit Çoğunluk, Devamsızlık - Üye Tamsayısı Salt Çoğunluğu 301, Milletvekilliğiyle Bağdaşmayan Görevde Israr; Kendiliğinden Düşenler: Ölüm, Gaiplik, Bakan/CB Yardımcısı Seçilme, Kesin Hüküm Giyme)", "Yasama Bağışıklıkları: Yasama Sorumsuzluğu (Mutlak, Ömür Boyu, Kaldırılamaz), Yasama Dokunulmazlığı (Nisbi, Kaldırılabilir, TBMM Kararına Karşı 7 Gün İçinde AYM'ye Başvuru - AYM 15 Günde Karar Verir)", "TBMM Görev ve Yetkileri (Kanun Yapmak, Değiştirmek, Kaldırmak; Bütçe ve Kesinhesap Kanun Tekliflerini Görüşmek ve Kabul Etmek; Para Basılmasına ve Savaş İlanına Karar Vermek; TSK Kullanılmasına İzin Vermek; Genel ve Özel Af İlanı - 3/5 360 Çoğunluk; Milletlerarası Antlaşmaların Onaylanmasını Uygun Bulmak)", "Toplantı ve Karar Yeter Sayıları: Toplantı Yeter Sayısı: Üye Tamsayısının 1/3'ü (200); Karar Yeter Sayısı: Katılanların Salt Çoğunluğu (Hiçbir Şekilde Üye Tamsayısının 1/4'ünün 1 Fazlasından Az Olamaz: En Az 151)", "Nitelikli Çoğunluklar: 301 (Salt Çoğunluk), 360 (3/5 Çoğunluk), 400 (2/3 Çoğunluk)", "Kanun Yapım Süreci ve Cumhurbaşkanının İncelemesi (15 Gün İçinde Yayımlama veya Geri Gönderme / Veto; Bütçe Kanunu Geri Gönderilemez; Meclis Aynen Kabul Ederse 301 ile CB Yayımlamak Zorundadır)", "TBMM Bilgi Edinme ve Denetim Yolları (Yazılı Soru - 15 Günde Cevaplanır, Genel Görüşme, Meclis Araştırması, Meclis Soruşturması; GENSORU VE GÜVENOYU 2017'DE KALDIRILMIŞTIR)"],
                "target_videos": 4
            },
            "1982_YURUTME_ORGANI": {
                "name": "1982 Anayasası Yürütme Organı (Cumhurbaşkanlığı Teşkilatı ve OHAL)",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Yürütme Yetkisi ve Görevi (Cumhurbaşkanına Aittir)", "Cumhurbaşkanı Seçilme Şartları (40 Yaşını Doldurmuş, Yükseköğrenim Yapmış, Milletvekili Seçilme Yeterliliğine Sahip Türk Vatandaşı, Halk Tarafından 5 Yıllığına, En Fazla 2 Kez)", "Cumhurbaşkanı Aday Gösterme Şartları (Siyasi Parti Grupları, Son Genel Seçimde Tek Başına veya Birlikte En Az %5 Oy Alan Partiler, En Az 100.000 Seçmen)", "Cumhurbaşkanı Seçim Usulü (İki Turlu Sistem: 1. Turda Geçerli Oyların Salt Çoğunluğu; 2. Turda En Çok Oy Alan İki Aday, En Çok Oyu Alan Seçilir)", "Cumhurbaşkanının Görev ve Yetkileri (Yürütmenin Başı, Devlet Denetleme Kurulu Üye ve Başkanını Atamak, Üst Düzey Kamu Yöneticilerini Atamak/Görevden Almak, CB Yardımcıları ve Bakanları Atamak/Görevden Almak, Yönetmelik Çıkarmak, Rektörleri Atamak, AYM Üyelerinin 12'sini, Danıştay Üyelerinin 1/4'ünü, HSK Üyelerinin 4'ünü, Yargıtay Başsavcısını Seçmek)", "Cumhurbaşkanlığı Kararnameleri (CBK: Olağan CBK Yalnızca Sosyal ve Ekonomik Haklarda Çıkarılabilir, Temel Haklar ve Siyasi Haklar Düzenlenemez; Kanunda Açıkça Düzenlenen Konularda CBK Çıkarılamaz; Kanun ile CBK Çelişirse Kanun Hükümleri Uygulanır; TBMM Aynı Konuda Kanun Çıkarırsa CBK Hükümsüz Kalır; Yargısal Denetim AYM Tarafından Yapılır)", "Cumhurbaşkanının Cezai Sorumluluğu (Yüce Divan Süreci: Teklif 301, Soruşturma Açılması 360, Yüce Divana Sevk 400)", "Cumhurbaşkanına Vekalet (Makamın Boşalması veya Geçici Ayrılma Durumunda En Yaşlı CB Yardımcısı Değil, Görevlendirilen / Belirlenen CB Yardımcısı Vekalet Eder)", "Milli Güvenlik Kurulu (MGK: 2 Ayda Bir CB Başkanlığında Toplanır, Kararları Tavsiye Niteliğindedir; Üyeleri: CB Yardımcıları, Adalet, İçişleri, Dışişleri, Milli Savunma Bakanları, Genelkurmay Başkanı, Kara, Deniz, Hava Kuvvetleri Komutanları; Jandarma Genel Komutanı MGK Üyesi DEĞİLDİR)", "Olağanüstü Hal (OHAL: Cumhurbaşkanı Tarafından Yurdun Tamamında veya Bir Bölgesinde En Fazla 6 Aylığına İlan Edilir; Resmi Gazetede Yayımlanır ve Aynı Gün TBMM Onayına Sunulur; TBMM Süreyi Değiştirebilir, Kaldırabilir veya Her Seferinde En Fazla 4 Ayı Geçmemek Üzere Uzatabilir)"],
                "target_videos": 4
            },
            "1982_YARGI_ORGANI": {
                "name": "1982 Anayasası Yargı Organı ve Yüksek Mahkemeler",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Yargı Yetkisi ve İlkeleri (Türk Milleti Adına Bağımsız ve Tarafsız Mahkemelerce Kullanılır, Hakimlik ve Savcılık Teminatı, Duruşmaların Açıklığı, Kararların Gerekçeli Olması)", "Yüksek Mahkemeler (4 Adettir: Anayasa Mahkemesi, Yargıtay, Danıştay, Uyuşmazlık Mahkemesi; ASKERİ YARGITAY VE ASKERİ YÜKSEK İDARE MAHKEMESİ 2017'DE KALDIRILMIŞTIR; Sayıştay ve HSK Yüksek Mahkeme DEĞİLDİR)", "Anayasa Mahkemesi (AYM: 15 Üyeden Oluşur; 3 Üyeyi TBMM, 12 Üyeyi Cumhurbaşkanı Seçer; Üyelerin Görev Süresi 12 Yıldır, Bir Kimse İki Defa AYM Üyesi Seçilemez; Emeklilik Yaşı 65'tir; Başkanını Üyeler Kendi Arasından 4 Yıllığına Gizli Oyla Seçer)", "AYM Görevleri: Norm Denetimi (İptal Davası / Soyut Norm Denetimi: Kanunlar, CBK'lar, TBMM İçtüzüğü için 60 Gün İçinde CB veya TBMM'de En Fazla Üyeye Sahip İki Parti Grubu veya En Az 1/5 120 Milletvekili Açabilir; İtiraz Yolu / Somut Norm Denetimi / Def'i Yolu: Davaya Bakan Mahkeme Tarafından Kanun veya CBK Hükmü için Başvurulur, AYM 5 Ayda Karar Verir); Bireysel Başvuru (Temel Hak ve Özgürlükleri İhlal Edilen Herkes Olağan Kanun Yollarını Tükettikten Sonra 30 Gün İçinde Başvurabilir); Yüce Divan Yargılamaları; Siyasi Parti Kapatma Davaları ve Mali Denetimi)", "Yargıtay (Adli Yargının Temyiz Mercii, Üyelerini HSK Seçer, Başsavcısını CB Seçer)", "Danıştay (İdari Yargının Temyiz Mercii, Üyelerinin 3/4'ünü HSK, 1/4'ünü Cumhurbaşkanı Seçer)", "Uyuşmazlık Mahkemesi (Adli ve İdari Yargı Arasındaki Görev ve Hüküm Uyuşmazlıklarını Kesin Çözer, Başkanını AYM Kendi Üyeleri Arasından Seçer)", "Hakimler ve Savcılar Kurulu (HSK: 13 Üyeden Oluşur, 2 Daire Halinde Çalışır; Başkanı Adalet Bakanıdır, Adalet Bakanlığı Müsteşarı / Bakan Yardımcısı Tabii Üyedir; 4 Üyeyi CB, 7 Üyeyi TBMM Seçer; Görev Süreleri 4 Yıldır; Meslekten Çıkarma Kararlarına Karşı Yargı Yolu AÇIKTIR)", "Sayıştay (TBMM Adına Kamu Harcamalarını Denetleyen Hesap Yargısı Organıdır, Üyelerini ve Başkanını TBMM Seçer)"],
                "target_videos": 4
            },
            "IDARE_HUKUKU_VE_TESKILAT": {
                "name": "İdare Hukuku ve Türkiye'nin İdari Teşkilat Yapısı",
                "exam_question_weight": "3 Soru",
                "subtopics": ["İdare Hukukunun Temel İlkeleri (Kanuni İdare, İdarenin Kanuniliği, İdarenin Bütünlüğü: Hiyerarşi ve İdari Vesayet Ayrımı)", "Hiyerarşi (Aynı Kamu Tüzel Kişisi İçindeki Ast-Üst İlişkisi: Vali -> Kaymakam, Bakan -> Genel Müdür, Rektör -> Dekan)", "İdari Vesayet (Farklı Kamu Tüzel Kişileri Arasındaki Denetim İlişkisi: İçişleri Bakanlığı -> Belediye, Vali -> Köy Muhtarı, YÖK -> Üniversite)", "Türkiye'nin İdari Teşkilat Şeması: 1. MERKEZDEN YÖNETİM (Başkent Teşkilatı: CB, Bakanlıklar, CB Teşkilatı, Yardımcı Kuruluşlar: Danıştay, Sayıştay, MGK; Taşra Teşkilatı: İl Genel İdaresi - Vali, İl İdare Şube Başkanları, İl İdare Kurulu; İlçe İdaresi - Kaymakam, İlçe İdare Şube Başkanları, İlçe İdare Kurulu; Bucak İdaresi)", "2. YERİNDEN YÖNETİM: Mahalli İdareler / Yerel Yönetimler (İl Özel İdaresi - Vali, İl Genel Meclisi, İl Encümeni; Belediye İdaresi - Belediye Başkanı, Belediye Meclisi, Belediye Encümeni; Büyükşehir Belediyesi; Köy İdaresi - Muhtar, İhtiyar Heyeti, Köy Derneği); Hizmet Yerinden Yönetim Kuruluşları (İktisadi Kamu Kurumları: KİT, TRT, TCDD; İdari Kamu Kurumları: Karayolları, Orman Genel Müd.; Sosyal: SGK, İŞKUR; Bilimsel/Kültürel: Üniversiteler, TÜBİTAK, RTÜK; Meslek Kuruluşları: Barolar, Tabipler Odası, Ticaret Odaları)", "Vali ve Kaymakam Karşılaştırması (Vali İstisnai Memurdur, CB Kararıyla Atanır, Devleti ve Cumhurbaşkanını Temsil Eder, Yetki Genişliğine Sahiptir, Yabancı Konsoloslarla Görüşebilir; Kaymakam Güvenceli Meslek Memurudur, CB Onayıyla Atanır, Yalnızca CB'yi Temsil Eder, Yetki Genişliği YOKTUR)", "Kamu Görevlileri ve 657 Sayılı DMK (Memuriyet İlkeleri: Liyakat, Kariyer, Sınıflandırma; Memurluğa Giriş Şartları; Disiplin Cezaları: Uyarma, Kınama, Aylıktan Kesme 1/30-1/8, Kademe İlerlemesinin Durdurulması 1-3 Yıl, Devlet Memurluğundan Çıkarma; Memuriyetten Çıkarma Kararını Yüksek Disiplin Kurulu Verir; Tüm Disiplin Cezalarına Karşı Yargı Yolu AÇIKTIR)"],
                "target_videos": 4
            },
            "GUNCEL_BILGILER_ULUSLARARASI": {
                "name": "Uluslararası Örgütler ve Güncel Sosyo-Kültürel Olaylar",
                "exam_question_weight": "3-6 Soru",
                "subtopics": ["Uluslararası Kuruluşlar (Birleşmiş Milletler ve Organları, NATO ve Genel Sekreteri, Avrupa Birliği Kurumları ve Genişleme Süreci, Avrupa Konseyi, Şanghay İşbirliği Örgütü, Türk Devletleri Teşkilatı, D-8 ve G-20 Ülkeleri, İKÖ/İİT, OECD, Karadeniz Ekonomik İşbirliği)", "Uluslararası Mahkemeler (Uluslararası Adalet Divanı - Lahey, Uluslararası Ceza Mahkemesi, Avrupa İnsan Hakları Mahkemesi AİHM)", "Türkiye'nin Üye Olduğu ve Kurucu Olduğu Örgütler", "2024-2025-2026 Dönemi Güncel Gelişmeler, Uzay Misyonları (Alper Gezeravcı, Tuva Cihangir Atasever), Önemli Yıl İlanları (UNESCO, BM), Edebiyat, Sanat, Sinema Ödülleri (Nobel, Oscar), Spor Başarıları ve Dünya Şampiyonaları"],
                "target_videos": 4
            }
        },

        # === GENEL YETENEK: TÜRKÇE (30 SORU) ===
        "TURKCE": {
            "SOZCUKTE_VE_SOZ_OBEKLERINDE_ANLAM": {
                "name": "Sözcükte ve Söz Öbeklerinde Anlam",
                "exam_question_weight": "3-4 Soru",
                "subtopics": ["Gerçek, Yan ve Mecaz Anlam Ayrımı", "Terim Anlam, Somutlaştırma ve Soyutlaştırma", "Eş Anlamlı, Zıt Anlamlı, Eş Sesli (Sesteş) ve Yakın Anlamlı Sözcükler", "Deyimler ve Atasözlerinin Anlamsal Özellikleri", "Dolaylama, Güzel Adlandırma ve İkilemeler"],
                "target_videos": 4
            },
            "CUMLEDE_ANLAM_VE_KAVRAMLAR": {
                "name": "Cümlede Anlam, Anlatım ve Kavramlar",
                "exam_question_weight": "3-4 Soru",
                "subtopics": ["Neden-Sonuç (Gerekçeli Yargı), Amaç-Sonuç, Koşul-Sonuç Cümleleri", "Öznel ve Nesnel Anlatım", "Doğrudan ve Dolaylı Anlatım, Örtülü Anlam", "Cümlenin İfade Ettiği Anlam Özellikleri (Tanım, Varsayım, Olasılık/İhtimal, Tahmin, Sezgi, Ön Yargı, Eleştiri, Öz Eleştiri, Kanıksama, Yadsıma, Aşamalı Durum, Yakınma, Sitem, Hayıflanma, Pişmanlık)", "Cümle Tamamlama ve Cümle Oluşturma"],
                "target_videos": 4
            },
            "PARAGRAFTA_ANLAM_VE_YAPI": {
                "name": "Paragrafta Anlam, Ana Düşünce, Yapı ve Yardımcı Fikirler",
                "exam_question_weight": "12-15 Soru",
                "subtopics": ["Paragrafta Ana Düşünce (Vurgulanan Temel Yargı)", "Paragrafta Yardımcı Düşünceler (Çıkarılamaz / Değinilmemiştir Soruları)", "Paragrafın Konusu ve Başlığı", "Paragrafta Yapı: Paragrafı İkiye Bölme, Akışı Bozan Cümle, Paragraf Tamamlama (Giriş/Gelişme/Sonuç Cümlesi Ekleme), Cümlelerin Yerini Değiştirme", "Çoklu Paragraflar (Aynı Metne Bağlı 2'li ve 3'lü Sorular)"],
                "target_videos": 4
            },
            "ANLATIM_BICIMLERI_VE_DUSUNCEYI_GELISTIRME": {
                "name": "Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Anlatım Biçimleri (Öyküleme, Betimleme, Açıklama, Tartışma)", "Düşünceyi Geliştirme Yolları (Tanımlama, Örneklendirme, Tanık Gösterme, Karşılaştırma, Sayısal Verilerden Yararlanma, Benzetme, Somutlama)", "Anlatıcı Türleri (1. ve 3. Kişili Anlatım, Hakim/İlahi, Kahraman, Gözlemci Bakış Açısı)", "Anlatım Özellikleri (Açıklık, Duruluk, Yalınlık, Akıcılık, Özgünlük, Yoğunluk/Özlülük, Evrensellik, Ulusallık)"],
                "target_videos": 4
            },
            "SES_BILGISI": {
                "name": "Ses Bilgisi ve Ses Olayları",
                "exam_question_weight": "1 Soru",
                "subtopics": ["Ünlü Düşmesi ve Ünlü Türemesi", "Ünsüz Yumuşaması (Değişimi) ve Aykırılıklar", "Ünsüz Benzeşmesi (Sertleşmesi - FıSTıKÇı ŞaHaP)", "Ünsüz Düşmesi ve Ünsüz Türemesi (İkizleşme)", "Ünlü Daralması (-yor ve kaynaştırma harfiyle)", "Ulama, Küçük ve Büyük Ünlü Uyumu"],
                "target_videos": 4
            },
            "YAZIM_KURALLARI": {
                "name": "Yazım Kuralları (TDK En Güncel Kılavuz)",
                "exam_question_weight": "1-2 Soru",
                "subtopics": ["Büyük Harflerin Kullanıldığı Yerler (Kurum, Kuruluş, Unvan, Tarihi Olay, Coğrafi Adlar)", "Ayrı ve Bitişik Yazılan Birleşik Sözcükler", "Bağlaç Olan 'de/da' ve 'ki' ile Ek Olan '-de' ve '-ki'nin Yazımı", "Soru Eki 'mı/mi'nin Yazımı", "Sayıların, Kısaltmaların ve Eklerin Yazımı", "Yazımı Karıştırılan Sözcükler (TDK Güncel Değişiklikleri)"],
                "target_videos": 4
            },
            "NOKTALAMA_ISARETLERI": {
                "name": "Noktalama İşaretleri",
                "exam_question_weight": "1-2 Soru",
                "subtopics": ["Nokta, Virgül ve Virgülün Kullanılmayacağı Yerler (Zarf-fiilden sonra, şart ekinden sonra, 've/veya' bağlaçlarından önce/sonra, tamlamalar arasına)", "Noktalı Virgül ve İki Nokta Ayrımı", "Üç Nokta, Soru ve Ünlem İşaretleri", "Kesme İşareti (Özel İsimlere Gelen Çekim Ekleri; Kurum/Kuruluş Adlarına Gelen Eklerde Kesme KULLANILMAZ)", "Tırnak, Parantez, Kısa ve Uzun Çizgi"],
                "target_videos": 4
            },
            "SOZCOKTE_YAPI_VE_EKLER": {
                "name": "Sözcükte Yapı, Kökler ve Ekler",
                "exam_question_weight": "1 Soru",
                "subtopics": ["Kök Türleri (İsim Kökü, Fiil Kökü, Ortak Kök, Sesteş Kök)", "Yapım Ekleri (İsimden İsim, İsimden Fiil, Fiilden Fiil, Fiilden İsim)", "Çekim Ekleri (İsim Çekim Ekleri: Çoğul, Hal/Durum, İyelik, İlgi/Tamlayan, Eşitlik; Fiil Çekim Ekleri: Kip ve Kişi Ekleri)", "Basit, Türemiş ve Birleşik Sözcükler"],
                "target_videos": 4
            },
            "SOZCOK_TURLERI": {
                "name": "Sözcük Türleri (İsim, Sıfat, Zamir, Zarf, Edat, Bağlaç, Ünlem)",
                "exam_question_weight": "2 Soru",
                "subtopics": ["İsimler (Adlar) ve İsim Tamlamaları (Belirtili, Belirtisiz, Zincirleme)", "Sıfatlar (Ön Adlar: Niteleme ve Belirtme Sıfatları) ve Sıfat Tamlamaları", "Zamirler (Adıllar: Kişi, İşaret, Belgisiz, Soru, Dönüşlülük 'Kendi', Ek Halindeki Zamirler)", "Zarflar (Belirteçler: Durum, Zaman, Miktar/Azlık-Çokluk, Yer-Yön, Soru Zarfları)", "Edatlar (İlgeçler), Bağlaçlar ve Ünlemler"],
                "target_videos": 4
            },
            "FIILLER_EK_FIIL_CATI_VE_FIILIMSILER": {
                "name": "Fiiller, Ek Fiil, Fiilde Çatı ve Fiilimsiler (Eylemsiler)",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Fiilde Anlam Kayması (Zaman Kayması)", "Ek Fiil (İsimleri Yüklem Yapma ve Birleşik Zamanlı Fiil Kurma: Hikaye, Rivayet, Şart)", "Fiilimsiler: İsim-Fiil (Mayışmak), Sıfat-Fiil (Anası Mezar Dikecekmiş), Zarf-Fiil (Kenyalı Asiye İnce İp Araklamadan...)", "Fiilde Çatı: Öznesine Göre (Etken, Edilgen - 'l/n' eki ve sözde özne, Dönüşlü, İşteş - 'ş' eki); Nesnesine Göre (Geçişli, Geçişsiz, Oldurgan, Ettirgen)"],
                "target_videos": 4
            },
            "CUMLENIN_OGELERI_VE_TURULERI": {
                "name": "Cümlenin Ögeleri, Cümle Türleri ve Anlatım Bozuklukları",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Cümlenin Temel Ögeleri (Yüklem, Özne - Gerçek, Gizli, Sözde, Örtülü Özne)", "Cümlenin Yardımcı Ögeleri (Nesne - Belirtili/Belirtisiz, Dolaylı Tümleç / Yer Tamlayıcısı, Zarf Tümleci, Edat Tümleci)", "Ögeleri Ayırmada Tamlama ve Deyim Bölünmezliği Kuralı", "Cümle Türleri: Yüklemin Türüne Göre (İsim/Fiil), Yüklemin Yerine Göre (Kurallı, Devrik, Eksiltili), Anlamına Göre (Olumlu, Olumsuz, Soru, Ünlem), Yapısına Göre (Basit, Birleşik - Girişik Birleşik/Fiilimsili, Sıralı - Bağımlı/Bağımsız, Bağlı Cümle)", "Anlatım Bozuklukları (Anlamsal ve Dil Bilgisel Bozukluklar)"],
                "target_videos": 4
            },
            "SOZEL_MANTIK_VE_MUHAKEME": {
                "name": "Sözel Mantık ve Muhakeme (Kesin Çözüm Metotları)",
                "exam_question_weight": "4 Soru",
                "subtopics": ["Tablo Kurma ve Değişken Tespiti (Az Olanı veya Sabit Olanı Başlık Yapma Kuralı)", "Sıralama ve Kat/Yerleştirme Problemleri", "Kategori ve Grup Eşleştirme Soruları", "Öncülleri Analiz Etme ve Kesinleşen / İhtimal Kalan Bilgileri Ayırma", "'Kesinlikle Doğrudur', 'Kesinlikle Yanlıştır', 'Hangisi Olabilir' Soru Kalıplarını Çözme Stratejisi"],
                "target_videos": 4
            }
        },

        # === GENEL YETENEK: MATEMATİK & GEOMETRİ (30 SORU) ===
        "MATEMATIK": {
            "TEMEL_KAVRAMLAR_VE_SAYILAR": {
                "name": "Temel Kavramlar, Sayı Kümeleri ve Basamak Analizi",
                "exam_question_weight": "2-3 Soru",
                "subtopics": ["Rakam, Doğal Sayı, Tam Sayı, Tek ve Çift Sayılar, Pozitif ve Negatif Sayılar", "Ardışık Sayılar ve Toplam Formülleri (Terim Sayısı, Terimler Toplamı)", "Asal Sayılar, Aralarında Asal Sayılar ve Faktöriyel Kavramı", "Sayı Basamakları ve Çözümleme"],
                "target_videos": 4
            },
            "BOLME_BOLUNEBILME_EBOB_EKOK": {
                "name": "Bölme, Bölünebilme Kuralları ve EBOB-EKOK",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Bölme İşlemi ve Kalan İlişkisi", "2, 3, 4, 5, 8, 9, 10, 11 ile Bölünebilme Kuralları ve Aralarında Asal Çarpanlara Ayırma (6, 12, 15, 18, 30, 36, 45)", "Asal Çarpanlara Ayırma ve Pozitif Bölen Sayısı", "EBOB - EKOK Hesaplama ve Problem Tipleri (Bahçe etrafına ağaç dikme, fayans döşeme, nöbet tutma/periyodik tekrar)"],
                "target_videos": 4
            },
            "RASYONEL_SAYILAR_VE_ONDALIK": {
                "name": "Rasyonel Sayılar, Ondalık Sayılar ve Basit Eşitsizlikler",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Rasyonel Sayılarda Dört İşlem ve İşlem Önceliği", "Merdivenli (Sonsuz) Kesirler", "Ondalık Sayılar ve Devirli Ondalık Açılımlar", "Rasyonel Sayılarda Sıralama", "Basit Eşitsizlikler, Aralık Kavramı ve Eşitsizlik Özellikleri (Negatif sayıyla çarpma/bölme yön değiştirir)"],
                "target_videos": 4
            },
            "MUTLAK_DEGER_USLU_KOKLU": {
                "name": "Mutlak Değer, Üslü Sayılar ve Köklü Sayılar",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Mutlak Değerin Tanımı, Özellikleri ve Mutlak Değerli Denklem/Eşitsizlikler", "Üslü Sayı Kuralları, Taban ve Üs Eşitliği, Üslü Denklemler", "Köklü Sayı Kuralları, Kök Dışına Çıkarma/İçine Alma, Paydayı Rasyonel Yapma (Eşlenik), İç İçe Kökler"],
                "target_videos": 4
            },
            "CARPANLARA_AYIRMA_VE_ORAN_ORANTI": {
                "name": "Çarpanlara Ayırma, Özdeşlikler ve Oran-Orantı",
                "exam_question_weight": "2 Soru",
                "subtopics": ["Ortak Çarpan Parantezi, Gruplandırma Yöntemi", "İki Kare Farkı Özdeşliği, Tam Kare Açılımları ve Küp Açılımları", "Rasyonel İfadelerin Sadeleştirilmesi", "Oran-Orantı Özellikleri (Doğru Orantı, Ters Orantı, Bileşik Orantı, Aritmetik ve Geometrik Ortalama)"],
                "target_videos": 4
            },
            "DENKLEM_COZME_VE_PROBLEMLER": {
                "name": "Denklem Çözme ve Temel Problemler (Sayı, Kesir, Yaş, İşçi)",
                "exam_question_weight": "6-8 Soru",
                "subtopics": ["Birinci Dereceden Bir ve İki Bilinmeyenli Denklem Sistemleri", "Sayı ve Kesir Problemleri", "Yaş Problemleri (Yıllar geçtikçe yaş farkının değişmemesi kuralı)", "İşçi Problemleri (Birim zamanda yapılan iş üzerinden çözüm)"],
                "target_videos": 4
            },
            "TICARI_VE_HAREKET_PROBLEMLERI": {
                "name": "Yüzde, Kâr-Zarar, Karışım, Hareket (Hız) ve Grafik Problemleri",
                "exam_question_weight": "4-5 Soru",
                "subtopics": ["Yüzde Hesapları, KDV, İndirim ve Zam", "Kâr - Zarar Problemleri (Maliyet, Satış, Etiket Fiyatı)", "Karışım Problemleri (Madde Miktarı / Toplam Miktar Formülü)", "Hareket ve Hız Problemleri ($x = v \\cdot t$, Zıt Yönlü ve Aynı Yönlü Hareket, Tünel ve Tren, Ortalama Hız)", "Grafik ve Tablo Okuma Problemleri (Daire, Çizgi, Sütun Grafikleri)"],
                "target_videos": 4
            },
            "KUMELER_FONKSIYONLAR_OLASILIK": {
                "name": "Kümeler, Fonksiyonlar, Permütasyon, Kombinasyon ve Olasılık",
                "exam_question_weight": "3 Soru",
                "subtopics": ["Kümelerde Birleşim, Kesişim, Fark, Tümleyen ve Küme Problemleri", "Fonksiyon Kavramı, Değer Bulma, Bileşke ve Ters Fonksiyon", "Sayma İlkeleri, Faktöriyel ve Permütasyon (Sıralama)", "Kombinasyon (Grup Seçimi) ve Binom Açılımı", "Basit Olasılık Hesabı (İstenen Durum / Tüm Durumlar)"],
                "target_videos": 4
            },
            "GEOMETRI_VE_SAYISAL_MANTIK": {
                "name": "Geometri (Açılar, Üçgenler, Dörtgenler, Çember, Analitik) ve Sayısal Mantık",
                "exam_question_weight": "4-5 Soru",
                "subtopics": ["Doğruda ve Üçgende Açılar", "Özel Üçgenler (3-4-5, 5-12-13, 8-15-17, 7-24-25, 30-60-90, 45-45-90)", "Üçgende Alan, Benzerlik, Açıortay ve Kenarortay Bağıntıları", "Çokgenler ve Özel Dörtgenler (Kare, Dikdörtgen, Paralelkenar, Eşkenar Dörtgen, Yamuk, Deltoid)", "Çember ve Daire (Açı, Uzunluk, Dairede Alan)", "Analitik Geometri (Noktanın ve Doğrunun Analitiği, Eğim, Doğru Denklemleri)", "Katı Cisimler (Prizma, Silindir, Koni, Küre Hacim ve Alanları)", "Sayısal Mantık, Şekil Yeteneği ve Sayı Dizileri"],
                "target_videos": 4
            }
        }
    }

    @classmethod
    def initialize_mastery_matrix(cls):
        """Veritabanındaki topic_mastery tablosunu resmi müfredatla ilklendirir."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            for lesson, topics in cls.OFFICIAL_CURRICULUM.items():
                for topic_code, topic_info in topics.items():
                    topic_id = f"{lesson}_{topic_code}"
                    cursor.execute("""
                    INSERT INTO topic_mastery (
                        topic_id, lesson, topic_name, target_videos_count,
                        consumed_videos_count, distinct_teachers_json, distinct_channels_json,
                        consumed_video_ids_json, facts_count, traps_count, reasoning_count,
                        mnemonics_count, mastery_stage, is_mastered, updated_at
                    ) VALUES (?, ?, ?, ?, 0, '[]', '[]', '[]', 0, 0, 0, 0, 'UNSTARTED', 0, ?)
                    ON CONFLICT(topic_id) DO NOTHING
                    """, (
                        topic_id,
                        lesson,
                        topic_info["name"],
                        topic_info.get("target_videos", 4),
                        now_str
                    ))

    @classmethod
    def record_video_consumption(
        cls,
        lesson: str,
        topic: str,
        video_id: str,
        teacher_name: str,
        channel_name: str,
        facts_extracted: int = 0,
        traps_extracted: int = 0,
        reasoning_extracted: int = 0,
        mnemonics_extracted: int = 0
    ) -> Dict[str, Any]:
        """
        Bir video tüketildiğinde ilgili resmi konunun hakimiyet sayımlarını ve öğretmen çeşitliliğini günceller.
        """
        now_str = datetime.now().isoformat()
        matched_topic_id = cls._find_matching_topic_id(lesson, topic)
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM topic_mastery WHERE topic_id = ?", (matched_topic_id,))
            row = cursor.fetchone()
            
            if not row:
                cls.initialize_mastery_matrix()
                cursor.execute("SELECT * FROM topic_mastery WHERE topic_id = ?", (matched_topic_id,))
                row = cursor.fetchone()

            if row:
                teachers: List[str] = json.loads(row["distinct_teachers_json"])
                channels: List[str] = json.loads(row["distinct_channels_json"])
                video_ids: List[str] = json.loads(row["consumed_video_ids_json"])

                if teacher_name and teacher_name not in teachers:
                    teachers.append(teacher_name)
                if channel_name and channel_name not in channels:
                    channels.append(channel_name)
                if video_id and video_id not in video_ids:
                    video_ids.append(video_id)

                consumed_count = len(video_ids)
                target_count = row["target_videos_count"]

                # Aşama hesaplama (En az 3-4 video kuralı)
                if consumed_count == 0:
                    stage = "UNSTARTED"
                elif consumed_count == 1:
                    stage = "STARTED (1/4 Video)"
                elif consumed_count == 2:
                    stage = "DEVELOPING (2/4 Video)"
                elif consumed_count == 3:
                    stage = "SYNTHESIZING (3/4 Video)"
                else:
                    stage = "MASTERED (4+/4 Video - Uzman Öğretmen Seviyesi)"

                is_mastered = 1 if consumed_count >= target_count and len(teachers) >= 2 else 0

                cursor.execute("""
                UPDATE topic_mastery
                SET consumed_videos_count = ?,
                    distinct_teachers_json = ?,
                    distinct_channels_json = ?,
                    consumed_video_ids_json = ?,
                    facts_count = facts_count + ?,
                    traps_count = traps_count + ?,
                    reasoning_count = reasoning_count + ?,
                    mnemonics_count = mnemonics_count + ?,
                    mastery_stage = ?,
                    is_mastered = ?,
                    last_digested_at = ?,
                    updated_at = ?
                WHERE topic_id = ?
                """, (
                    consumed_count,
                    json.dumps(teachers, ensure_ascii=False),
                    json.dumps(channels, ensure_ascii=False),
                    json.dumps(video_ids, ensure_ascii=False),
                    facts_extracted,
                    traps_extracted,
                    reasoning_extracted,
                    mnemonics_extracted,
                    stage,
                    is_mastered,
                    now_str,
                    now_str,
                    matched_topic_id
                ))

                return {
                    "topic_id": matched_topic_id,
                    "lesson": lesson,
                    "consumed_videos_count": consumed_count,
                    "target_videos_count": target_count,
                    "distinct_teachers_count": len(teachers),
                    "teachers": teachers,
                    "mastery_stage": stage,
                    "is_mastered": bool(is_mastered)
                }

        return {}

    @classmethod
    def _find_matching_topic_id(cls, lesson: str, topic_str: str) -> str:
        """Metin içindeki anahtar kelimelerden en uygun resmi müfredat topic_id'sini tespit eder."""
        clean_lesson = lesson.upper().replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
        if clean_lesson not in cls.OFFICIAL_CURRICULUM:
            clean_lesson = "TARIH"

        topic_str_lower = topic_str.lower()
        topics_dict = cls.OFFICIAL_CURRICULUM.get(clean_lesson, {})
        
        for code, data in topics_dict.items():
            name_lower = data["name"].lower()
            if topic_str_lower in name_lower or name_lower in topic_str_lower:
                return f"{clean_lesson}_{code}"
            for sub in data.get("subtopics", []):
                if sub.lower() in topic_str_lower or topic_str_lower in sub.lower():
                    return f"{clean_lesson}_{code}"

        # Varsayılan ilk konu
        first_code = list(topics_dict.keys())[0] if topics_dict else "GENEL"
        return f"{clean_lesson}_{first_code}"

    @classmethod
    def get_curriculum_mastery_report(cls) -> Dict[str, Any]:
        """Tüm müfredatın resmi konu hakimiyet durumunu detaylı döner."""
        cls.initialize_mastery_matrix()
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM topic_mastery ORDER BY lesson, topic_id")
            rows = cursor.fetchall()
            
            all_topics = []
            total_topics = len(rows)
            mastered_topics = 0
            synthesizing_topics = 0
            in_progress_topics = 0
            unstarted_topics = 0
            
            by_lesson_stats: Dict[str, Dict[str, int]] = {}

            for r in rows:
                item = dict(r)
                item["distinct_teachers"] = json.loads(item["distinct_teachers_json"])
                item["distinct_channels"] = json.loads(item["distinct_channels_json"])
                item["consumed_video_ids"] = json.loads(item["consumed_video_ids_json"])
                
                ls = item["lesson"]
                if ls not in by_lesson_stats:
                    by_lesson_stats[ls] = {"total": 0, "mastered": 0, "in_progress": 0, "unstarted": 0, "videos_consumed": 0}
                
                by_lesson_stats[ls]["total"] += 1
                by_lesson_stats[ls]["videos_consumed"] += item["consumed_videos_count"]

                if item["is_mastered"] == 1 or item["consumed_videos_count"] >= item["target_videos_count"]:
                    mastered_topics += 1
                    by_lesson_stats[ls]["mastered"] += 1
                elif item["consumed_videos_count"] == 3:
                    synthesizing_topics += 1
                    by_lesson_stats[ls]["in_progress"] += 1
                elif item["consumed_videos_count"] > 0:
                    in_progress_topics += 1
                    by_lesson_stats[ls]["in_progress"] += 1
                else:
                    unstarted_topics += 1
                    by_lesson_stats[ls]["unstarted"] += 1

                all_topics.append(item)

            return {
                "total_official_topics": total_topics,
                "fully_mastered_count": mastered_topics,
                "synthesizing_count": synthesizing_topics,
                "in_progress_count": in_progress_topics,
                "unstarted_count": unstarted_topics,
                "mastery_percentage": round((mastered_topics / max(1, total_topics)) * 100, 1),
                "by_lesson": by_lesson_stats,
                "topics": all_topics
            }

    @classmethod
    def get_topics_needing_videos(cls, max_topics: int = 5) -> List[Dict[str, Any]]:
        """Henüz 3-4 video eşiğine ulaşmamış ve öncelikli araştırılması gereken konuları listeler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM topic_mastery
            WHERE is_mastered = 0 AND consumed_videos_count < target_videos_count
            ORDER BY consumed_videos_count ASC, lesson ASC
            LIMIT ?
            """, (max_topics,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["distinct_teachers"] = json.loads(item["distinct_teachers_json"])
                item["needed_videos_count"] = item["target_videos_count"] - item["consumed_videos_count"]
                result.append(item)
            return result

    @classmethod
    def get_scores(cls) -> Dict[str, float]:
        """Tüm konuların doluluk / güven skorlarını döner (0.0 - 1.0)."""
        scores = {}
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic_id, consumed_videos_count, target_videos_count, is_mastered FROM topic_mastery")
            rows = cursor.fetchall()
            for r in rows:
                t_id = r["topic_id"]
                if r["is_mastered"] == 1:
                    scores[t_id] = 0.98
                else:
                    scores[t_id] = round(r["consumed_videos_count"] / max(1, r["target_videos_count"]), 2)
        return scores

    @classmethod
    def update_score(cls, topic_id: str, score: float = 0.98):
        """Belirli bir konunun güven ve tamlık skorunu günceller."""
        is_mastered = 1 if score >= 0.85 else 0
        stage = "MASTERED (Uzman Seviyesi)" if score >= 0.85 else "IN_PROGRESS"
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE topic_mastery
            SET is_mastered = ?, mastery_stage = ?, updated_at = ?
            WHERE topic_id = ? OR topic_name = ?
            """, (is_mastered, stage, datetime.now().isoformat(), topic_id, topic_id))

curriculum_matrix = CurriculumMatrixEngine()
# Otomatik veritabanı eşitlemesi
curriculum_matrix.initialize_mastery_matrix()

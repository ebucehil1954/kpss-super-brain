"""
Promius KPSS Super-Brain: Otonom Yapay Zeka Öğretmen Gözlem ve Yönetim Merkezi (Mission Control v5)
Çalıştırmak için: python web_ui.py
Erişim: http://127.0.0.1:8500
"""
import os
import sys
import uvicorn
from fastapi.responses import HTMLResponse
from api.server import app

@app.get("/", response_class=HTMLResponse)
async def serve_control_panel():
    return """
<!DOCTYPE html>
<html lang="tr" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Promius KPSS Super-Brain | Otonom Yapay Zeka Öğretmen Zihni</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #070a13; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .glass-panel { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .tab-nav-btn { cursor: pointer; transition: all 0.2s ease; }
        .tab-nav-btn.active { background: rgba(99, 102, 241, 0.25); color: #a5b4fc; border-color: rgba(99, 102, 241, 0.5); font-weight: 700; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0b0f19; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
    </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col">
    <!-- Top Header -->
    <header class="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center font-black text-xl shadow-lg shadow-indigo-500/30">
                🧠
            </div>
            <div>
                <h1 class="text-sm font-black tracking-tight text-white flex items-center gap-2">
                    PROMIUS KPSS SUPER-BRAIN
                    <span class="text-[9px] uppercase font-black tracking-widest px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 animate-pulse" id="header-status-badge">
                        7/24 Otonom Zihin Aktif
                    </span>
                </h1>
                <p class="text-[11px] text-slate-400 font-medium">Her Konuda En Az 3-4 Farklı Hocayı Tüketen ve Karşılaştırmalı Sentez Yapan KPSS Uzman Öğretmeni</p>
            </div>
        </div>

        <!-- Status & Stats Badges -->
        <div id="status-bar" class="flex items-center gap-3 text-xs">
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <span class="text-slate-400">Müfredat Kapsamı:</span>
                <span class="text-emerald-400 font-bold font-mono" id="stat-curriculum-coverage">%0 (0/49 Konu)</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <span class="text-slate-400">İzlenen Video:</span>
                <span class="text-rose-400 font-bold font-mono" id="stat-videos-watched">0 Ders</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <span class="text-slate-400">Ambar:</span>
                <span class="text-cyan-400 font-bold font-mono" id="stat-records">0 Bilgi</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <span class="text-slate-400">Model:</span>
                <span class="text-indigo-300 font-bold font-mono" id="active-model">qwen2.5:14b</span>
            </div>
        </div>
    </header>

    <!-- Navigation Bar (Tabs) -->
    <div class="bg-slate-950/70 border-b border-slate-800/80 px-6 py-2 flex items-center gap-2 overflow-x-auto">
        <button onclick="switchTab('dashboard')" id="btn-tab-dashboard" class="tab-nav-btn active px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>🚀 Canlı Yönetim & Video Sindirici</span>
        </button>
        <button onclick="switchTab('curriculum-matrix')" id="btn-tab-curriculum-matrix" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>📋 Resmi Müfredat & Konu Hakimiyet Matrisi</span>
            <span class="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono" id="badge-mastered-count">0/49</span>
        </button>
        <button onclick="switchTab('manus-discovery')" id="btn-tab-manus-discovery" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>🌐 Manus YouTube Keşif Radarı</span>
            <span class="px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-mono" id="badge-playlists-count">0 Kanal</span>
        </button>
        <button onclick="switchTab('cross-syntheses')" id="btn-tab-cross-syntheses" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>🎓 Çoklu Hoca Uzman Sentezi</span>
            <span class="px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-mono" id="badge-syntheses-count">0 Sentez</span>
        </button>
        <button onclick="switchTab('knowledge-store')" id="btn-tab-knowledge-store" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>💾 Yapılandırılmış Bilgi Ambarı</span>
            <span class="px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-mono" id="badge-kr">0</span>
        </button>
        <button onclick="switchTab('video-queue-view')" id="btn-tab-video-queue-view" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>📺 Video Kuyruğu & İzleme Takibi</span>
            <span class="px-1.5 py-0.2 rounded-full bg-rose-500/20 text-rose-300 text-[10px] font-mono" id="badge-vq">0</span>
        </button>
        <button onclick="switchTab('pdf-studio')" id="btn-tab-pdf-studio" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>📚 Kitap & PDF Sindirici</span>
        </button>
        <button onclick="switchTab('exports-hub')" id="btn-tab-exports-hub" class="tab-nav-btn px-3.5 py-1.5 rounded-xl text-xs text-slate-300 border border-transparent hover:bg-slate-900 flex items-center gap-2">
            <span>📁 Sade JSON Dışa Aktarımları</span>
        </button>
    </div>

    <!-- Main Content -->
    <main class="flex-1 p-6 max-w-[1680px] w-full mx-auto space-y-6">

        <!-- TAB 1: DASHBOARD -->
        <div id="tab-pane-dashboard" class="space-y-6">
            <!-- Metric Cards -->
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div class="glass-panel p-4 rounded-2xl flex items-center justify-between cursor-pointer" onclick="switchTab('curriculum-matrix')">
                    <div>
                        <span class="text-xs text-slate-400 font-medium">Tamamlanan Konu (>=4 Video)</span>
                        <h3 class="text-2xl font-black text-emerald-400 mt-1" id="dash-mastered-topics">0</h3>
                    </div>
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold text-lg">🎓</div>
                </div>
                <div class="glass-panel p-4 rounded-2xl flex items-center justify-between cursor-pointer" onclick="switchTab('video-queue-view')">
                    <div>
                        <span class="text-xs text-slate-400 font-medium">İzlenen Ders Videosu</span>
                        <h3 class="text-2xl font-black text-rose-400 mt-1" id="dash-watched">0</h3>
                    </div>
                    <div class="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center font-bold text-lg">📺</div>
                </div>
                <div class="glass-panel p-4 rounded-2xl flex items-center justify-between cursor-pointer" onclick="switchTab('cross-syntheses')">
                    <div>
                        <span class="text-xs text-slate-400 font-medium">Çoklu Hoca Sentezi</span>
                        <h3 class="text-2xl font-black text-indigo-400 mt-1" id="dash-syntheses">0</h3>
                    </div>
                    <div class="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-bold text-lg">👨‍🏫</div>
                </div>
                <div class="glass-panel p-4 rounded-2xl flex items-center justify-between cursor-pointer" onclick="switchTab('knowledge-store')">
                    <div>
                        <span class="text-xs text-slate-400 font-medium">Toplam Bilgi Kaydı</span>
                        <h3 class="text-2xl font-black text-cyan-400 mt-1" id="dash-records">0</h3>
                    </div>
                    <div class="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center font-bold text-lg">💾</div>
                </div>
                <div class="glass-panel p-4 rounded-2xl flex items-center justify-between border-emerald-500/30">
                    <div>
                        <span class="text-xs text-slate-400 font-medium">Öğretmenlik Düzeyi</span>
                        <h3 class="text-sm font-black text-emerald-400 mt-1" id="dash-status-text">DERİNLEŞİYOR</h3>
                    </div>
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold text-lg">🧠</div>
                </div>
            </div>

            <!-- Action & Live Feed -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <!-- Left: Controls -->
                <div class="lg:col-span-5 space-y-6">
                    <div class="glass-panel p-6 rounded-3xl space-y-4">
                        <h2 class="text-xs font-black uppercase tracking-wider text-slate-200 flex items-center gap-2">
                            ⚡ Canlı Döngü & Manus Keşif Kontrolü
                        </h2>
                        <p class="text-xs text-slate-400">
                            KPSS zihni arka planda <code>python start_super_brain.bat</code> ile kesintisiz çalışarak YouTube'u tarar ve 3-4 video eşiğini tamamlar.
                        </p>
                        
                        <div class="space-y-2.5 pt-2">
                            <button id="btn-trigger-manus" onclick="triggerManusDiscovery()" class="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 font-bold text-xs text-white flex items-center justify-center gap-2 transition-all shadow-lg shadow-purple-600/30">
                                🕵️‍♂️ Manus YouTube Keşif Ajanını Çalıştır (Tüm Müfredat)
                            </button>
                            <button id="btn-trigger-step" onclick="triggerStep(false)" class="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold text-xs text-white flex items-center justify-center gap-2 transition-all">
                                🎬 Sıradaki Dersi Tüket ve Beyne İşle (1 Adım)
                            </button>
                            <button onclick="triggerExportRefresh()" class="w-full py-2.5 rounded-xl border border-slate-700 hover:bg-slate-800 text-xs text-slate-300 flex items-center justify-center gap-2">
                                📁 Sade JSON Dosyalarını Hemen Dışa Aktar
                            </button>
                        </div>
                    </div>

                    <!-- Gaps Alert Box -->
                    <div class="glass-panel p-5 rounded-3xl space-y-3">
                        <div class="flex items-center justify-between">
                            <h3 class="text-xs font-bold text-slate-200 flex items-center gap-2">
                                🎯 Öncelikli Video İhtiyacı Olan Konular
                            </h3>
                            <button onclick="loadHealthGaps()" class="text-[10px] text-indigo-400 hover:underline">Yenile</button>
                        </div>
                        <div id="gaps-list" class="space-y-2 max-h-[260px] overflow-y-auto pr-1 text-xs">
                            <!-- Loaded via JS -->
                        </div>
                    </div>
                </div>

                <!-- Right: Output Feed -->
                <div class="lg:col-span-7 space-y-6">
                    <div class="glass-panel p-5 rounded-3xl space-y-4">
                        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                            <div class="flex items-center gap-2">
                                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                <h3 class="text-xs font-bold text-white uppercase tracking-wider">Son Video Sindirme & Çıkarım Raporu</h3>
                            </div>
                            <span class="text-[10px] text-slate-400 font-mono" id="feed-timestamp">Hazır</span>
                        </div>

                        <div id="dashboard-feed" class="space-y-4 max-h-[620px] overflow-y-auto pr-2 text-xs">
                            <div class="p-8 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-center space-y-2">
                                <div class="text-3xl">🧠</div>
                                <p class="font-bold text-slate-200 text-sm">KPSS Uzman Öğretmen Zihni Hazır</p>
                                <p class="text-xs text-slate-400 max-w-md mx-auto">
                                    Sol taraftan <strong>'Manus YouTube Keşif Ajanını Çalıştır'</strong> butonuna basarak tüm müfredat için 3-4 farklı popüler hocanın derslerini aratıp kuyruğa alabilirsiniz.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: RESMİ MÜFREDAT & KONU HAKİMİYET MATRİSİ -->
        <div id="tab-pane-curriculum-matrix" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            📋 Resmi ÖSYM Müfredatı & Konu Hakimiyet Matrisi
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">Her resmi konu başlığı için en az 3-4 farklı hoca videosu tüketilerek uzman seviyesine ulaşılır.</p>
                    </div>
                    <div class="flex items-center gap-3 w-full md:w-auto">
                        <select id="matrix-lesson-filter" onchange="renderCurriculumMatrix()" class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white">
                            <option value="">Tüm Dersler</option>
                            <option value="TARIH">Tarih (27 Soru)</option>
                            <option value="COGRAFYA">Coğrafya (18 Soru)</option>
                            <option value="VATANDASLIK">Vatandaşlık (15 Soru)</option>
                            <option value="TURKCE">Türkçe (30 Soru)</option>
                            <option value="MATEMATIK">Matematik (30 Soru)</option>
                        </select>
                        <button onclick="loadCurriculumMastery()" class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold text-xs text-white">Yenile</button>
                    </div>
                </div>

                <div id="matrix-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <!-- Loaded dynamically via JS -->
                </div>
            </div>
        </div>

        <!-- TAB 3: MANUS YOUTUBE KEŞİF RADARI -->
        <div id="tab-pane-manus-discovery" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            🌐 Manus YouTube Keşif & Kaynak Radarı
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">YouTube üzerindeki tüm popüler KPSS kanalları, oynatma listeleri ve tam ders serileri.</p>
                    </div>
                    <button onclick="triggerManusDiscovery()" class="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 font-bold text-xs text-white shadow-lg shadow-purple-600/30">
                        🚀 Otonom Keşfi Başlat
                    </button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div class="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
                        <h3 class="text-xs font-bold text-slate-200">🕵️‍♂️ Ajan Durumu</h3>
                        <div id="discovery-agent-status" class="text-xs text-slate-300 space-y-2 font-mono">
                            <div>Durum: <span class="text-emerald-400" id="agent-state">HAZIR</span></div>
                            <div>Son Tarama: <span class="text-slate-400" id="agent-last-scan">Henüz yapılmadı</span></div>
                        </div>
                    </div>
                    <div class="lg:col-span-2 p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
                        <h3 class="text-xs font-bold text-slate-200">📺 Keşfedilen Oynatma Listeleri & Seriler</h3>
                        <div id="discovered-playlists-list" class="space-y-2 max-h-[360px] overflow-y-auto pr-1 text-xs">
                            <!-- Loaded via JS -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 4: ÇOKLU HOCA UZMAN SENTEZİ -->
        <div id="tab-pane-cross-syntheses" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            🎓 Çoklu Öğretmen Karşılaştırmalı Uzman Sentezi
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">3-4 farklı hocanın aynı konudaki ortaklaştığı noktalar, tuzaklar ve taktikleri tek çatı altında.</p>
                    </div>
                    <button onclick="loadCrossSyntheses()" class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold text-xs text-white">Yenile</button>
                </div>

                <div id="syntheses-container" class="space-y-4">
                    <!-- Loaded via JS -->
                </div>
            </div>
        </div>

        <!-- TAB 5: KNOWLEDGE STORE (FTS5 Search) -->
        <div id="tab-pane-knowledge-store" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            💾 Yapılandırılmış Bilgi Ambarı (FTS5 Arama)
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">Videolardan çıkarılan olgular (FACT), tuzaklar (TRAP), şifreler (MNEMONIC) ve eğitmen vurguları.</p>
                    </div>
                    <div class="flex items-center gap-3 w-full md:w-auto">
                        <input type="text" id="kr-search-input" onkeyup="if(event.key==='Enter')loadKnowledgeRecords()" placeholder="FTS5 Anlamsal ara (örn: TBMM, Tanzimat, Bakır...)" 
                               class="bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 w-full md:w-64" />
                        <select id="kr-lesson-filter" onchange="loadKnowledgeRecords()" class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white">
                            <option value="">Tüm Dersler</option>
                            <option value="VATANDASLIK">Vatandaşlık</option>
                            <option value="TARIH">Tarih</option>
                            <option value="COGRAFYA">Coğrafya</option>
                            <option value="TURKCE">Türkçe</option>
                            <option value="MATEMATIK">Matematik</option>
                        </select>
                        <button onclick="loadKnowledgeRecords()" class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold text-xs text-white">Ara</button>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-2xl border border-slate-800">
                    <table class="w-full text-left text-xs text-slate-300">
                        <thead class="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                            <tr>
                                <th class="p-3">Tür & Ders</th>
                                <th class="p-3">Öğrenilen Bilgi & Metin</th>
                                <th class="p-3">Kaynak & Öğretmen</th>
                                <th class="p-3 text-center">Pekiştirme</th>
                                <th class="p-3">Tarih</th>
                            </tr>
                        </thead>
                        <tbody id="kr-table-body" class="divide-y divide-slate-800/60 font-sans">
                            <!-- Loaded via JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 6: VIDEO QUEUE -->
        <div id="tab-pane-video-queue-view" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex items-center justify-between">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            📺 Video İzleme Kuyruğu ve Takibi
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">Sıradaki izlenecek ders videoları ve hocaları.</p>
                    </div>
                </div>
                <div id="vq-stats-cards" class="grid grid-cols-2 md:grid-cols-4 gap-4"></div>
            </div>
        </div>

        <!-- TAB 7: PDF STUDIO -->
        <div id="tab-pane-pdf-studio" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <h2 class="text-base font-black text-white flex items-center gap-2">
                    📚 Kitap & PDF Belge Sindirici
                </h2>
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div class="lg:col-span-5 space-y-4">
                        <input type="file" id="pdf-file-input" accept=".pdf,.txt" onchange="handleFileSelected(event)" class="text-xs text-slate-300" />
                        <div id="selected-file-name" class="text-xs text-indigo-400 hidden"></div>
                        <input type="text" id="doc-topic" placeholder="Konu Başlığı (örn: Osmanlı Kültür ve Medeniyeti)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white" />
                        <select id="doc-lesson" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white">
                            <option value="TARIH">Tarih</option>
                            <option value="COGRAFYA">Coğrafya</option>
                            <option value="VATANDASLIK">Vatandaşlık</option>
                            <option value="TURKCE">Türkçe</option>
                            <option value="MATEMATIK">Matematik</option>
                        </select>
                        <button id="btn-ingest-doc" onclick="startDocumentIngestion()" class="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-bold text-xs text-white">
                            📖 Belgeyi Zihne İşle
                        </button>
                    </div>
                    <div class="lg:col-span-7" id="doc-ingest-output">
                        <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-400">
                            PDF yüklemek için sol taraftan dosya seçin.
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 8: EXPORTS HUB -->
        <div id="tab-pane-exports-hub" class="hidden space-y-6">
            <div class="glass-panel p-6 rounded-3xl space-y-5">
                <div class="flex items-center justify-between">
                    <div>
                        <h2 class="text-base font-black text-white flex items-center gap-2">
                            📁 Sade JSON Dışa Aktarımları (Exports Hub)
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5"><code>kpss-super-brain/data/exports/</code> klasöründeki temiz JSON dosyaları.</p>
                    </div>
                    <button onclick="triggerExportRefresh()" class="px-4 py-2 rounded-xl bg-indigo-600 font-bold text-xs text-white">Yeniden Dışa Aktar</button>
                </div>
                <div id="exports-list" class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs"></div>
            </div>
        </div>

    </main>

    <script>
        let allCurriculumTopics = [];

        function switchTab(tabId) {
            document.querySelectorAll('[id^="tab-pane-"]').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-nav-btn').forEach(el => el.classList.remove('active'));
            
            const targetPane = document.getElementById(`tab-pane-${tabId}`);
            const targetBtn = document.getElementById(`btn-tab-${tabId}`);
            if (targetPane) targetPane.classList.remove('hidden');
            if (targetBtn) targetBtn.classList.add('active');

            if (tabId === 'curriculum-matrix') loadCurriculumMastery();
            if (tabId === 'manus-discovery') loadManusDiscovery();
            if (tabId === 'cross-syntheses') loadCrossSyntheses();
            if (tabId === 'knowledge-store') loadKnowledgeRecords();
            if (tabId === 'video-queue-view') loadVideoQueue();
        }

        async function updateStatus() {
            try {
                const res = await fetch('/api/curriculum/mastery');
                const matrix = await res.json();
                
                document.getElementById('stat-curriculum-coverage').textContent = `%${matrix.mastery_percentage || 0} (${matrix.fully_mastered_count}/${matrix.total_official_topics} Konu)`;
                document.getElementById('badge-mastered-count').textContent = `${matrix.fully_mastered_count}/${matrix.total_official_topics}`;
                document.getElementById('dash-mastered-topics').textContent = `${matrix.fully_mastered_count}/${matrix.total_official_topics}`;

                const sRes = await fetch('/api/status');
                const statusData = await sRes.json();
                const metrics = statusData.metrics || {};
                
                document.getElementById('stat-videos-watched').textContent = `${metrics.videos_watched || 0} Ders`;
                document.getElementById('dash-watched').textContent = metrics.videos_watched || 0;
                document.getElementById('stat-records').textContent = `${metrics.total_records || 0} Bilgi`;
                document.getElementById('dash-records').textContent = metrics.total_records || 0;
                document.getElementById('badge-kr').textContent = metrics.total_records || 0;

                const synthRes = await fetch('/api/curriculum/syntheses');
                const synthData = await synthRes.json();
                document.getElementById('dash-syntheses').textContent = synthData.total || 0;
                document.getElementById('badge-syntheses-count').textContent = `${synthData.total || 0} Sentez`;

                loadHealthGaps();
            } catch (e) {
                console.error("Status update error", e);
            }
        }

        async function loadHealthGaps() {
            try {
                const res = await fetch('/api/health/gaps');
                const data = await res.json();
                const container = document.getElementById('gaps-list');
                
                if (data.critical_gaps && data.critical_gaps.length > 0) {
                    container.innerHTML = data.critical_gaps.slice(0, 5).map(g => `
                        <div class="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs hover:border-slate-700 transition-all">
                            <div class="space-y-0.5">
                                <div class="flex items-center gap-2">
                                    <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-indigo-500/20 text-indigo-300">${g.lesson}</span>
                                    <span class="font-bold text-white">${g.topic}</span>
                                </div>
                                <div class="text-[10px] text-slate-400">Tüketilen: ${g.consumed_videos}/${g.target_videos} Video | Farklı Hoca: ${g.teachers_count}</div>
                            </div>
                            <span class="px-2 py-0.5 rounded text-[9px] font-bold ${g.consumed_videos === 0 ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'}">${g.status}</span>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = `<div class="p-4 text-center text-emerald-400 text-xs font-bold">🎉 Tüm müfredat konularında en az 3-4 video tüketildi!</div>`;
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function loadCurriculumMastery() {
            try {
                const res = await fetch('/api/curriculum/mastery');
                const data = await res.json();
                allCurriculumTopics = data.topics || [];
                renderCurriculumMatrix();
            } catch (e) {
                console.error(e);
            }
        }

        function renderCurriculumMatrix() {
            const filterLesson = document.getElementById('matrix-lesson-filter').value;
            const container = document.getElementById('matrix-grid');
            
            const filtered = filterLesson ? allCurriculumTopics.filter(t => t.lesson === filterLesson) : allCurriculumTopics;

            container.innerHTML = filtered.map(t => {
                const consumed = t.consumed_videos_count || 0;
                const target = t.target_videos_count || 4;
                const pct = Math.min(100, Math.round((consumed / target) * 100));
                const teachers = t.distinct_teachers || [];

                let badgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30";
                let stageText = "0/4 Video (Eksik)";
                if (consumed >= target) {
                    badgeClass = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
                    stageText = `${consumed}/4 Video (Uzman Seviyesi)`;
                } else if (consumed === 3) {
                    badgeClass = "bg-purple-500/20 text-purple-300 border-purple-500/30";
                    stageText = "3/4 Video (Sentezleniyor)";
                } else if (consumed > 0) {
                    badgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
                    stageText = `${consumed}/4 Video (Öğreniliyor)`;
                }

                return `
                    <div class="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3 hover:border-indigo-500/50 transition-all">
                        <div class="flex items-start justify-between gap-2">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300">${t.lesson}</span>
                            <span class="px-2 py-0.5 rounded-full text-[9px] font-bold border ${badgeClass}">${stageText}</span>
                        </div>
                        <h4 class="font-bold text-white text-xs leading-snug">${t.topic_name}</h4>
                        
                        <div class="space-y-1">
                            <div class="flex items-center justify-between text-[10px] text-slate-400">
                                <span>İlerleme (${consumed}/${target} Video)</span>
                                <span>%${pct}</span>
                            </div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div class="bg-gradient-to-r from-indigo-500 to-emerald-400 h-1.5 rounded-full" style="width: ${pct}%"></div>
                            </div>
                        </div>

                        <div class="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
                            <div>Hocalar: ${teachers.length > 0 ? teachers.join(', ') : 'Henüz izlenmedi'}</div>
                            <div class="text-cyan-300 font-bold">${t.facts_count || 0} Bilgi</div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function loadManusDiscovery() {
            try {
                const res = await fetch('/api/discovery/status');
                const data = await res.json();
                
                document.getElementById('agent-state').textContent = data.is_scanning ? "AKTİF TARAMA YAPIYOR..." : "HAZIR (BEKLEMEDE)";
                document.getElementById('agent-state').className = data.is_scanning ? "text-purple-400 animate-pulse font-bold" : "text-emerald-400 font-bold";
                document.getElementById('agent-last-scan').textContent = data.last_scan_time ? new Date(data.last_scan_time).toLocaleTimeString() : 'Henüz yapılmadı';
                document.getElementById('badge-playlists-count').textContent = `${data.total_discovered_channels_playlists || 0} Kaynak`;

                const listContainer = document.getElementById('discovered-playlists-list');
                if (data.recent_discoveries && data.recent_discoveries.length > 0) {
                    listContainer.innerHTML = data.recent_discoveries.map(p => `
                        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                            <div class="space-y-0.5">
                                <div class="font-bold text-white">${p.title}</div>
                                <div class="text-[10px] text-slate-400">Kanal: ${p.channel_name} (${p.channel_handle || ''}) | Ders: ${p.lesson}</div>
                            </div>
                            <a href="${p.url}" target="_blank" class="px-2.5 py-1 rounded bg-indigo-600/30 hover:bg-indigo-600 text-[10px] text-indigo-300 font-bold">YouTube'da Aç</a>
                        </div>
                    `).join('');
                } else {
                    listContainer.innerHTML = `<div class="p-4 text-center text-slate-500">Henüz taranmış bir oynatma listesi yok. 'Otonom Keşfi Başlat' butonuna basınız.</div>`;
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function triggerManusDiscovery() {
            const btn = document.getElementById('btn-trigger-manus');
            if (btn) { btn.disabled = true; btn.textContent = "🕵️‍♂️ Keşif Başlatıldı..."; }
            try {
                const res = await fetch('/api/discovery/trigger', { method: 'POST' });
                const data = await res.json();
                alert(`Manus Keşfi Başarılı: +${data.videos_queued || 0} video kuyruğa alındı!`);
                loadManusDiscovery();
                updateStatus();
            } catch (e) {
                alert(`Hata: ${e.message}`);
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = "🕵️‍♂️ Manus YouTube Keşif Ajanını Çalıştır (Tüm Müfredat)"; }
            }
        }

        async function triggerStep(forceDiscovery = false) {
            const btn = document.getElementById('btn-trigger-step');
            if (btn) { btn.disabled = true; btn.textContent = "⏳ Video Zihne İşleniyor..."; }
            try {
                const res = await fetch('/api/autonomous/step', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ force_discovery: forceDiscovery })
                });
                const data = await res.json();
                
                const feed = document.getElementById('dashboard-feed');
                if (data.result) {
                    const r = data.result;
                    feed.innerHTML = `
                        <div class="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-3">
                            <div class="flex items-center justify-between">
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">${r.lesson} - ${r.topic}</span>
                                <span class="text-[10px] text-slate-400 font-mono">${r.teacher}</span>
                            </div>
                            <h4 class="font-bold text-white text-sm">✅ Ders Başarıyla Sindirildi!</h4>
                            <div class="grid grid-cols-4 gap-2 text-center text-[11px] pt-1">
                                <div class="p-2 bg-slate-900 rounded-xl"><span class="text-emerald-400 font-bold">+${r.facts_extracted}</span> Bilgi</div>
                                <div class="p-2 bg-slate-900 rounded-xl"><span class="text-rose-400 font-bold">+${r.traps_extracted}</span> Tuzak</div>
                                <div class="p-2 bg-slate-900 rounded-xl"><span class="text-amber-400 font-bold">+${r.mnemonics_extracted}</span> Şifre</div>
                                <div class="p-2 bg-slate-900 rounded-xl"><span class="text-indigo-400 font-bold">+${r.reasoning_extracted}</span> Mantık</div>
                            </div>
                        </div>
                    ` + feed.innerHTML;
                }
                updateStatus();
            } catch (e) {
                console.error(e);
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = "🎬 Sıradaki Dersi Tüket ve Beyne İşle (1 Adım)"; }
            }
        }

        async function loadCrossSyntheses() {
            try {
                const res = await fetch('/api/curriculum/syntheses');
                const data = await res.json();
                const container = document.getElementById('syntheses-container');

                if (data.syntheses && data.syntheses.length > 0) {
                    container.innerHTML = data.syntheses.map(s => `
                        <div class="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                            <div class="flex items-center justify-between">
                                <span class="px-2.5 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 text-xs font-bold">${s.lesson} — ${s.topic}</span>
                                <span class="text-xs text-slate-400">İncelenen Hocalar: <strong class="text-white">${(s.teachers_involved || []).join(', ')}</strong></span>
                            </div>
                            
                            <div class="text-xs text-slate-300 leading-relaxed font-sans">${s.master_summary.replace(/\\n/g, '<br>')}</div>

                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                                <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                    <div class="text-[11px] font-bold text-emerald-400">✅ Hocaların Ortaklaştığı Kesin Bilgiler</div>
                                    <ul class="text-[10px] text-slate-300 list-disc pl-4 space-y-0.5">
                                        ${(s.consensus_facts || []).slice(0, 4).map(f => `<li>${f}</li>`).join('')}
                                    </ul>
                                </div>
                                <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                    <div class="text-[11px] font-bold text-rose-400">⚠️ ÖSYM Çeldirici ve Sınav Tuzakları</div>
                                    <ul class="text-[10px] text-slate-300 list-disc pl-4 space-y-0.5">
                                        ${(s.unified_traps || []).slice(0, 4).map(tr => `<li>${tr}</li>`).join('')}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs">Henüz 3-4 video tüketilerek tamamlanmış bir hoca sentezi yok. Videolar sindirildikçe otomatik sentezlenecektir.</div>`;
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function loadKnowledgeRecords() {
            const query = document.getElementById('kr-search-input')?.value || '';
            const lesson = document.getElementById('kr-lesson-filter')?.value || '';
            try {
                const res = await fetch(`/api/knowledge/records?query=${encodeURIComponent(query)}&lesson=${encodeURIComponent(lesson)}&limit=40`);
                const data = await res.json();
                const tbody = document.getElementById('kr-table-body');
                
                tbody.innerHTML = (data.records || []).map(r => `
                    <tr class="hover:bg-slate-900/60 transition-all">
                        <td class="p-3">
                            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${r.record_type === 'FACT' ? 'bg-cyan-500/20 text-cyan-300' : (r.record_type === 'TRAP' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300')}">${r.record_type}</span>
                            <div class="text-[10px] text-slate-400 mt-0.5">${r.lesson}</div>
                        </td>
                        <td class="p-3 max-w-lg text-slate-200">${r.text}</td>
                        <td class="p-3 text-[11px] text-slate-400">${(r.source_chain && r.source_chain[0] && r.source_chain[0].teacher) || 'Genel'}</td>
                        <td class="p-3 text-center text-emerald-400 font-bold">${r.times_reinforced || 1}x</td>
                        <td class="p-3 text-[10px] text-slate-500 font-mono">${r.first_learned ? r.first_learned.split('T')[0] : ''}</td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error(e);
            }
        }

        async function loadVideoQueue() {
            try {
                const res = await fetch('/api/video-queue');
                const data = await res.json();
                const container = document.getElementById('vq-stats-cards');
                const counts = data.status_counts || {};
                
                container.innerHTML = `
                    <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center"><div class="text-xs text-slate-400">Bekleyen (Pending)</div><div class="text-xl font-black text-amber-400 mt-1">${counts.PENDING || 0}</div></div>
                    <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center"><div class="text-xs text-slate-400">İzlenen (Watched)</div><div class="text-xl font-black text-emerald-400 mt-1">${counts.WATCHED || 0}</div></div>
                    <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center"><div class="text-xs text-slate-400">İşlenen (Processing)</div><div class="text-xl font-black text-cyan-400 mt-1">${counts.PROCESSING || 0}</div></div>
                    <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center"><div class="text-xs text-slate-400">Toplam Kuyruk</div><div class="text-xl font-black text-white mt-1">${data.total_in_queue || 0}</div></div>
                `;
            } catch (e) {
                console.error(e);
            }
        }

        async function triggerExportRefresh() {
            try {
                const res = await fetch('/api/exports/refresh', { method: 'POST' });
                const data = await res.json();
                alert(`Dışa aktarım başarılı! ${Object.keys(data.files || {}).length} adet JSON güncellendi.`);
            } catch (e) {
                alert(`Hata: ${e.message}`);
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            updateStatus();
            setInterval(updateStatus, 8000);
        });
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("[SUPER-BRAIN MISSION CONTROL] Başlatılıyor...")
    print("Web Tarayıcınızda açın: http://127.0.0.1:8500")
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8500, reload=False)

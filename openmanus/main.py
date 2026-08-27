"""
OpenManus Ana Giriş Noktası (CLI Arayüzü)
Kullanıcıdan "Soru: " şeklinde girdi alır.
Argümanlarda veya girdide "kpss" terimi geçtiğinde doğrudan KPSSAgent'ı çağırır.
"""
import argparse
import asyncio
import sys
from typing import Optional

from app.agent.manus import Manus
from app.agent.kpss_agent import KPSSAgent
from app.logger import logger


def parse_arguments():
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(
        description="OpenManus & KPSS Super-Brain Otonom Ajan CLI Arayüzü"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Komut satırından doğrudan verilecek soru veya argümanlar (Örn: python main.py kpss 'AYM üye sayısı kaçtır?')"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=False,
        help="Ajan için doğrudan sorgu metni"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="kpss",
        choices=["kpss", "manus"],
        help="Çalıştırılacak ajan tipi: 'kpss' (varsayılan) veya 'manus'"
    )
    parser.add_argument(
        "--kpss",
        action="store_true",
        help="KPSSAgent'ı doğrudan çalıştırmak için bayrak"
    )
    return parser.parse_args()


async def main():
    args = parse_arguments()

    # CLI argümanlarında "kpss" geçip geçmediğini dinamik kontrol et
    raw_argv = [arg.lower() for arg in sys.argv[1:]]
    use_kpss = (
        args.kpss
        or "kpss" in raw_argv
        or args.agent.lower() == "kpss"
    )

    # İlgili ajanı oluştur ve başlat
    if use_kpss:
        logger.info("🎓 KPSSAgent (KPSS & Resmi Mevzuat Uzmanı) seçildi.")
        agent = await KPSSAgent.create()
    else:
        logger.info("🤖 Standart Manus Genel Ajanı seçildi.")
        agent = await Manus.create()

    try:
        # 1. Öncelik: --prompt parametresi
        # 2. Öncelik: Pozisyonel query argümanları (içindeki 'kpss' anahtar kelimesini temizle)
        # 3. Öncelik: Konsoldan interaktif 'Soru: ' girdisi
        prompt: Optional[str] = None
        if args.prompt:
            prompt = args.prompt
        elif args.query:
            clean_query_parts = [q for q in args.query if q.lower() != "kpss"]
            if clean_query_parts:
                prompt = " ".join(clean_query_parts)

        if not prompt:
            print("\n" + "=" * 55)
            print("🏛️  KPSS & OPENMANUS OTONOM BEYİN CLI SİSTEMİ")
            print("=" * 55)
            prompt = input("Soru: ")

        clean_prompt = prompt.strip()
        if not clean_prompt:
            logger.warning("Boş soru girildi. Sistem kapatılıyor.")
            return

        logger.info(f"Soru alındı ve işleniyor: '{clean_prompt}'")
        print("\n⏳ Ajan kaynakları tarıyor, çelişkileri çözüyor ve yanıt hazırlıyor...\n")

        # Ajanı doğrudan await ile çalıştır
        answer = await agent.run(clean_prompt)

        print("\n" + "=" * 55)
        print("📝 AJAN CEVABI:")
        print("=" * 55)
        if answer:
            print(answer)
        else:
            print("İşlem tamamlandı.")
        print("=" * 55 + "\n")

    except KeyboardInterrupt:
        logger.warning("İşlem kullanıcı tarafından durduruldu (Ctrl+C).")
    except Exception as e:
        logger.error(f"Ajan çalışırken beklenmeyen bir hata oluştu: {e}")
    finally:
        # Ajan kaynaklarını güvenle temizle
        logger.info("Ajan kaynakları temizleniyor...")
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
import os
import re
import numpy as np
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt

# --- RESMI TATIL TAKVIMI ---
try:
    import holidays
    tr_holidays = holidays.Turkey(years=range(2020, 2030))
    # np.busday_count icin dogru format: datetime64[D]
    tat_tatiller = np.array([np.datetime64(d) for d in tr_holidays.keys()], dtype="datetime64[D]")
except Exception:
    tat_tatiller = np.array([], dtype="datetime64[D]")

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .ana-baslik-kutusu {
        background-color: transparent; border: 4px solid #1a4a7c;
        padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 30px;
    }
    .ana-baslik-yazisi { color: var(--text-color); font-size: 38px !important; font-weight: 900 !important; margin: 0; }
    [data-testid="stMetric"] {
        background-color: transparent; border: 3px solid #1a4a7c !important;
        padding: 20px !important; border-radius: 20px !important;
    }
    div[data-testid="stMetricValue"] > div { color: #1a4a7c !important; font-weight: 900 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: var(--text-color) !important; font-weight: 700 !important;
    }
    div[data-testid="stSidebarUserContent"] .stMultiSelect,
    div[data-testid="stSidebarUserContent"] .stSelectbox,
    div[data-testid="stSidebarUserContent"] .stRadio {
        background-color: transparent !important; border: 2px solid #1a4a7c !important;
        padding: 15px !important; border-radius: 12px !important; margin-bottom: 15px !important;
    }
    .imza-alani { text-align: right; font-family: 'Courier New', monospace; font-weight: bold; padding-top: 10px; color: var(--text-color); }
    .logo-alti-yazi { text-align: center; font-weight: 800; color: #1a4a7c !important; margin-top: 10px; }
    .mini-ciro-kutu {
        border: 2px solid #1a4a7c; padding: 12px; border-radius: 12px;
        text-align: center; min-width: 120px; background-color: transparent; flex: 1 1 0;
    }
    .mini-ciro-ay { font-size: 1rem; font-weight: 800; color: var(--text-color); margin-bottom: 5px; }
    .mini-ciro-deger { color: #1a4a7c; font-size: 1.25rem; font-weight: 900; }
    @media (prefers-color-scheme: dark) {
        .logo-alti-yazi { color: #3b82f6 !important; }
        div[data-testid="stMetricValue"] > div { color: #3b82f6 !important; }
        .mini-ciro-kutu { border-color: #3b82f6; }
        .mini-ciro-deger { color: #3b82f6; }
        div[data-testid="stSidebarUserContent"] .stMultiSelect,
        div[data-testid="stSidebarUserContent"] .stSelectbox,
        div[data-testid="stSidebarUserContent"] .stRadio { border: 2px solid #3b82f6 !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YONETIMI ---
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

if not st.session_state["giris_yapildi"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=250)
        st.title("🔒 Güvenli Giriş")
        with st.form("login_form"):
            kullanici_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Sisteme Giriş Yap"):
                if kullanici_adi == "admin" and sifre == "lab2026":
                    st.session_state["giris_yapildi"] = True
                    st.rerun()
                else:
                    st.error("❌ Bilgiler hatalı!")

# --- YARDIMCI FONKSIYONLAR ---
def normalize_text(text):
    t = str(text).upper()
    return (
        t.replace("İ", "I")
         .replace("Ç", "C")
         .replace("Ş", "S")
         .replace("Ü", "U")
         .replace("Ö", "O")
         .replace("Ğ", "G")
         .strip()
    )


def test_kategorisi_bul(test_adi):
    t = normalize_text(test_adi)

    # 4 ana SLA kategorisi:
    # 1) Test adında ARASTIRMA geçiyorsa diğer gruplara dahil edilmez.
    if "ARASTIRMA" in t:
        return "Araştırma Testleri (Hedef: Belirsiz)", None

    # 2) PCR veya DNA geçiyorsa moleküler
    if "PCR" in t or "DNA" in t:
        return "Moleküler Test (Hedef: 3 Gün)", 3

    # 3) Ekim, Bakteri, Total Bakteri, Bakteriyolojik, Antibiyogram geçiyorsa bakteriyolojik
    if any(x in t for x in ["EKIM", "BAKTERI", "TOTAL BAKTERI", "BAKTERIYOLOJIK", "ANTIBIYOGRAM"]):
        return "Bakteriyolojik Test (Hedef: 5 Gün)", 5

    # 4) Bunlar dışında kalan tüm testler seroloji
    return "Serolojik Test (Hedef: 3 Gün)", 3


def tat_hesapla(row):
    """
    SLA/TAT hesabı yalnızca tarih bazlı yapılır.

    Notlar:
    - Yeni veri girişinde saat yazmaya gerek yoktur.
    - Eski kayıtlarda saat varsa okunur ama hesapta sadece tarih kısmı kullanılır.
    - Kapsam: Numune Geliş Zamanı dolu ve 06.05.2026 veya sonrası olan kayıtlar.
    - Hedefler: Moleküler 3 iş günü, Bakteriyolojik 5 iş günü, Seroloji 3 iş günü, Araştırma hedef süresi belirsizdir ve SLA başarı/gecikme hesabına dahil edilmez.
    """
    kategori, hedef = test_kategorisi_bul(row.get("Yapılan Test", ""))

    gelis = row.get("Numune Geliş Zamanı")
    test = row.get("Test tarihi")
    milat = pd.Timestamp("2026-05-06").date()

    if pd.isna(gelis):
        return pd.Series([kategori, "Numune Geliş Zamanı Yok", None, hedef])

    try:
        gelis = pd.Timestamp(gelis)
    except Exception:
        return pd.Series([kategori, "Hatalı Numune Geliş Tarihi", None, hedef])

    if gelis.date() < milat:
        return pd.Series([kategori, "6 Mayıs Öncesi (Kapsam Dışı)", None, hedef])

    # Araştırma testlerinde hedef süresi şimdilik belirsizdir.
    # Bu kayıtlar raporda ayrı gösterilir ancak SLA başarı/gecikme oranına dahil edilmez.
    if hedef is None:
        return pd.Series([kategori, "Hedef Tanımsız", None, hedef])

    if pd.isna(test):
        return pd.Series([kategori, "Test Tarihi Eksik", None, hedef])

    try:
        test = pd.Timestamp(test)
    except Exception:
        return pd.Series([kategori, "Hatalı Test Tarihi", None, hedef])

    try:
        # Sadece tarih bazlı hesap: saat bilgisi varsa yok sayılır.
        baslangic = np.datetime64(gelis.date(), "D")
        bitis = np.datetime64(test.date(), "D")

        gun_farki = np.busday_count(baslangic, bitis, holidays=tat_tatiller)
        gun_farki = max(int(gun_farki), 0)

        durum = "Hedef İçi" if gun_farki <= hedef else "Gecikmeli"
        return pd.Series([kategori, durum, gun_farki, hedef])

    except Exception as e:
        return pd.Series([kategori, f"Hatalı Tarih: {e}", None, hedef])

def tarih_saat_duzelt(x):
    """
    Google Sheets / Excel tarihlerini güvenli şekilde datetime'a çevirir.

    Önemli düzeltme:
    Excel/Sheets bazen tarih+saat değerini 46148.458333 gibi seri sayı olarak verir.
    Eski kod bunu metne çevirip pd.to_datetime ile okuyamadığı için NaT oluyordu;
    bu yüzden binlerce SLA satırı grafiğe girmiyordu.
    """
    if pd.isna(x):
        return pd.NaT

    # Excel/Google Sheets seri tarihi: 46148.458333 = 06.05.2026 11:00 gibi
    if isinstance(x, (int, float, np.integer, np.floating)):
        try:
            if 20000 < float(x) < 80000:
                return pd.to_datetime(float(x), unit="D", origin="1899-12-30")
        except Exception:
            pass

    val = str(x).strip()
    if val.lower() in ["nan", "nat", "", "-", "null", "none"]:
        return pd.NaT

    # Seri tarih metin olarak geldiyse: "46148.458333333336"
    try:
        numeric_val = float(val.replace(",", "."))
        if 20000 < numeric_val < 80000:
            return pd.to_datetime(numeric_val, unit="D", origin="1899-12-30")
    except Exception:
        pass

    val = re.sub(r"\s+", " ", val)
    val = val.replace("/", ".")

    # Örn: "08.05.2026 09.00" veya "12.05:2026 16:30"
    if " " in val:
        d_part, t_part = val.split(" ", 1)
        d_part = d_part.replace(":", ".")
        t_part = t_part.replace(".", ":")
        val = f"{d_part} {t_part}"
    else:
        val = val.replace(":", ".")

    return pd.to_datetime(val, errors="coerce", dayfirst=True)


def para_temizle(deger):
    try:
        deger = str(deger)
        deger = re.sub(r"[^\d.,]", "", deger)
        if not deger:
            return 0.0
        if "." in deger and "," in deger:
            if deger.rfind(",") > deger.rfind("."):
                deger = deger.replace(".", "").replace(",", ".")
            else:
                deger = deger.replace(",", "")
        elif "," in deger:
            deger = deger.replace(",", ".")
        return float(deger)
    except Exception:
        return 0.0

# --- PDF MOTORU ---
def pdf_olustur(df_filtreli):
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    def tr_temizle(text):
        return str(text).translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))

    def pdf_kategori_bul(test_adi):
        kategori, _ = test_kategorisi_bul(test_adi)
        if "Araştırma" in kategori:
            return "Arastirma Testleri"
        if "Moleküler" in kategori:
            return "Molekuler Testler"
        if "Bakteriyolojik" in kategori:
            return "Bakteriyolojik Testler"
        return "Serolojik Testler"

    grup_aciklamalari = {
        "Arastirma Testleri": "(Test adinda arastirma ibaresi bulunan ozel calismalar)",
        "Molekuler Testler": "(PCR veya DNA ifadeli molekuler analizler)",
        "Bakteriyolojik Testler": "(Ekim, bakteri, total bakteri, bakteriyolojik, antibiyogram vb.)",
        "Serolojik Testler": "(Arastirma, molekuler ve bakteriyolojik disindaki tum testler)",
    }

    df_pdf = df_filtreli.copy()
    if "Yapılan Test" in df_pdf.columns:
        df_pdf["PDF_Grup"] = df_pdf["Yapılan Test"].apply(pdf_kategori_bul)
    else:
        df_pdf["PDF_Grup"] = "Serolojik Testler"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- PDF LOGO ---
    # logo.png dosyası rapor.py ile aynı GitHub klasöründe olmalı.
    try:
        base_dir = Path(__file__).resolve().parent
    except Exception:
        base_dir = Path.cwd()
    logo_path = base_dir / "logo.png"
    if logo_path.exists():
        try:
            pdf.image(str(logo_path), x=10, y=8, w=35)
            pdf.ln(12)
        except Exception:
            pdf.ln(5)
    else:
        pdf.ln(5)

    pdf.set_fill_color(26, 74, 124)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, tr_temizle("DIAGEN LABORATUVARI ANALIZ RAPORU"), ln=True, align="C", fill=True)

    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, tr_temizle(f"Rapor Uretim Tarihi: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="R")
    pdf.ln(5)

    # 🎯 OPERASYONEL HEDEF (SLA/TAT) PDF ÖZETİ
    # Bu bölüm satır sayısını değil, İşlenen Numune Sayısı toplamını esas alır.
    if all(col in df_pdf.columns for col in ["TAT_Durum", "TAT_Kategori", "İşlenen Numune Sayısı"]):
        tat_gecerli = df_pdf[df_pdf["TAT_Durum"].isin(["Hedef İçi", "Gecikmeli"])].copy()

        if not tat_gecerli.empty:
            toplam_analiz = tat_gecerli["İşlenen Numune Sayısı"].sum()
            hedef_ici = tat_gecerli[tat_gecerli["TAT_Durum"] == "Hedef İçi"]["İşlenen Numune Sayısı"].sum()
            gecikmeli = tat_gecerli[tat_gecerli["TAT_Durum"] == "Gecikmeli"]["İşlenen Numune Sayısı"].sum()
            hedef_tanimsiz = df_pdf[df_pdf["TAT_Durum"] == "Hedef Tanımsız"]["İşlenen Numune Sayısı"].sum()
            basari = (hedef_ici / toplam_analiz * 100) if toplam_analiz > 0 else 0

            pdf.set_fill_color(220, 255, 220)
            pdf.set_text_color(0, 90, 0)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, tr_temizle(" OPERASYONEL HEDEF (SLA/TAT) PERFORMANSI"), ln=True, fill=True, align="C")

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(63, 10, tr_temizle(f"Toplam Analiz: {int(toplam_analiz)}"), border=1)
            pdf.cell(63, 10, tr_temizle(f"Hedef Ici: {int(hedef_ici)}"), border=1)
            pdf.cell(64, 10, tr_temizle(f"Gecikmeli: {int(gecikmeli)}"), border=1, ln=True)
            pdf.cell(190, 10, tr_temizle(f"Genel Basari Orani: %{basari:.1f}"), border=1, ln=True, align="C")
            if hedef_tanimsiz > 0:
                pdf.cell(190, 8, tr_temizle(f"Arastirma / Hedef Tanimsiz Analiz: {int(hedef_tanimsiz)} (SLA basari oranina dahil degildir)"), border=1, ln=True, align="C")
            pdf.ln(5)

            pdf.set_fill_color(200, 200, 200)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(80, 8, tr_temizle("Test Kategorisi"), border=1, fill=True)
            pdf.cell(35, 8, tr_temizle("Hedef Ici"), border=1, align="C", fill=True)
            pdf.cell(35, 8, tr_temizle("Gecikmeli"), border=1, align="C", fill=True)
            pdf.cell(40, 8, tr_temizle("Basari %"), border=1, align="C", fill=True)
            pdf.ln()

            kategori_ozet = (
                tat_gecerli
                .groupby(["TAT_Kategori", "TAT_Durum"])["İşlenen Numune Sayısı"]
                .sum()
                .unstack(fill_value=0)
                .reset_index()
            )

            # Üç ana kategori sırasını PDF'de sabit tut
            kategori_sirasi = [
                "Moleküler Test (Hedef: 3 Gün)",
                "Bakteriyolojik Test (Hedef: 5 Gün)",
                "Serolojik Test (Hedef: 3 Gün)",
            ]
            kategori_ozet["_sira"] = kategori_ozet["TAT_Kategori"].apply(
                lambda x: kategori_sirasi.index(x) if x in kategori_sirasi else 99
            )
            kategori_ozet = kategori_ozet.sort_values("_sira")

            pdf.set_font("Arial", "", 9)
            for _, row in kategori_ozet.iterrows():
                kategori = row["TAT_Kategori"]
                h_ici = row["Hedef İçi"] if "Hedef İçi" in row else 0
                gec = row["Gecikmeli"] if "Gecikmeli" in row else 0
                toplam = h_ici + gec
                oran = (h_ici / toplam * 100) if toplam > 0 else 0

                pdf.cell(80, 8, tr_temizle(kategori), border=1)
                pdf.cell(35, 8, str(int(h_ici)), border=1, align="C")
                pdf.cell(35, 8, str(int(gec)), border=1, align="C")
                pdf.cell(40, 8, f"%{oran:.1f}", border=1, align="C")
                pdf.ln()

            # Kısa açıklama: Raporu okuyan kişinin SLA/TAT kavramlarını bilmesine gerek kalmasın
            pdf.set_text_color(90, 90, 90)
            pdf.set_font("Arial", "I", 8)
            pdf.multi_cell(0, 5, tr_temizle(
                "Aciklama: SLA, laboratuvarin belirlenen hedef sureler icinde analiz sonuclandirma performansini ifade eder. "
                "TAT ise numunenin laboratuvara kabulunden test sonuclandirilmasina kadar gecen operasyonel suredir. "
                "Bu bolumdeki adetler satir sayisini degil, Islenen Numune Sayisi toplamlarini esas alir."
            ))
            pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, tr_temizle(" DONEMSEL GENEL TOPLAM NUMUNE DURUMU"), ln=True, fill=True)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 10, tr_temizle(f" Toplam Gelen Numune : {int(df_pdf['Gelen Numune Sayısı'].sum())} Adet"), border=1)
    pdf.cell(95, 10, tr_temizle(f" Toplam Islenen Numune: {int(df_pdf['İşlenen Numune Sayısı'].sum())} Adet"), border=1, ln=True)
    pdf.ln(5)

    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(50, 8, tr_temizle("Test Grubu"), border=1, fill=True)
    pdf.cell(115, 8, tr_temizle("Grup Icerigi"), border=1, fill=True)
    pdf.cell(25, 8, tr_temizle("Toplam"), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    if "Yapılan Test" in df_pdf.columns:
        genel_grup = df_pdf.groupby("PDF_Grup")["İşlenen Numune Sayısı"].sum().reset_index()
        for _, satir in genel_grup.iterrows():
            if satir["İşlenen Numune Sayısı"] > 0:
                pdf.cell(50, 8, tr_temizle(satir["PDF_Grup"]), border=1)
                pdf.cell(115, 8, tr_temizle(grup_aciklamalari.get(satir["PDF_Grup"], "")), border=1)
                pdf.cell(25, 8, str(int(satir["İşlenen Numune Sayısı"])), border=1, align="C")
                pdf.ln()
    pdf.ln(10)

    # 📅 AYLIK DETAYLI NUMUNE VE TEST ANALİZİ
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, tr_temizle(" AYLIK DETAYLI NUMUNE VE TEST ANALIZI"), ln=True, fill=True)
    pdf.ln(3)

    ay_sirasi = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    if "Ay" in df_pdf.columns:
        mevcut_aylar = [ay for ay in df_pdf["Ay"].dropna().unique() if ay in ay_sirasi]
        sirali_aylar = sorted(mevcut_aylar, key=lambda x: ay_sirasi.index(x))
    else:
        sirali_aylar = []

    for ay in sirali_aylar:
        df_ay = df_pdf[df_pdf["Ay"] == ay]
        gelen_toplam = int(df_ay["Gelen Numune Sayısı"].sum()) if "Gelen Numune Sayısı" in df_ay.columns else 0
        islenen_toplam = int(df_ay["İşlenen Numune Sayısı"].sum()) if "İşlenen Numune Sayısı" in df_ay.columns else 0

        if islenen_toplam == 0 and gelen_toplam == 0:
            continue

        # Sayfa sonuna yaklaşıldıysa yeni sayfa aç
        if pdf.get_y() > 245:
            pdf.add_page()

        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(190, 8, tr_temizle(f" [{ay.upper()} AYI]  |  Gelen: {gelen_toplam} Numune  -  Islenen: {islenen_toplam} Analiz"), border=1, ln=True, fill=True)

        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(80, 7, tr_temizle("Test Grubu"), border=1, fill=True)
        pdf.cell(75, 7, tr_temizle("Grup Icerigi"), border=1, fill=True)
        pdf.cell(35, 7, tr_temizle("Islenen Analiz"), border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        if "PDF_Grup" in df_ay.columns and "İşlenen Numune Sayısı" in df_ay.columns:
            aylik_grup = (
                df_ay.groupby("PDF_Grup")["İşlenen Numune Sayısı"]
                .sum()
                .reset_index()
                .sort_values("İşlenen Numune Sayısı", ascending=False)
            )
            for _, satir in aylik_grup.iterrows():
                if satir["İşlenen Numune Sayısı"] > 0:
                    if pdf.get_y() > 270:
                        pdf.add_page()
                    pdf.cell(80, 6, tr_temizle(satir["PDF_Grup"]), border=1)
                    pdf.cell(75, 6, tr_temizle(grup_aciklamalari.get(satir["PDF_Grup"], "")), border=1)
                    pdf.cell(35, 6, str(int(satir["İşlenen Numune Sayısı"])), border=1, align="C")
                    pdf.ln()
        pdf.ln(5)



    # 📈 PDF ÖZET GRAFIK SAYFASI
    # Performans için artık dashboarddaki tüm grafikler tek tek uzun şekilde PDF'e basılmaz.
    # İlk bölümler/tablolar aynen korunur; buradan itibaren sadece yönetici özeti verilir.
    try:
        pdf.add_page()
        pdf.set_fill_color(26, 74, 124)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 13, tr_temizle("YONETICI OZETI - GRAFIK VE KISA TABLOLAR"), ln=True, align="C", fill=True)
        pdf.ln(4)

        pdf.set_text_color(80, 80, 80)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(0, 5, tr_temizle(
            "Bu sayfa, dashboard'daki detayli grafiklerin PDF icin sadeleştirilmis ozetidir. "
            "Raporun hizli acilmasi ve sayfa sayisinin dusmesi icin yalnizca ana kirilimlar verilir. "
            "Adetlerde islenen analiz sayisi esas alinmistir."
        ))
        pdf.ln(3)

        # 1) Aylık işlem hacmi tablosu - kısa özet
        if all(c in df_pdf.columns for c in ["Ay", "Gelen Numune Sayısı", "İşlenen Numune Sayısı"]):
            aylik = (
                df_pdf.groupby("Ay")[["Gelen Numune Sayısı", "İşlenen Numune Sayısı"]]
                .sum()
                .reindex(ay_sirasi)
                .dropna(how="all")
                .fillna(0)
            )
            if not aylik.empty:
                pdf.set_fill_color(230, 240, 250)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, tr_temizle("Aylik Hacim Ozeti"), ln=True, fill=True)
                pdf.set_fill_color(210, 210, 210)
                pdf.set_font("Arial", "B", 8)
                pdf.cell(50, 7, tr_temizle("Ay"), border=1, fill=True)
                pdf.cell(45, 7, tr_temizle("Gelen Numune"), border=1, align="C", fill=True)
                pdf.cell(50, 7, tr_temizle("Islenen Analiz"), border=1, align="C", fill=True)
                pdf.cell(45, 7, tr_temizle("Analiz/Numune"), border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for ay, row in aylik.iterrows():
                    gelen = float(row.get("Gelen Numune Sayısı", 0))
                    islenen = float(row.get("İşlenen Numune Sayısı", 0))
                    oran = islenen / gelen if gelen > 0 else 0
                    pdf.cell(50, 6, tr_temizle(ay), border=1)
                    pdf.cell(45, 6, str(int(gelen)), border=1, align="C")
                    pdf.cell(50, 6, str(int(islenen)), border=1, align="C")
                    pdf.cell(45, 6, f"{oran:.1f}", border=1, align="C")
                    pdf.ln()
                pdf.ln(4)

        # 2) SLA kategori özeti - kısa tablo
        if all(c in df_pdf.columns for c in ["TAT_Durum", "TAT_Kategori", "İşlenen Numune Sayısı"]):
            tat_gecerli = df_pdf[df_pdf["TAT_Durum"].isin(["Hedef İçi", "Gecikmeli"])]
            if not tat_gecerli.empty:
                kat_sira = [
                    "Moleküler Test (Hedef: 3 Gün)",
                    "Bakteriyolojik Test (Hedef: 5 Gün)",
                    "Serolojik Test (Hedef: 3 Gün)",
                ]
                kat_ozet = tat_gecerli.groupby(["TAT_Kategori", "TAT_Durum"])["İşlenen Numune Sayısı"].sum().unstack(fill_value=0)
                kat_ozet = kat_ozet.reindex(kat_sira).fillna(0)

                pdf.set_fill_color(230, 240, 250)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, tr_temizle("Hedef Uyum Ozeti"), ln=True, fill=True)
                pdf.set_fill_color(210, 210, 210)
                pdf.set_font("Arial", "B", 8)
                pdf.cell(75, 7, tr_temizle("Kategori"), border=1, fill=True)
                pdf.cell(35, 7, tr_temizle("Hedef Ici"), border=1, align="C", fill=True)
                pdf.cell(35, 7, tr_temizle("Gecikmeli"), border=1, align="C", fill=True)
                pdf.cell(45, 7, tr_temizle("Basari %"), border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for kat, row in kat_ozet.iterrows():
                    hedef_ici = float(row.get("Hedef İçi", 0))
                    gecikmeli = float(row.get("Gecikmeli", 0))
                    toplam = hedef_ici + gecikmeli
                    basari = hedef_ici / toplam * 100 if toplam > 0 else 0
                    pdf.cell(75, 6, tr_temizle(str(kat).split(" (")[0]), border=1)
                    pdf.cell(35, 6, str(int(hedef_ici)), border=1, align="C")
                    pdf.cell(35, 6, str(int(gecikmeli)), border=1, align="C")
                    pdf.cell(45, 6, f"%{basari:.1f}", border=1, align="C")
                    pdf.ln()
                pdf.ln(4)

        # 3) İlk 10 şehir + ilk 10 müşteri + ilk 15 test paneli: grafik yerine kısa tablolar
        def kisa_liste_tablosu(baslik, seri, kolon_adi, limit=10):
            if seri is None or seri.empty:
                return
            nonlocal_pdf_y = pdf.get_y()
            if nonlocal_pdf_y > 225:
                pdf.add_page()
            pdf.set_fill_color(230, 240, 250)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, tr_temizle(baslik), ln=True, fill=True)
            pdf.set_fill_color(210, 210, 210)
            pdf.set_font("Arial", "B", 8)
            pdf.cell(135, 7, tr_temizle(kolon_adi), border=1, fill=True)
            pdf.cell(55, 7, tr_temizle("Islenen Analiz"), border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Arial", "", 7)
            for idx, val in seri.head(limit).items():
                isim = tr_temizle(str(idx))[:75]
                pdf.cell(135, 5.5, isim, border=1)
                pdf.cell(55, 5.5, str(int(val)), border=1, align="C")
                pdf.ln()
            pdf.ln(3)

        if all(c in df_pdf.columns for c in ["Numunenin Geldiği Şehir", "İşlenen Numune Sayısı"]):
            sehir = df_pdf.groupby("Numunenin Geldiği Şehir")["İşlenen Numune Sayısı"].sum().sort_values(ascending=False)
            kisa_liste_tablosu("Sehir Bazli Operasyon Hacmi - Ilk 10", sehir, "Sehir", 10)

        if all(c in df_pdf.columns for c in ["Kurum/Numune Sahibi", "İşlenen Numune Sayısı"]):
            musteri = df_pdf.groupby("Kurum/Numune Sahibi")["İşlenen Numune Sayısı"].sum().sort_values(ascending=False)
            kisa_liste_tablosu("Musteri Bazli Islenen Analiz - Ilk 10", musteri, "Kurum / Numune Sahibi", 10)

        if all(c in df_pdf.columns for c in ["Yapılan Test", "İşlenen Numune Sayısı"]):
            testler = df_pdf.groupby("Yapılan Test")["İşlenen Numune Sayısı"].sum().sort_values(ascending=False)
            kisa_liste_tablosu("Calisilan Test Panelleri - Ilk 15", testler, "Yapilan Test", 15)

    except Exception:
        # Özet sayfasında sorun olursa PDF'in ana bölümleri yine üretilebilsin.
        pass

    try:
        return bytes(pdf.output())
    except Exception:
        return pdf.output(dest="S").encode("latin-1")

# --- ANA UYGULAMA ---
if st.session_state["giris_yapildi"]:
    st.markdown('<div class="ana-baslik-kutusu"><h1 class="ana-baslik-yazisi">DİAGEN Veteriner LAB Rapor Analiz Paneli</h1></div>', unsafe_allow_html=True)

    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.markdown('<p class="logo-alti-yazi">Veteriner Teşhis ve Analiz Laboratuvarı</p>', unsafe_allow_html=True)
        st.sidebar.divider()

    st.sidebar.markdown("### ⚙️ Görünüm Ayarları")
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi Seçeneği:", ["📈 Çubuk (Bar)", "🍕 Pasta (Ay Bazlı)"])
    secilen_renk = st.sidebar.selectbox("Grafik Renk Paleti:", ["Kurumsal Mavi", "Canlı Yeşil", "Sıcak Turuncu", "Renkli"])

    renk_ayarlari = {
        "Kurumsal Mavi": {"skala": "Blues", "liste": px.colors.qualitative.Pastel1},
        "Canlı Yeşil": {"skala": "Greens", "liste": px.colors.qualitative.Dark2},
        "Sıcak Turuncu": {"skala": "Oranges", "liste": px.colors.qualitative.Vivid},
        "Renkli": {"skala": "Viridis", "liste": px.colors.qualitative.Prism},
    }
    guncel_skala = renk_ayarlari[secilen_renk]["skala"]
    guncel_liste = renk_ayarlari[secilen_renk]["liste"]

    @st.cache_data(ttl=300)
    def veri_getir():
        try:
            sheet_url = "https://docs.google.com/spreadsheets/d/1709woL6PJjewZ2lMvxapYX60qvXG-obEYW3akJY62GI/edit?usp=sharing"
            csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")
            df = pd.read_csv(csv_url)

            df = df.dropna(how="all")
            df.columns = df.columns.str.replace(r"\xa0", " ", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()

            sutun_map = {}
            for col in df.columns:
                c_upper = normalize_text(col)
                if "ISLENEN" in c_upper:
                    sutun_map[col] = "İşlenen Numune Sayısı"
                elif "YAPILAN" in c_upper:
                    sutun_map[col] = "Yapılan Test"
                elif "FATURA" in c_upper and "TUTAR" in c_upper:
                    sutun_map[col] = "Fatura Tutarı"
                elif "TAHSILAT" in c_upper:
                    sutun_map[col] = "Tahsilat Durumu"
                elif "SEHIR" in c_upper:
                    sutun_map[col] = "Numunenin Geldiği Şehir"
                elif "KURUM" in c_upper or "SAHIBI" in c_upper:
                    sutun_map[col] = "Kurum/Numune Sahibi"
                elif "TEST" in c_upper and ("TARIH" in c_upper or "ZAMAN" in c_upper):
                    sutun_map[col] = "Test tarihi"
                elif "GELIS" in c_upper and ("ZAMAN" in c_upper or "TARIH" in c_upper):
                    sutun_map[col] = "Numune Geliş Zamanı"
                elif "GELEN" in c_upper and "NUMUNE" in c_upper:
                    sutun_map[col] = "Gelen Numune Sayısı"

            df.rename(columns=sutun_map, inplace=True)

            beklenen_sutunlar = ["Test tarihi", "Gelen Numune Sayısı", "İşlenen Numune Sayısı", "Kurum/Numune Sahibi"]
            eksikler = [s for s in beklenen_sutunlar if s not in df.columns]
            if eksikler:
                st.error(f"🚨 E-Tablonuzda şu başlıklar bulunamadı: **{', '.join(eksikler)}**")
                return pd.DataFrame()

            # Bosluk/ tire temizlikleri
            df.replace(r"^\s*$", np.nan, regex=True, inplace=True)
            df.replace(r"^-$", np.nan, regex=True, inplace=True)
            df.replace("nan", np.nan, inplace=True)
            df.replace("NaN", np.nan, inplace=True)

            # Birlesik satirlar icin once genel alanlari doldur
            sutunlar_ffill = ["Test tarihi", "Kurum/Numune Sahibi", "Numunenin Geldiği Şehir"]
            for col in sutunlar_ffill:
                if col in df.columns:
                    df[col] = df[col].ffill()

            # Numune gelis zamani da eger ana satirda tek kez yazilip alt test satirlarinda bos kaliyorsa doldurulsun
            if "Numune Geliş Zamanı" in df.columns:
                df["Numune Geliş Zamanı"] = df["Numune Geliş Zamanı"].ffill()

            if "Numunenin Geldiği Şehir" in df.columns:
                df["Numunenin Geldiği Şehir"] = df["Numunenin Geldiği Şehir"].astype(str).str.replace("i", "İ").str.upper().str.strip()
                df["Numunenin Geldiği Şehir"] = df["Numunenin Geldiği Şehir"].replace("NAN", "BİLİNMİYOR")

            if "Yapılan Test" in df.columns:
                df["Yapılan Test"] = df["Yapılan Test"].astype(str).str.replace("i", "İ").str.upper().str.strip()
                df["Yapılan Test"] = df["Yapılan Test"].replace("NAN", "BİLİNMEYEN TEST")

            df["Test tarihi"] = df["Test tarihi"].apply(tarih_saat_duzelt)

            if "Numune Geliş Zamanı" in df.columns:
                df["Numune Geliş Zamanı"] = df["Numune Geliş Zamanı"].apply(tarih_saat_duzelt)
            else:
                df["Numune Geliş Zamanı"] = pd.NaT

            df = df.dropna(subset=["Test tarihi"])

            df["Gelen Numune Sayısı"] = pd.to_numeric(df["Gelen Numune Sayısı"], errors="coerce").fillna(0)
            df["İşlenen Numune Sayısı"] = pd.to_numeric(df["İşlenen Numune Sayısı"], errors="coerce").fillna(0)

            # SLA/TAT hesaplari
            tat_sonuclar = df.apply(tat_hesapla, axis=1)
            df["TAT_Kategori"] = tat_sonuclar[0]
            df["TAT_Durum"] = tat_sonuclar[1]
            df["Fark_Gun"] = tat_sonuclar[2]
            df["Hedef_Gun"] = tat_sonuclar[3]

            df["Yıl"] = df["Test tarihi"].dt.year.astype(int).astype(str)
            df["Hafta Numarası"] = df["Test tarihi"].dt.isocalendar().week
            df["Hafta Metni"] = df["Hafta Numarası"].astype(str) + ". Hafta"

            ay_sozlugu = {
                1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
                7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
            }
            df["Ay"] = df["Test tarihi"].dt.month.map(ay_sozlugu)

            if "Fatura Tutarı" in df.columns:
                df["Fatura Tutarı"] = df["Fatura Tutarı"].apply(para_temizle)
            if "Tahsilat Durumu" in df.columns:
                df["Tahsilat Durumu"] = df["Tahsilat Durumu"].fillna("Belirtilmedi")

            return df

        except Exception as e:
            st.error(f"Beklenmeyen bir veri okuma hatası: {e}")
            return pd.DataFrame()

    df_ham = veri_getir()

    if not df_ham.empty:
        ay_sirasi = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

        st.sidebar.markdown("### 📅 Filtreler")
        mevcut_yillar = sorted(df_ham["Yıl"].unique().tolist(), reverse=True)
        secilen_yillar = st.sidebar.multiselect("Yılı Filtrele:", mevcut_yillar, default=mevcut_yillar)
        df_yilli = df_ham[df_ham["Yıl"].isin(secilen_yillar)] if secilen_yillar else df_ham

        gecerli_aylar = sorted([ay for ay in df_yilli["Ay"].unique() if ay in ay_sirasi], key=lambda x: ay_sirasi.index(x))
        secilen_aylar = st.sidebar.multiselect("Ayları Filtrele:", gecerli_aylar, default=gecerli_aylar)
        df = df_yilli[df_yilli["Ay"].isin(secilen_aylar)] if secilen_aylar else df_yilli

        st.sidebar.divider()
        st.sidebar.markdown("### 📄 Raporlama")
        if "hazir_pdf_verisi" not in st.session_state:
            st.session_state["hazir_pdf_verisi"] = None
            st.session_state["hazir_pdf_adi"] = None

        if st.sidebar.button("📊 PDF Raporu Hazırla", use_container_width=True):
            with st.spinner("PDF rapor hazırlanıyor..."):
                pdf_verisi = pdf_olustur(df)
            if pdf_verisi:
                st.session_state["hazir_pdf_verisi"] = pdf_verisi
                st.session_state["hazir_pdf_adi"] = f"Diagen_Analiz_Raporu_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            else:
                st.sidebar.error("PDF için 'fpdf' gereklidir. requirements.txt içine fpdf ekleyin.")

        if st.session_state.get("hazir_pdf_verisi"):
            st.sidebar.download_button(
                label="📥 Hazırlanan PDF Raporu İndir",
                data=st.session_state["hazir_pdf_verisi"],
                file_name=st.session_state.get("hazir_pdf_adi") or "Diagen_Analiz_Raporu.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.sidebar.divider()
        if st.sidebar.button("🔄 Verileri Yenile", use_container_width=True):
            veri_getir.clear()
            st.rerun()

        col_cikis, col_imza = st.sidebar.columns([1, 1])
        with col_cikis:
            st.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({"giris_yapildi": False}), use_container_width=True)
        with col_imza:
            st.markdown('<div class="imza-alani">AEY</div>', unsafe_allow_html=True)

        # --- ANA KPI'LAR ---
        m1, m2, m3 = st.columns(3)
        m1.metric("🐄 Gelen Numune Sayısı", f"{int(df['Gelen Numune Sayısı'].sum()):,.0f} Adet")
        m2.metric("🧪 İşlenen Test / Analiz Adedi", f"{int(df['İşlenen Numune Sayısı'].sum()):,.0f} Adet")
        m3.metric("🚜 Aktif Kurum / Müşteri", f"{df['Kurum/Numune Sahibi'].nunique()} Adet")

        st.markdown("<br>", unsafe_allow_html=True)

        f1, f2, f3 = st.columns(3)
        toplam_ciro = df["Fatura Tutarı"].sum() if "Fatura Tutarı" in df.columns else 0
        bekleyen_tahsilat = df[df["Tahsilat Durumu"].str.contains("Ödenmedi", case=False, na=False)]["Fatura Tutarı"].sum() if "Tahsilat Durumu" in df.columns and "Fatura Tutarı" in df.columns else 0
        sehir_sayisi = df["Numunenin Geldiği Şehir"].nunique() if "Numunenin Geldiği Şehir" in df.columns else 0

        f1.metric("🌍 Numune Gelen Şehir", f"{sehir_sayisi} Şehir")
        f2.metric("💰 Toplam Ciro (KDV Hariç)", f"₺ {toplam_ciro:,.2f}")
        f3.metric("⏳ Bekleyen Tahsilat", f"₺ {bekleyen_tahsilat:,.2f}")

        # --- SLA / TAT ANALIZI ---
        st.divider()
        st.subheader("🎯 Operasyonel Hedef (SLA/TAT) Analizi")
        st.info(
            "**SLA**: Belirlenen hedef süre içinde analiz sonuçlandırma performansıdır. "
            "**TAT**: Numunenin laboratuvara kabulünden testin sonuçlandırılmasına kadar geçen operasyonel süredir. "
            "Bu bölümdeki adetler satır sayısını değil, **İşlenen Numune Sayısı / analiz adedi** toplamını gösterir. Araştırma ibaresi geçen testler ayrı kategori olarak izlenir; hedef süresi belirsiz olduğu için başarı/gecikme oranına dahil edilmez."
        )

        tat_gecerli = df[df["TAT_Durum"].isin(["Hedef İçi", "Gecikmeli"])].copy()
        toplam_sla_is = tat_gecerli["İşlenen Numune Sayısı"].sum()
        hedef_ici_sla_is = tat_gecerli[tat_gecerli["TAT_Durum"] == "Hedef İçi"]["İşlenen Numune Sayısı"].sum()
        gecikmeli_sla_is = tat_gecerli[tat_gecerli["TAT_Durum"] == "Gecikmeli"]["İşlenen Numune Sayısı"].sum()
        hedef_tanimsiz_is = df[df["TAT_Durum"] == "Hedef Tanımsız"]["İşlenen Numune Sayısı"].sum()
        basari_orani = (hedef_ici_sla_is / toplam_sla_is * 100) if toplam_sla_is > 0 else 0

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("SLA Kapsamındaki Analiz", f"{int(toplam_sla_is):,.0f}")
        s2.metric("Hedef İçi Analiz", f"{int(hedef_ici_sla_is):,.0f}")
        s3.metric("Gecikmeli Analiz", f"{int(gecikmeli_sla_is):,.0f}")
        s4.metric("Başarı Oranı", f"%{basari_orani:.1f}")
        s5.metric("Araştırma / Hedef Tanımsız", f"{int(hedef_tanimsiz_is):,.0f}")

        if toplam_sla_is > 0:
            t1, t2 = st.columns(2)

            with t1:
                tat_ozet = tat_gecerli.groupby("TAT_Durum")["İşlenen Numune Sayısı"].sum().reset_index()
                tat_ozet.columns = ["Durum", "Adet"]
                fig_tat1 = px.pie(
                    tat_ozet,
                    values="Adet",
                    names="Durum",
                    hole=0.5,
                    title="Genel Hedef Uyum Performansı",
                    color="Durum",
                    color_discrete_map={"Hedef İçi": "#2ECC71", "Gecikmeli": "#E74C3C"},
                    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
                )
                fig_tat1.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_tat1, use_container_width=True)

            with t2:
                tum_kategoriler = [
                    "Moleküler Test (Hedef: 3 Gün)",
                    "Bakteriyolojik Test (Hedef: 5 Gün)",
                    "Serolojik Test (Hedef: 3 Gün)",
                ]
                tum_durumlar = ["Hedef İçi", "Gecikmeli"]

                kategori_ozet = (
                    tat_gecerli.groupby(["TAT_Kategori", "TAT_Durum"])["İşlenen Numune Sayısı"]
                    .sum()
                    .reset_index(name="Adet")
                )

                tam_index = pd.MultiIndex.from_product([tum_kategoriler, tum_durumlar], names=["TAT_Kategori", "TAT_Durum"])
                kategori_ozet = (
                    kategori_ozet.set_index(["TAT_Kategori", "TAT_Durum"])
                    .reindex(tam_index, fill_value=0)
                    .reset_index()
                )

                fig_tat2 = px.bar(
                    kategori_ozet,
                    x="TAT_Kategori",
                    y="Adet",
                    color="TAT_Durum",
                    title="Test Kategorilerine Göre Hedef Uyum Dağılımı",
                    barmode="group",
                    text_auto=".0f",
                    color_discrete_map={"Hedef İçi": "#2ECC71", "Gecikmeli": "#E74C3C"},
                    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
                )
                fig_tat2.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="")
                st.plotly_chart(fig_tat2, use_container_width=True)
        else:
            st.info("ℹ️ SLA/TAT hesabına giren geçerli analiz bulunmuyor. Numune Geliş Zamanı ve Test tarihi alanlarını kontrol edin.")

        # --- SLA KONTROL TABLOSU ---
        with st.expander("🔍 SLA Kontrol Tablosu / Hata Ayıklama", expanded=False):
            st.write("TAT Durum Dağılımı - işlenen analiz toplamı")
            durum_debug = df.groupby("TAT_Durum")["İşlenen Numune Sayısı"].sum().reset_index().sort_values("İşlenen Numune Sayısı", ascending=False)
            st.dataframe(durum_debug, use_container_width=True)

            st.write("TAT Kategori Dağılımı - işlenen analiz toplamı")
            kategori_debug = df.groupby("TAT_Kategori")["İşlenen Numune Sayısı"].sum().reset_index().sort_values("İşlenen Numune Sayısı", ascending=False)
            st.dataframe(kategori_debug, use_container_width=True)

            kolonlar = ["Yapılan Test", "Numune Geliş Zamanı", "Test tarihi", "İşlenen Numune Sayısı", "TAT_Kategori", "TAT_Durum", "Fark_Gun", "Hedef_Gun"]
            mevcut_kolonlar = [c for c in kolonlar if c in df.columns]
            st.dataframe(df[mevcut_kolonlar], use_container_width=True)

        # --- AYLIK CIRO ---
        if "Fatura Tutarı" in df.columns:
            st.markdown("<br><h5 style='text-align:center; font-weight: 800; color: var(--text-color);'>📅 Aylık Ciro Dağılımı</h5>", unsafe_allow_html=True)
            aylik_ciro = df.groupby("Ay")["Fatura Tutarı"].sum().reset_index()
            aylik_ciro["Ay_Sirasi"] = aylik_ciro["Ay"].apply(lambda x: ay_sirasi.index(x))
            aylik_ciro = aylik_ciro.sort_values("Ay_Sirasi")

            html_content = '<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 10px;">'
            for _, row in aylik_ciro.iterrows():
                html_content += f'<div class="mini-ciro-kutu"><div class="mini-ciro-ay">{row["Ay"]}</div><div class="mini-ciro-deger">₺ {row["Fatura Tutarı"]:,.2f}</div></div>'
            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)

        st.divider()

        # --- SEHIR VE TAHSILAT ---
        st.subheader("🌍 Şehir ve Tahsilat Dağılımı")
        lok1, lok2 = st.columns(2)

        with lok1:
            if "Numunenin Geldiği Şehir" in df.columns:
                sehir_dagilimi = df.groupby("Numunenin Geldiği Şehir")[["Gelen Numune Sayısı", "İşlenen Numune Sayısı"]].sum().reset_index()
                sehir_dagilimi = sehir_dagilimi.sort_values("İşlenen Numune Sayısı", ascending=False).head(10)
                sehir_melt = sehir_dagilimi.melt(
                    id_vars="Numunenin Geldiği Şehir",
                    value_vars=["Gelen Numune Sayısı", "İşlenen Numune Sayısı"],
                    var_name="Numune Türü",
                    value_name="Adet",
                )
                fig_sehir = px.bar(
                    sehir_melt,
                    x="Numunenin Geldiği Şehir",
                    y="Adet",
                    color="Numune Türü",
                    barmode="group",
                    title="Şehir Bazlı Operasyon Hacmi (İlk 10)",
                    text_auto=".0f",
                    color_discrete_sequence=guncel_liste,
                    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
                )
                fig_sehir.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""))
                st.plotly_chart(fig_sehir, use_container_width=True)

        with lok2:
            if "Tahsilat Durumu" in df.columns and "Fatura Tutarı" in df.columns:
                tahsilat_ozet = df.groupby("Tahsilat Durumu")["Fatura Tutarı"].sum().reset_index()
                fig_tahsilat = px.pie(
                    tahsilat_ozet,
                    values="Fatura Tutarı",
                    names="Tahsilat Durumu",
                    hole=0.5,
                    title="Finansal Tahsilat Durumu",
                    color_discrete_sequence=guncel_liste,
                    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
                )
                fig_tahsilat.update_traces(textinfo="percent+label")
                fig_tahsilat.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_tahsilat, use_container_width=True)

        st.divider()

        # --- MUSTERI PERFORMANS ---
        st.subheader("🏢 Müşteri Performans Analizleri")
        if "Kurum/Numune Sahibi" in df.columns:
            m_gelen = df.groupby("Kurum/Numune Sahibi")["Gelen Numune Sayısı"].sum().reset_index().sort_values("Gelen Numune Sayısı", ascending=False).head(15)
            fig1 = px.bar(
                m_gelen,
                x="Gelen Numune Sayısı",
                y="Kurum/Numune Sahibi",
                orientation="h",
                title="Müşteri Bazlı Numune Girişi (İlk 15)",
                color="Gelen Numune Sayısı",
                color_continuous_scale=guncel_skala,
                text_auto=".0f",
                template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
            )
            fig1.update_layout(yaxis={"categoryorder": "total ascending"}, height=550, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig1, use_container_width=True)

            m_islenen = df.groupby("Kurum/Numune Sahibi")["İşlenen Numune Sayısı"].sum().reset_index().sort_values("İşlenen Numune Sayısı", ascending=False).head(15)
            fig2 = px.bar(
                m_islenen,
                x="İşlenen Numune Sayısı",
                y="Kurum/Numune Sahibi",
                orientation="h",
                title="Müşterilere Göre İşlenen Test / Analiz Adedi (İlk 15)",
                color="İşlenen Numune Sayısı",
                color_continuous_scale=guncel_skala,
                text_auto=".0f",
                template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
            )
            fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=550, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # --- DONEMSEL YOGUNLUK ---
        st.subheader("⏳ Dönemsel Yoğunluk Analizi")
        if grafik_tarzi == "📈 Çubuk (Bar)":
            haftalik_veri = df.groupby(["Ay", "Hafta Metni"])["İşlenen Numune Sayısı"].sum().reset_index()
            aktif_ay_sirasi = [ay for ay in ay_sirasi if ay in secilen_aylar]
            fig_zaman = px.bar(
                haftalik_veri,
                x="Ay",
                y="İşlenen Numune Sayısı",
                color="Hafta Metni",
                barmode="group",
                title="Aylık/Haftalık İşlem Hacmi",
                text_auto=".0f",
                category_orders={"Ay": aktif_ay_sirasi},
                color_discrete_sequence=guncel_liste,
                template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
            )
            fig_zaman.update_layout(height=500, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_zaman, use_container_width=True)
        else:
            secili_aylar_liste = sorted(df["Ay"].unique().tolist(), key=lambda x: ay_sirasi.index(x))
            num_cols = 2
            num_rows = (len(secili_aylar_liste) + num_cols - 1) // num_cols
            fig_donut = make_subplots(rows=num_rows, cols=num_cols, specs=[[{"type": "domain"}] * num_cols] * num_rows, subplot_titles=secili_aylar_liste)
            for i, ay in enumerate(secili_aylar_liste):
                ay_verisi = df[df["Ay"] == ay].groupby("Hafta Metni")["İşlenen Numune Sayısı"].sum().reset_index()
                fig_donut.add_trace(go.Pie(labels=ay_verisi["Hafta Metni"], values=ay_verisi["İşlenen Numune Sayısı"], name=ay, hole=0.4), row=(i // num_cols) + 1, col=(i % num_cols) + 1)
            fig_donut.update_layout(height=400 * num_rows, colorway=guncel_liste, template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        # --- TEST DAGILIMI ---
        if "Yapılan Test" in df.columns:
            test_dagilimi = df.groupby("Yapılan Test")["İşlenen Numune Sayısı"].sum().reset_index().sort_values("İşlenen Numune Sayısı", ascending=False)
            grafik_boyu = max(600, len(test_dagilimi) * 35)
            fig_test = px.funnel(
                test_dagilimi,
                x="İşlenen Numune Sayısı",
                y="Yapılan Test",
                title="Çalışılan Tüm Test Panelleri",
                color_discrete_sequence=guncel_liste,
                template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
            )
            fig_test.update_layout(height=grafik_boyu, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_test, use_container_width=True)

        st.caption(f"⚙️ Son Veri Senkronizasyonu: {datetime.datetime.now().strftime('%H:%M:%S')} (Yenile butonuna basarak güncelleyebilirsiniz)")

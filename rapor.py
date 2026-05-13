import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
import os
import re
import numpy as np
import time

# Resmi tatil takvimi için
try:
    import holidays
    tr_holidays = holidays.Turkey(years=range(2020, 2030))
    tat_tatiller = [d for d in tr_holidays.keys()]
except ImportError:
    tat_tatiller = []

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- 🎨 KURUMSAL LACİVERT TASARIM VE AKILLI RENK CSS ---
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
    
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span { 
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
        div[data-testid="stSidebarUserContent"] .stRadio {
            border: 2px solid #3b82f6 !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state: st.session_state['giris_yapildi'] = False

if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", width=250)
        st.title("🔒 Güvenli Giriş")
        with st.form("login_form"):
            kullanici_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Sisteme Giriş Yap"):
                if kullanici_adi == "admin" and sifre == "lab2026":
                    st.session_state['giris_yapildi'] = True
                    st.rerun()
                else: st.error("❌ Bilgiler hatalı!")

# --- SLA ZAMAN HESAPLAMA MOTORU ---
def adjust_start_time(dt):
    if pd.isna(dt): return dt
    if dt.weekday() >= 5:
        days_to_add = 7 - dt.weekday() 
        dt = dt + pd.Timedelta(days=days_to_add)
        dt = dt.replace(hour=8, minute=0, second=0)
    else:
        if dt.hour >= 18:
            dt = dt + pd.Timedelta(days=1)
            if dt.weekday() == 5:
                dt = dt + pd.Timedelta(days=2)
            dt = dt.replace(hour=8, minute=0, second=0)
        elif dt.hour < 8:
            dt = dt.replace(hour=8, minute=0, second=0)
    return dt

def tat_hesapla(row):
    test_adi = str(row.get('Yapılan Test', '')).upper()
    test_adi = test_adi.replace('İ', 'I').replace('Ç', 'C').replace('Ş', 'S').replace('Ü', 'U').replace('Ö', 'O').replace('Ğ', 'G')
    
    if "PCR" in test_adi:
        kategori = "Moleküler Test (Hedef: 3 Gün)"
        hedef = 3
    elif any(x in test_adi for x in ["EKIM", "ANTIBIYOGRAM", "TOTAL BAKTERI"]):
        kategori = "Bakteriyolojik Test (Hedef: 5 Gün)"
        hedef = 5
    else:
        kategori = "Serolojik Test (Hedef: 3 Gün)"
        hedef = 3

    gelis = row.get('Numune Geliş Zamanı')
    test = row.get('Test tarihi')
    
    if pd.isna(gelis) or pd.isna(test):
        return pd.Series([kategori, "Zaman Verisi Eksik", None])
        
    if gelis < pd.to_datetime('2026-05-06'):
        return pd.Series([kategori, "6 Mayıs Öncesi (Kapsam Dışı)", None])
        
    gelis_adj = adjust_start_time(gelis)
    
    try:
        gun_farki = np.busday_count(gelis_adj.date(), test.date(), holidays=tat_tatiller)
        if gun_farki < 0: gun_farki = 0
        durum = "Hedef İçi" if gun_farki <= hedef else "Gecikmeli"
        return pd.Series([kategori, durum, gun_farki])
    except:
        return pd.Series([kategori, "Hatalı Tarih", None])

# --- GELİŞMİŞ TASARIMLI PDF MOTORU ---
def pdf_olustur(df_filtreli):
    try:
        from fpdf import FPDF
    except ImportError:
        return None 

    def tr_temizle(text):
        return str(text).translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))

    def pdf_kategori_bul(test_adi):
        t = str(test_adi).upper()
        t = t.replace('İ', 'I').replace('Ç', 'C').replace('Ş', 'S').replace('Ü', 'U').replace('Ö', 'O').replace('Ğ', 'G')
        
        if "PCR" in t: 
            return "Yapilan PCR Testleri"
        elif any(x in t for x in ["EKIM", "ANTIBIYOGRAM", "TOTAL BAKTERI"]): 
            return "Bakteriyolojik Testler"
        elif any(x in t for x in ["SAT", "BRUCELLA", "ROSE BENGAL"]): 
            return "Brucella Serolojik Testleri"
        elif any(x in t for x in ["TB FERON", "FERON", "MBOVIS", "M. BOVIS", "M.BOVIS", "BOVIS"]): 
            return "Tuberkuloz Testleri"
        elif "ARASTIRMA" in t: 
            return "Arastirma Testleri"
        else: 
            return "Diger Serolojik Analizler"

    grup_aciklamalari = {
        "Yapilan PCR Testleri": "(Tum PCR icerikli analizler)",
        "Bakteriyolojik Testler": "(Bakteriyolojik Ekim, Antibiyogram, Total Bakteri vb.)",
        "Brucella Serolojik Testleri": "(SAT, Brucella Ab, Rose Bengal vb.)",
        "Tuberkuloz Testleri": "(TB Feron, M. Bovis Ab vb.)",
        "Arastirma Testleri": "(Arastirma icerikli analizler)",
        "Diger Serolojik Analizler": "(Yukari gruplar disindaki diger tum testler)"
    }

    df_pdf = df_filtreli.copy()
    if 'Yapılan Test' in df_pdf.columns:
        df_pdf['PDF_Grup'] = df_pdf['Yapılan Test'].apply(pdf_kategori_bul)
    else:
        df_pdf['PDF_Grup'] = "Diger Serolojik Analizler"

    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_fill_color(26, 74, 124) 
    pdf.set_text_color(255, 255, 255) 
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, tr_temizle("DIAGEN LABORATUVARI ANALIZ RAPORU"), ln=True, align='C', fill=True)
    
    pdf.set_text_color(100, 100, 100) 
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, tr_temizle(f"Rapor Uretim Tarihi: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align='R')
    pdf.ln(5)

    if 'TAT_Durum' in df_pdf.columns:
        tat_gecerli = df_pdf[df_pdf['TAT_Durum'].isin(['Hedef İçi', 'Gecikmeli'])]
        if not tat_gecerli.empty:
            basari = (len(tat_gecerli[tat_gecerli['TAT_Durum'] == 'Hedef İçi']) / len(tat_gecerli)) * 100
            pdf.set_fill_color(220, 255, 220)
            pdf.set_text_color(0, 100, 0)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, tr_temizle(f" HEDEF SURE (SLA) UYUM BASARISI (6 Mayis Sonrasi): %{basari:.1f}"), ln=True, fill=True, align='C')
            pdf.ln(5)

    pdf.set_text_color(0, 0, 0) 
    pdf.set_fill_color(230, 240, 250) 
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_temizle(" DONEMSEL GENEL TOPLAM HAVA DURUMU"), ln=True, fill=True)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 10, tr_temizle(f" Toplam Gelen Numune : {int(df_pdf['Gelen Numune Sayısı'].sum())} Adet"), border=1)
    pdf.cell(95, 10, tr_temizle(f" Toplam Islenen Numune: {int(df_pdf['İşlenen Numune Sayısı'].sum())} Adet"), border=1, ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(200, 200, 200) 
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(50, 8, tr_temizle("Test Grubu"), border=1, fill=True)
    pdf.cell(115, 8, tr_temizle("Grup Icerigi"), border=1, fill=True)
    pdf.cell(25, 8, tr_temizle("Toplam (Adet)"), border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font("Arial", '', 9)
    if 'Yapılan Test' in df_pdf.columns:
        genel_grup = df_pdf.groupby('PDF_Grup')['İşlenen Numune Sayısı'].sum().reset_index()
        for _, satir in genel_grup.iterrows():
            if satir['İşlenen Numune Sayısı'] > 0:
                pdf.cell(50, 8, tr_temizle(satir['PDF_Grup']), border=1)
                pdf.cell(115, 8, tr_temizle(grup_aciklamalari.get(satir['PDF_Grup'], "")), border=1)
                pdf.cell(25, 8, str(int(satir['İşlenen Numune Sayısı'])), border=1, align='C')
                pdf.ln()
    pdf.ln(10)

    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_temizle(" AYLIK DETAYLI NUMUNE VE TEST ANALIZI"), ln=True, fill=True)
    pdf.ln(3)

    ay_sirasi = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    mevcut_aylar = df_pdf['Ay'].unique()
    sirali_aylar = sorted(mevcut_aylar, key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)

    for ay in sirali_aylar:
        df_ay = df_pdf[df_pdf['Ay'] == ay]
        gelen_toplam = int(df_ay['Gelen Numune Sayısı'].sum())
        islenen_toplam = int(df_ay['İşlenen Numune Sayısı'].sum())
        
        if islenen_toplam == 0 and gelen_toplam == 0:
            continue

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(190, 8, tr_temizle(f" [{ay.upper()} AYI]  |  Gelen: {gelen_toplam} Numune  -  Islenen: {islenen_toplam} Test"), border=1, ln=True, fill=True)
        
        pdf.set_font("Arial", '', 9)
        if 'Yapılan Test' in df_ay.columns:
            aylik_grup = df_ay.groupby('PDF_Grup')['İşlenen Numune Sayısı'].sum().reset_index()
            for _, satir in aylik_grup.iterrows():
                if satir['İşlenen Numune Sayısı'] > 0:
                    pdf.cell(50, 6, tr_temizle(satir['PDF_Grup']), border='L,B')
                    pdf.cell(115, 6, tr_temizle(grup_aciklamalari.get(satir['PDF_Grup'], "")), border='B')
                    pdf.cell(25, 6, str(int(satir['İşlenen Numune Sayısı'])), border='R,B', align='C')
                    pdf.ln()
        pdf.ln(5)

    try:
        return bytes(pdf.output()) 
    except Exception:
        return pdf.output(dest='S').encode('latin-1')

# --- SİSTEM UYGULAMA KODLARI ---
if st.session_state['giris_yapildi']:
    st.markdown('<div class="ana-baslik-kutusu"><h1 class="ana-baslik-yazisi">DİAGEN Veteriner LAB Rapor Analiz Paneli</h1></div>', unsafe_allow_html=True)

    if os.path.exists("logo.png"): 
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.markdown('<p class="logo-alti-yazi">Veteriner Teşhis ve Analiz Laboratuvarı</p>', unsafe_allow_html=True)
        st.sidebar.divider()
    
    st.sidebar.markdown("### ⚙️ Görünüm Ayarları")
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi Seçeneği:", ["📈 Çubuk (Bar)", "🍕 Pasta (Ay Bazlı)"])
    secilen

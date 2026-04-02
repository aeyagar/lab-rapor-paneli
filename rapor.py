import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
import os
import re

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

# --- PDF ÜRETME MOTORU (SADECE RAPORA ÖZEL VERİ İŞLEME) ---
def pdf_olustur(df_filtreli):
    try:
        from fpdf import FPDF
    except ImportError:
        return None # Eğer fpdf yüklü değilse uyarı verdirmek için

    # FPDF standart fontları Türkçe desteklemediği için harfleri dönüştüren güvenlik kilidi
    def tr_temizle(text):
        return str(text).translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))

    # Sizin belirlediğiniz özel PDF gruplama mantığı
    def pdf_kategori_bul(test_adi):
        t = str(test_adi).upper()
        if "PCR" in t: 
            return "Yapilan PCR Testleri"
        elif any(x in t for x in ["EKIM", "EKİM", "ANTIBIYOGRAM", "ANTİBİYOGRAM", "TOTAL BAKTERI", "TOTAL BAKTERİ"]): 
            return "Bakteriyolojik Testler"
        elif any(x in t for x in ["SAT", "BRUCELLA", "ROSE BENGAL"]): 
            return "Brucella Serolojik Testleri"
        elif any(x in t for x in ["TB FERON", "MBOVIS", "M. BOVIS", "M.BOVIS"]): 
            return "Tuberkuloz Testleri"
        elif "ARASTIRMA" in t or "ARAŞTIRMA" in t: 
            return "Arastirma Testleri"
        else: 
            return "Diger Serolojik Analizler"

    # UI etkilenmesin diye dataframe'in kopyası üzerinden çalışıyoruz
    df_pdf = df_filtreli.copy()
    if 'Yapılan Test' in df_pdf.columns:
        df_pdf['PDF_Grup'] = df_pdf['Yapılan Test'].apply(pdf_kategori_bul)
    else:
        df_pdf['PDF_Grup'] = "Diger Serolojik Analizler"

    pdf = FPDF()
    pdf.add_page()
    
    # Başlık Alanı
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, tr_temizle("DIAGEN LABORATUVARI ANALIZ RAPORU"), ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, tr_temizle(f"Rapor TARIHI: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(8)

    # 1. YILLIK GENEL ÖZET
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_temizle("--- DONEMSEL GENEL TOPLAM ---"), ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 7, tr_temizle(f"* Toplam Gelen Numune Sayisi : {int(df_pdf['Gelen Numune Sayısı'].sum())} Adet"), ln=True)
    pdf.cell(0, 7, tr_temizle(f"* Toplam Islenen Numune Sayisi: {int(df_pdf['İşlenen Numune Sayısı'].sum())} Adet"), ln=True)
    pdf.ln(4)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, tr_temizle("Islem Gruplari Dagilimi:"), ln=True)
    pdf.set_font("Arial", '', 11)
    if 'Yapılan Test' in df_pdf.columns:
        genel_grup = df_pdf.groupby('PDF_Grup')['İşlenen Numune Sayısı'].sum().reset_index()
        for _, satir in genel_grup.iterrows():
            if satir['İşlenen Numune Sayısı'] > 0:
                pdf.cell(0, 7, tr_temizle(f"  > {satir['PDF_Grup']}: {int(satir['İşlenen Numune Sayısı'])} Adet"), ln=True)
    pdf.line(10, pdf.get_y()+5, 200, pdf.get_y()+5)
    pdf.ln(10)

    # 2. AYLIK DETAYLI DÖKÜM
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_temizle("--- AYLIK DETAYLI ANALIZ ---"), ln=True)
    pdf.ln(3)

    ay_sirasi = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    mevcut_aylar = df_pdf['Ay'].unique()
    sirali_aylar = sorted(mevcut_aylar, key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)

    for ay in sirali_aylar:
        df_ay = df_pdf[df_pdf['Ay'] == ay]
        gelen_toplam = int(df_ay['Gelen Numune Sayısı'].sum())
        islenen_toplam = int(df_ay['İşlenen Numune Sayısı'].sum())
        
        if islenen_toplam == 0 and gelen_toplam == 0:
            continue # Verisi olmayan ayları atla

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, tr_temizle(f"[{ay.upper()} AYI]"), ln=True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, tr_temizle(f"Gelen Numune: {gelen_toplam} | Islenen Numune: {islenen_toplam}"), ln=True)
        
        if 'Yapılan Test' in df_ay.columns:
            aylik_grup = df_ay.groupby('PDF_Grup')['İşlenen Numune Sayısı'].sum().reset_index()
            for _, satir in aylik_grup.iterrows():
                if satir['İşlenen Numune Sayısı'] > 0:
                    pdf.cell(0, 6, tr_temizle(f"  - {satir['PDF_Grup']}: {int(satir['İşlenen Numune Sayısı'])} Adet"), ln=True)
        pdf.ln(5)

    try:
        return bytes(pdf.output()) # fpdf2 için
    except Exception:
        return pdf.output(dest='S').encode('latin-1') # fpdf(legacy) için


if st.session_state['giris_yapildi']:
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
        "Renkli": {"skala": "Viridis", "liste": px.colors.qualitative.Prism}
    }
    guncel_skala = renk_ayarlari[secilen_renk]["skala"]
    guncel_liste = renk_ayarlari[secilen_renk]["liste"]

    @st.cache_data(ttl=15)
    def veri_getir():
        try:
            sheet_url = "https://docs.google.com/spreadsheets/d/1709woL6PJjewZ2lMvxapYX60qvXG-obEYW3akJY62GI/edit?usp=sharing"
            csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
            df = pd.read_csv(csv_url)
            
            df = df.dropna(how='all')
            df.columns = df.columns.str.replace(r'\xa0', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
            
            sutun_map = {}
            for col in df.columns:
                c_upper = col.upper().replace('İ', 'I') 
                if "IŞLENEN" in c_upper or "ISLENEN" in c_upper: sutun_map[col] = 'İşlenen Numune Sayısı'
                elif "YAPILAN" in c_upper: sutun_map[col] = 'Yapılan Test'
                elif "FATURA" in c_upper and "TUTAR" in c_upper: sutun_map[col] = 'Fatura Tutarı'
                elif "TAHSILAT" in c_upper: sutun_map[col] = 'Tahsilat Durumu'
                elif "ŞEHIR" in c_upper or "SEHIR" in c_upper: sutun_map[col] = 'Numunenin Geldiği Şehir'
                elif "KURUM" in c_upper or "SAHIBI" in c_upper: sutun_map[col] = 'Kurum/Numune Sahibi'
            df.rename(columns=sutun_map, inplace=True)

            beklenen_sutunlar = ['Test tarihi', 'Gelen Numune Sayısı', 'İşlenen Numune Sayısı', 'Kurum/Numune Sahibi']
            eksikler = [s for s in beklenen_sutunlar if s not in df.columns]
            if eksikler:
                st.error(f"🚨 E-Tablonuzda şu başlıklar bulunamadı: **{', '.join(eksikler)}**")
                return pd.DataFrame()

            sutunlar_ffill = ['Test tarihi', 'Kurum/Numune Sahibi', 'Numunenin Geldiği Şehir']
            for col in sutunlar_ffill:
                if col in df.columns:
                    df[col] = df[col].ffill()

            if 'Numunenin Geldiği Şehir' in df.columns:
                df['Numunenin Geldiği Şehir'] = df['Numunenin Geldiği Şehir'].astype(str).str.replace('i', 'İ').str.upper().str.strip()
                df['Numunenin Geldiği Şehir'] = df['Numunenin Geldiği Şehir'].replace('NAN', 'BİLİNMİYOR')

            if 'Yapılan Test' in df.columns:
                df['Yapılan Test'] = df['Yapılan Test'].astype(str).str.replace('i', 'İ').str.upper().str.strip()
                df['Yapılan Test'] = df['Yapılan Test'].replace('NAN', 'BİLİNMEYEN TEST')

            df['Test tarihi'] = pd.to_datetime(df['Test tarihi'], errors='coerce', dayfirst=True)
            df = df.dropna(subset=['Test tarihi'])
            
            df['Yıl'] = df['Test tarihi'].dt.year.astype(int).astype(str)
            df['Hafta Numarası'] = df['Test tarihi'].dt.isocalendar().week
            df['Hafta Metni'] = df['Hafta Numarası'].astype(str) + ". Hafta"
            
            ay_sozlugu = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 
                          7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Ay'] = df['Test tarihi'].dt.month.map(ay_sozlugu)
            
            df['Gelen Numune Sayısı'] = pd.to_numeric(df['Gelen Numune Sayısı'], errors='coerce').fillna(0)
            df['İşlenen Numune Sayısı'] = pd.to_numeric(df['İşlenen Numune Sayısı'], errors='coerce').fillna(0)
            
            def para_temizle(deger):
                try:
                    deger = str(deger)
                    deger = re.sub(r'[^\d.,]', '', deger)
                    if not deger: return 0.0
                    if '.' in deger and ',' in deger:
                        if deger.rfind(',') > deger.rfind('.'):
                            deger = deger.replace('.', '').replace(',', '.')
                        else:
                            deger = deger.replace(',', '')
                    elif ',' in deger:
                        deger = deger.replace(',', '.')
                    return float(deger)
                except:
                    return 0.0

            if 'Fatura Tutarı' in df.columns:
                df['Fatura Tutarı'] = df['Fatura Tutarı'].apply(para_temizle)
            
            if 'Tahsilat Durumu' in df.columns: df['Tahsilat Durumu'] = df['Tahsilat Durumu'].fillna('Belirtilmedi')
            
            return df
        except Exception as e:
            st.error(f"Beklenmeyen bir veri okuma hatası: {e}")
            return pd.DataFrame()

    df_ham = veri_getir()

    if not df_ham.empty:
        ay_sirasi = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        
        st.sidebar.markdown("### 📅 Filtreler")
        
        mevcut_yillar = sorted(df_ham['Yıl'].unique().tolist(), reverse=True)
        secilen_yillar = st.sidebar.multiselect("Yılı Filtrele:", mevcut_yillar, default=mevcut_yillar)
        df_yilli = df_ham[df_ham['Yıl'].isin(secilen_yillar)] if secilen_yillar else df_ham
        
        gecerli_aylar = sorted([ay for ay in df_yilli['Ay'].unique() if ay in ay_sirasi], key=lambda x: ay_sirasi.index(x))
        secilen_aylar = st.sidebar.multiselect("Ayları Filtrele:", gecerli_aylar, default=gecerli_aylar)
        
        df = df_yilli[df_yilli['Ay'].isin(secilen_aylar)] if secilen_aylar else df_yilli
        
        st.sidebar.divider()

        # --- YENİ: PDF RAPOR BUTONU ---
        st.sidebar.markdown("### 📄 Raporlama")
        pdf_verisi = pdf_olustur(df)
        if pdf_verisi:
            st.sidebar.download_button(
                label="📥 Ozet Raporu PDF Indir",
                data=pdf_verisi,
                file_name=f"Diagen_Analiz_Raporu_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.sidebar.error("PDF için 'pip install fpdf' gereklidir.")

        st.sidebar.divider()
        if st.sidebar.button("🔄 Verileri Yenile", use_container_width=True):
            veri_getir.clear()
            st.rerun()
            
        col_cikis, col_imza = st.sidebar.columns([1,1])
        with col_cikis: st.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}), use_container_width=True)
        with col_imza: st.markdown('<div class="imza-alani">AEY</div>', unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("🐄 Gelen Numune Sayısı", f"{int(df['Gelen Numune Sayısı'].sum()):,.0f} Adet")
        m2.metric("🧪 İşlenen Test Adedi", f"{int(df['İşlenen Numune Sayısı'].sum()):,.0f} Adet")
        m3.metric("🚜 Aktif Kurum / Müşteri", f"{df['Kurum/Numune Sahibi'].nunique()} Adet")

        st.markdown("<br>", unsafe_allow_html=True)

        f1, f2, f3 = st.columns(3)
        toplam_ciro = df['Fatura Tutarı'].sum() if 'Fatura Tutarı' in df.columns else 0
        bekleyen_tahsilat = df[df['Tahsilat Durumu'].str.contains('Ödenmedi', case=False, na=False)]['Fatura Tutarı'].sum() if 'Tahsilat Durumu' in df.columns and 'Fatura Tutarı' in df.columns else 0
        sehir_sayisi = df['Numunenin Geldiği Şehir'].nunique() if 'Numunenin Geldiği Şehir' in df.columns else 0
        
        f1.metric("🌍 Numune Gelen Şehir", f"{sehir_sayisi} Şehir")
        f2.metric("💰 Toplam Ciro (KDV Hariç)", f"₺ {toplam_ciro:,.2f}")
        f3.metric("⏳ Bekleyen Tahsilat", f"₺ {bekleyen_tahsilat:,.2f}")

        if 'Fatura Tutarı' in df.columns:
            st.markdown("<br><h5 style='text-align:center; font-weight: 800; color: var(--text-color);'>📅 Aylık Ciro Dağılımı</h5>", unsafe_allow_html=True)
            
            aylik_ciro = df.groupby('Ay')['Fatura Tutarı'].sum().reset_index()
            aylik_ciro['Ay_Sirasi'] = aylik_ciro['Ay'].apply(lambda x: ay_sirasi.index(x))
            aylik_ciro = aylik_ciro.sort_values('Ay_Sirasi')
            
            html_content = '<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 10px;">'
            for _, row in aylik_ciro.iterrows():
                html_content += f'<div class="mini-ciro-kutu"><div class="mini-ciro-ay">{row["Ay"]}</div><div class="mini-ciro-deger">₺ {row["Fatura Tutarı"]:,.2f}</div></div>'
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)

        st.divider()

        st.subheader("🌍 Şehir ve Tahsilat Dağılımı")
        lok1, lok2 = st.columns(2)
        
        with lok1:
            if 'Numunenin Geldiği Şehir' in df.columns:
                sehir_dagilimi = df.groupby('Numunenin Geldiği Şehir')[['Gelen Numune Sayısı', 'İşlenen Numune Sayısı']].sum().reset_index()
                sehir_dagilimi = sehir_dagilimi.sort_values('İşlenen Numune Sayısı', ascending=False).head(10)
                
                sehir_melt = sehir_dagilimi.melt(id_vars='Numunenin Geldiği Şehir', 
                                                 value_vars=['Gelen Numune Sayısı', 'İşlenen Numune Sayısı'], 
                                                 var_name='Numune Türü', value_name='Adet')
                
                fig_sehir = px.bar(sehir_melt, x='Numunenin Geldiği Şehir', y='Adet', color='Numune Türü', barmode='group',
                                   title='Şehir Bazlı Operasyon Hacmi (İlk 10)', text_auto='.0f',
                                   color_discrete_sequence=guncel_liste, template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
                
                fig_sehir.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""))
                st.plotly_chart(fig_sehir, use_container_width=True)

        with lok2:
            if 'Tahsilat Durumu' in df.columns and 'Fatura Tutarı' in df.columns:
                tahsilat_ozet = df.groupby('Tahsilat Durumu')['Fatura Tutarı'].sum().reset_index()
                fig_tahsilat = px.pie(tahsilat_ozet, values='Fatura Tutarı', names='Tahsilat Durumu', hole=0.5,
                                      title='Finansal Tahsilat Durumu', color_discrete_sequence=guncel_liste,
                                      template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
                fig_tahsilat.update_traces(textinfo='percent+label')
                fig_tahsilat.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_tahsilat, use_container_width=True)

        st.divider()

        st.subheader("🏢 Müşteri Performans Analizleri")
        if 'Kurum/Numune Sahibi' in df.columns:
            m_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index().sort_values('Gelen Numune Sayısı', ascending=False).head(15)
            fig1 = px.bar(m_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', 
                          title='Müşteri Bazlı Numune Girişi (İlk 15)', color='Gelen Numune Sayısı', 
                          color_continuous_scale=guncel_skala, text_auto='.0f', template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            fig1.update_layout(yaxis={'categoryorder':'total ascending'}, height=550, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)

            m_islenen = df.groupby('Kurum/Numune Sahibi')['İşlenen Numune Sayısı'].sum().reset_index().sort_values('İşlenen Numune Sayısı', ascending=False).head(15)
            fig2 = px.bar(m_islenen, x='İşlenen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', 
                          title='Müşterilere Göre İşlenen Test Adedi (İlk 15)', color='İşlenen Numune Sayısı', 
                          color_continuous_scale=guncel_skala, text_auto='.0f', template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            fig2.update_layout(yaxis={'categoryorder':'total ascending'}, height=550, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("⏳ Dönemsel Yoğunluk Analizi")
        if grafik_tarzi == "📈 Çubuk (Bar)":
            haftalik_veri = df.groupby(['Ay', 'Hafta Metni'])['İşlenen Numune Sayısı'].sum().reset_index()
            aktif_ay_sirasi = [ay for ay in ay_sirasi if ay in secilen_aylar]
            
            fig_zaman = px.bar(haftalik_veri, x='Ay', y='İşlenen Numune Sayısı', color='Hafta Metni', 
                               barmode='group', title='Aylık/Haftalık İşlem Hacmi', text_auto='.0f',
                               category_orders={'Ay': aktif_ay_sirasi}, color_discrete_sequence=guncel_liste,
                               template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            fig_zaman.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_zaman, use_container_width=True)
        else:
            secili_aylar_liste = sorted(df['Ay'].unique().tolist(), key=lambda x: ay_sirasi.index(x))
            num_cols = 2 
            num_rows = (len(secili_aylar_liste) + num_cols - 1) // num_cols
            fig_donut = make_subplots(rows=num_rows, cols=num_cols, specs=[[{'type':'domain'}]*num_cols]*num_rows, subplot_titles=secili_aylar_liste)
            for i, ay in enumerate(secili_aylar_liste):
                ay_verisi = df[df['Ay'] == ay].groupby('Hafta Metni')['İşlenen Numune Sayısı'].sum().reset_index()
                fig_donut.add_trace(go.Pie(labels=ay_verisi['Hafta Metni'], values=ay_verisi['İşlenen Numune Sayısı'], name=ay, hole=0.4), row=(i//num_cols)+1, col=(i%num_cols)+1)
            fig_donut.update_layout(height=400*num_rows, colorway=guncel_liste, template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        if 'Yapılan Test' in df.columns:
            test_dagilimi = df.groupby('Yapılan Test')['İşlenen Numune Sayısı'].sum().reset_index().sort_values('İşlenen Numune Sayısı', ascending=False)
            grafik_boyu = max(600, len(test_dagilimi) * 35)
            fig_test = px.funnel(test_dagilimi, x='İşlenen Numune Sayısı', y='Yapılan Test', 
                                 title='Çalışılan Tüm Test Panelleri', color_discrete_sequence=guncel_liste,
                                 template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly")
            fig_test.update_layout(height=grafik_boyu, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_test, use_container_width=True)

        st.caption(f"⚙️ Son Veri Senkronizasyonu: {datetime.datetime.now().strftime('%H:%M:%S')} (Yenile butonuna basarak güncelleyebilirsiniz)")

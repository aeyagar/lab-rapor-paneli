import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- 🎨 KURUMSAL TASARIM VE ÇERÇEVELER (CSS) ---
st.markdown("""
<style>
    /* Ana Başlık Kutusu */
    .ana-baslik-kutusu {
        background-color: #ffffff;
        border: 4px solid #2e956e;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }
    .ana-baslik-yazisi {
        color: #1e2125;
        font-size: 38px !important;
        font-weight: 900 !important;
        margin: 0;
    }
    /* Metrik Kare Balonlar */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 3px solid #2e956e !important;
        padding: 20px !important;
        border-radius: 20px !important;
        box-shadow: 6px 6px 20px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #1e2125 !important;
        font-weight: 800 !important;
        font-size: 1.3rem !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: #2e956e !important;
        font-weight: 900 !important;
        font-size: 2.5rem !important;
    }
    /* Sol Menü Kutucukları */
    div[data-testid="stSidebarUserContent"] .stMultiSelect, 
    div[data-testid="stSidebarUserContent"] .stSelectbox,
    div[data-testid="stSidebarUserContent"] .stRadio {
        background-color: #ffffff !important;
        border: 2px solid #2e956e !important;
        padding: 15px !important;
        border-radius: 12px !important;
        margin-bottom: 15px !important;
    }
    [data-testid="stSidebar"] label p {
        font-weight: 900 !important;
        color: #1e2125 !important;
    }
    /* İmza Alanı Stil */
    .imza-alani {
        text-align: right;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        color: #1e2125;
        padding-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- GİRİŞ EKRANI ---
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

# --- ANA UYGULAMA ---
if st.session_state['giris_yapildi']:
    
    # Üst Başlık
    st.markdown('<div class="ana-baslik-kutusu"><h1 class="ana-baslik-yazisi">DİAGEN Veteriner LAB Rapor Analiz Paneli</h1></div>', unsafe_allow_html=True)

    # Sidebar Logo ve Alt Yazısı
    if os.path.exists("logo.png"): 
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.markdown("<p style='text-align: center; font-weight: 800; color: #2e956e;'>Veteriner Teşhis ve Analiz Laboratuvarı</p>", unsafe_allow_html=True)
        st.sidebar.divider()
    
    # Görünüm Ayarları
    st.sidebar.markdown("### ⚙️ Görünüm Ayarları")
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi Seçeneği:", ["📈 Çubuk (Bar)", "🍕 Pasta (Ay Bazlı)"])
    secilen_renk = st.sidebar.selectbox("Grafik Renk Paleti:", ["Canlı Yeşil", "Kurumsal Mavi", "Sıcak Turuncu", "Renkli"])
    
    renk_ayarlari = {
        "Canlı Yeşil": {"skala": "Greens", "liste": px.colors.qualitative.Dark2},
        "Kurumsal Mavi": {"skala": "Blues", "liste": px.colors.qualitative.Pastel1},
        "Sıcak Turuncu": {"skala": "Oranges", "liste": px.colors.qualitative.Vivid},
        "Renkli": {"skala": "Viridis", "liste": px.colors.qualitative.Prism}
    }
    guncel_skala = renk_ayarlari[secilen_renk]["skala"]
    guncel_liste = renk_ayarlari[secilen_renk]["liste"]

    # Veri Yükleme
    @st.cache_data(ttl=60)
    def veri_getir():
        try:
            df = pd.read_excel("veri.xlsx")
            df.columns = df.columns.str.strip()
            df['Test tarihi'] = pd.to_datetime(df['Test tarihi'], errors='coerce')
            df['Hafta Numarası'] = df['Test tarihi'].dt.isocalendar().week
            df['Hafta Metni'] = df['Hafta Numarası'].astype(str) + ". Hafta"
            ay_sozlugu = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 
                          7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Ay'] = df['Test tarihi'].dt.month.map(ay_sozlugu)
            df['Gelen Numune Sayısı'] = pd.to_numeric(df['Gelen Numune Sayısı'], errors='coerce').fillna(0)
            df['Numune adedi (işlenen numune)'] = pd.to_numeric(df['Numune adedi (işlenen numune)'], errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Hata: {e}"); return pd.DataFrame()

    df_ham = veri_getir()

    if not df_ham.empty:
        ay_sirasi = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        st.sidebar.markdown("### 📅 Filtreler")
        mevcut_aylar = sorted(df_ham['Ay'].dropna().unique().tolist(), key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)
        secilen_aylar = st.sidebar.multiselect("Görmek İstediğiniz Aylar:", mevcut_aylar, default=mevcut_aylar)
        df = df_ham[df_ham['Ay'].isin(secilen_aylar)] if secilen_aylar else df_ham
        
        # Sol Alt Çıkış ve İmza
        st.sidebar.divider()
        col_cikis, col_imza = st.sidebar.columns([1,1])
        with col_cikis:
            st.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))
        with col_imza:
            st.markdown('<div class="imza-alani">AEY</div>', unsafe_allow_html=True)

        # Metrikler
        m1, m2, m3 = st.columns(3)
        m1.metric("🐄 Toplam Gelen Numune", f"{int(df['Gelen Numune Sayısı'].sum()):,.0f} Adet")
        m2.metric("🧪 İşlenen Test Adedi", f"{int(df['Numune adedi (işlenen numune)'].sum()):,.0f} Adet")
        m3.metric("🚜 Hizmet Verilen Kurum", f"{df['Kurum/Numune Sahibi'].nunique()} Müşteri")

        st.divider()

        # Grafikler
        m_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index().sort_values('Gelen Numune Sayısı', ascending=False).head(15)
        fig1 = px.bar(m_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', 
                      title='Müşteri Bazlı Numune Girişi (İlk 15)', color='Gelen Numune Sayısı', 
                      color_continuous_scale=guncel_skala, text_auto='.0f')
        fig1.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        m_islenen = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().reset_index().sort_values('Numune adedi (işlenen numune)', ascending=False).head(15)
        fig2 = px.bar(m_islenen, x='Numune adedi (işlenen numune)', y='Kurum/Numune Sahibi', orientation='h', 
                      title='Müşterilere Göre İşlenen Test Adedi (İlk 15)', color='Numune adedi (işlenen numune)', 
                      color_continuous_scale=guncel_skala, text_auto='.0f')
        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("⏳ Dönemsel Yoğunluk Analizi")
        if grafik_tarzi == "📈 Çubuk (Bar)":
            haftalik_veri = df.groupby(['Ay', 'Hafta Metni'])['Numune adedi (işlenen numune)'].sum().reset_index()
            fig_zaman = px.bar(haftalik_veri, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni', 
                               barmode='group', title='Aylık/Haftalık İşlem Hacmi', text_auto='.0f',
                               category_orders={'Ay': ay_sirasi}, color_discrete_sequence=guncel_liste)
            fig_zaman.update_layout(height=550)
            st.plotly_chart(fig_zaman, use_container_width=True)
        else:
            secili_aylar_liste = sorted(df['Ay'].unique().tolist(), key=lambda x: ay_sirasi.index(x))
            num_cols = 2 
            num_rows = (len(secili_aylar_liste) + num_cols - 1) // num_cols
            fig_donut = make_subplots(rows=num_rows, cols=num_cols, specs=[[{'type':'domain'}]*num_cols]*num_rows, subplot_titles=secili_aylar_liste)
            for i, ay in enumerate(secili_aylar_liste):
                ay_verisi = df[df['Ay'] == ay].groupby('Hafta Metni')['Numune adedi (işlenen numune)'].sum().reset_index()
                fig_donut.add_trace(go.Pie(labels=ay_verisi['Hafta Metni'], values=ay_verisi['Numune adedi (işlenen numune)'], name=ay, hole=0.4), row=(i//num_cols)+1, col=(i%num_cols)+1)
            fig_donut.update_layout(height=450*num_rows, colorway=guncel_liste)
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        test_dagilimi = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index().sort_values('Numune adedi (işlenen numune)', ascending=False).head(20)
        fig_test = px.funnel(test_dagilimi, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)', 
                             title='En Çok Çalışılan Test Panelleri (İlk 20)', color_discrete_sequence=guncel_liste)
        fig_test.update_layout(height=800)
        st.plotly_chart(fig_test, use_container_width=True)

        st.caption(f"⚙️ Son Güncelleme: {datetime.datetime.now().strftime('%H:%M:%S')}")

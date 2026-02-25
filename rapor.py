import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- 🎨 YÜKSEK OKUNABİLİRLİK VE RENK DÜZELTME (CSS) ---
st.markdown("""
<style>
    /* Sol Menü (Sidebar) Yazı Rengi Düzeltme */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        color: #1e2125 !important;
    }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #1e2125 !important; /* Yazıları koyu antrasit yapar */
        font-weight: 500;
    }

    /* Metrik Kutuları */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 2px solid #2e956e;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
        text-align: center;
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
            if st.form_submit_button("Giriş Yap"):
                if kullanici_adi == "admin" and sifre == "lab2026":
                    st.session_state['giris_yapildi'] = True
                    st.rerun()
                else: st.error("❌ Hatalı bilgi!")

# --- ANA UYGULAMA ---
if st.session_state['giris_yapildi']:
    if os.path.exists("logo.png"): st.sidebar.image("logo.png", use_container_width=True)
    
    st.sidebar.header("🎨 Görünüm Ayarları")
    secilen_renk = st.sidebar.selectbox("Renk Paleti", ["Canlı Yeşil", "Kurumsal Mavi", "Pastel", "Renkli"])
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi", ["📈 Çubuk (Bar)", "🍕 Pasta (Haftalık Dağılım)"])
    
    renk_map = {"Pastel": px.colors.qualitative.Pastel, "Kurumsal Mavi": px.colors.sequential.Blues_r,
                "Canlı Yeşil": px.colors.sequential.Greens_r, "Renkli": px.colors.qualitative.Prism}
    renk_paleti = renk_map[secilen_renk]

    st.sidebar.divider()
    st.sidebar.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))

    st.title("🐄 DİAGEN Veteriner LAB Rapor İzleme Paneli")

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
        mevcut_aylar = sorted(df_ham['Ay'].dropna().unique().tolist(), key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)
        secilen_aylar = st.sidebar.multiselect("Ayları Seçin:", mevcut_aylar, default=mevcut_aylar)
        df = df_ham[df_ham['Ay'].isin(secilen_aylar)] if secilen_aylar else df_ham
        
        # --- METRİKLER ---
        m1, m2, m3 = st.columns(3)
        m1.metric("🐄 Toplam Gelen Numune", f"{int(df['Gelen Numune Sayısı'].sum()):,.0f} Adet")
        m2.metric("🧪 İşlenen Test Adedi", f"{int(df['Numune adedi (işlenen numune)'].sum()):,.0f} Adet")
        m3.metric("🚜 Hizmet Verilen Kurum", f"{df['Kurum/Numune Sahibi'].nunique()} Müşteri")

        st.divider()

        # --- MÜŞTERİ ANALİZLERİ (BÜYÜK VE TAM GENİŞLİK) ---
        m_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index().sort_values('Gelen Numune Sayısı', ascending=False).head(15)
        fig1 = px.bar(m_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', 
                      title='Müşterilere Göre Gelen Numune Sayısı (İlk 15)', color='Gelen Numune Sayısı', 
                      color_continuous_scale='Greens', text_auto='.0f')
        fig1.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        fig1.update_traces(textfont_size=14, textposition="outside", hovertemplate="<b>%{y}</b><br>Miktar: %{x}<extra></extra>")
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        m_islenen = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().reset_index().sort_values('Numune adedi (işlenen numune)', ascending=False).head(15)
        fig2 = px.bar(m_islenen, x='Numune adedi (işlenen numune)', y='Kurum/Numune Sahibi', orientation='h', 
                      title='Müşterilere Göre İşlenen Test Adedi (İlk 15)', color='Numune adedi (işlenen numune)', 
                      color_continuous_scale='Teal', text_auto='.0f')
        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        fig2.update_traces(textfont_size=14, textposition="outside", hovertemplate="<b>%{y}</b><br>İşlem: %{x}<extra></extra>")
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # --- ZAMAN ANALİZİ ---
        st.subheader("⏳ Dönemsel Analiz")
        if grafik_tarzi == "📈 Çubuk (Bar)":
            haftalik_veri = df.groupby(['Ay', 'Hafta Metni'])['Numune adedi (işlenen numune)'].sum().reset_index()
            fig_zaman = px.bar(haftalik_veri, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni', 
                               barmode='group', title='Aylık ve Haftalık Yoğunluk', text_auto='.0f',
                               category_orders={'Ay': ay_sirasi}, color_discrete_sequence=renk_paleti)
            fig_zaman.update_layout(height=500)
            fig_zaman.update_traces(textfont_size=12, textposition="outside")
            st.plotly_chart(fig_zaman, use_container_width=True)
        else:
            secili_aylar_liste = sorted(df['Ay'].unique().tolist(), key=lambda x: ay_sirasi.index(x))
            num_cols = 2 # Pasta grafikleri yan yana 2'li olsun (Daha büyük görünmesi için)
            num_rows = (len(secili_aylar_liste) + num_cols - 1) // num_cols
            fig_donut = make_subplots(rows=num_rows, cols=num_cols, specs=[[{'type':'domain'}]*num_cols]*num_rows, subplot_titles=secili_aylar_liste)
            for i, ay in enumerate(secili_aylar_liste):
                ay_verisi = df[df['Ay'] == ay].groupby('Hafta Metni')['Numune adedi (işlenen numune)'].sum().reset_index()
                fig_donut.add_trace(go.Pie(labels=ay_verisi['Hafta Metni'], values=ay_verisi['Numune adedi (işlenen numune)'], name=ay, hole=0.4), row=(i//num_cols)+1, col=(i%num_cols)+1)
            fig_donut.update_layout(height=400*num_rows, showlegend=True)
            fig_donut.update_traces(textinfo='percent+value', hovertemplate="<b>%{label}</b><br>Miktar: %{value}<br>Oran: %{percent}<extra></extra>")
            st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        # --- TEST DAĞILIMI (FUNNEL) ---
        test_dagilimi = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index().sort_values('Numune adedi (işlenen numune)', ascending=False).head(20)
        fig_test = px.funnel(test_dagilimi, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)', title='En Çok Çalışılan Test Panelleri (İlk 20)')
        fig_test.update_layout(height=700)
        fig_test.update_traces(textfont_size=14, hovertemplate="<b>%{y}</b><br>Miktar: %{x}<extra></extra>")
        st.plotly_chart(fig_test, use_container_width=True)

        st.caption(f"⚙️ Veri Kaynağı: veri.xlsx | Güncelleme: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

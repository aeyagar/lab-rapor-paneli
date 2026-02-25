import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- GİRİŞ EKRANI ---
if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=250)
            
        st.title("🔒 Güvenli Giriş")
        st.markdown("DİAGEN Veteriner Laboratuvarı İzleme Paneli")
        
        with st.form("login_form"):
            kullanici_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            giris_butonu = st.form_submit_button("Giriş Yap")
            
            if giris_butonu:
                if kullanici_adi == "admin" and sifre == "lab2026":
                    st.session_state['giris_yapildi'] = True
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı!")

# --- ANA UYGULAMA ---
if st.session_state['giris_yapildi']:
    
    # --- AKILLI KARŞILAMA ---
    saat = datetime.datetime.now().hour
    if saat < 12:
        karsilama = "🌅 Günaydın"
    elif saat < 18:
        karsilama = "☀️ İyi Günler"
    else:
        karsilama = "🌙 İyi Akşamlar"
    
    # --- SOL MENÜ ---
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.divider()
    
    if os.path.exists("ruminant.png"):
        st.sidebar.image("ruminant.png", use_container_width=True, caption="Ruminant Sağlığı Merkezi")
        st.sidebar.divider()

    st.sidebar.success(f"{karsilama}, Admin! 👋")
    
    st.sidebar.header("🎨 Görünüm Ayarları")
    secilen_tema = st.sidebar.selectbox("Grafik Renk Teması", ["Kurumsal (Mavi & Turkuaz)", "Sıcak (Kırmızı & Turuncu)", "Doğa (Yeşil Tonları)", "Canlı (Pastel & Karışık)"])
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi Tarzı", ["Çubuk (Bar)", "Çizgi (Line)"])
    
    if secilen_tema == "Kurumsal (Mavi & Turkuaz)":
        renk_paleti_1, renk_paleti_2 = 'Blues', 'Teal'
        zaman_renkleri = px.colors.qualitative.Set1
    elif secilen_tema == "Sıcak (Kırmızı & Turuncu)":
        renk_paleti_1, renk_paleti_2 = 'Reds', 'Oranges'
        zaman_renkleri = px.colors.qualitative.Vivid
    elif secilen_tema == "Doğa (Yeşil Tonları)":
        renk_paleti_1, renk_paleti_2 = 'Greens', 'YlGn'
        zaman_renkleri = px.colors.qualitative.Pastel
    else:
        renk_paleti_1, renk_paleti_2 = 'Plasma', 'Viridis'
        zaman_renkleri = px.colors.qualitative.Plotly

    st.sidebar.divider()
    st.sidebar.button("🚪 Sistemden Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))

    st.title("🐄 DİAGEN Veteriner LAB Rapor Paneli")

    # --- VERİ YÜKLEME ---
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
            st.error(f"SİSTEMİN GERÇEK HATASI: {e}")
            return pd.DataFrame()

    df_ham = veri_getir()

    if not df_ham.empty:
        ay_sirasi = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        
        # --- FİLTRELER ---
        st.sidebar.header("🔍 Veri Filtreleri")
        mevcut_aylar = sorted(df_ham['Ay'].dropna().unique().tolist(), key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)
        mevcut_haftalar = sorted(df_ham['Hafta Numarası'].dropna().unique().tolist())
        hafta_sirasi = [f"{h}. Hafta" for h in mevcut_haftalar]
        
        secilen_aylar = st.sidebar.multiselect("Ayları Filtrele:", mevcut_aylar, default=mevcut_aylar)
        secilen_haftalar = st.sidebar.multiselect("Haftaları Filtrele:", hafta_sirasi, default=hafta_sirasi)
        
        df = df_ham.copy()
        if secilen_aylar:
            df = df[df['Ay'].isin(secilen_aylar)]
        if secilen_haftalar:
            df = df[df['Hafta Metni'].isin(secilen_haftalar)]
        
        if df.empty:
            st.warning("Seçili filtrelere uygun veri bulunamadı!")
        else:
            # --- KPI METRİKLER ---
            c1, c2, c3 = st.columns(3)
            c1.metric("🐄 Toplam Gelen Numune", f"{int(df['Gelen Numune Sayısı'].sum()):,.0f} Adet")
            c2.metric("🧪 İşlenen Test Adedi", f"{int(df['Numune adedi (işlenen numune)'].sum()):,.0f} Adet")
            c3.metric("🚜 Hizmet Verilen Kurum", df['Kurum/Numune Sahibi'].nunique())

            st.divider()

            # --- ANALİZ GRAFİKLERİ ---
            k1, k2 = st.columns(2)
            with k1:
                kurum_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index().sort_values(by='Gelen Numune Sayısı', ascending=False).head(10)
                fig_gelen = px.bar(kurum_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', title='En Çok Numune Gönderenler', text_auto=True, color='Gelen Numune Sayısı', color_continuous_scale=renk_paleti_1)
                fig_gelen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig_gelen, use_container_width=True)
                
            with k2:
                test_ozet = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index().sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
                fig_testler = px.funnel(test_ozet, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)', title='En Çok Çalışılan Testler')
                st.plotly_chart(fig_testler, use_container_width=True)

            st.divider()

            # --- ZAMAN ÇİZELGESİ (GENİŞ GÖRÜNÜM) ---
            st.subheader("⏳ Aylara Göre Haftalık Test Yoğunluğu")
            haftalik_aylik = df.groupby(['Ay', 'Hafta Metni'])['Numune adedi (işlenen numune)'].sum().reset_index()
            siralama_ayari = {'Ay': ay_sirasi, 'Hafta Metni': hafta_sirasi}
            
            if grafik_tarzi == "Çubuk (Bar)":
                fig_zaman = px.bar(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni', barmode='group', text_auto=True, category_orders=siralama_ayari, color_discrete_sequence=zaman_renkleri)
            else:
                fig_zaman = px.line(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni', markers=True, category_orders=siralama_ayari, color_discrete_sequence=zaman_renkleri)
                
            st.plotly_chart(fig_zaman, use_container_width=True)

            st.caption(f"⚙️ Veriler 'veri.xlsx' dosyasından alınmaktadır. Son Güncelleme: {datetime.datetime.now().strftime('%H:%M:%S')}")

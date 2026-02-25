import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- SAYFA AYARLARI ---
# Tarayıcı sekmesindeki ikonu inek (🐄) yaptık
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- GİRİŞ EKRANI ---
if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=250)
            
        st.title("🔒 Sisteme Giriş")
        st.markdown("Lütfen DİAGEN Veteriner Laboratuvarı paneline erişmek için bilgilerinizi girin.")
        
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
    
    # --- SOL MENÜ ---
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.divider()
    
    # Yan menüye isteğe bağlı Ruminant figürü/fotoğrafı ekleme alanı
    if os.path.exists("ruminant.png"):
        st.sidebar.image("ruminant.png", use_container_width=True, caption="Ruminant Sağlığı Merkezi")
        st.sidebar.divider()
        
    st.sidebar.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))
    st.sidebar.divider()

    # BAŞLIKLAR VE İKONLAR RUMİNANT TEMASINA UYARLANDI
    st.title("🐄 DİAGEN Veteriner LAB Rapor İzleme Paneli")
    st.markdown("Büyükbaş ve küçükbaş numune akışını, kurum performanslarını ve test yoğunluklarını analiz edin.")

    # --- VERİ YÜKLEME VE TEMİZLEME ---
    @st.cache_data(ttl=60)
    def veri_getir():
        try:
            df = pd.read_excel("veri.xlsx")
            df.columns = df.columns.str.strip()
            
            df['Test tarihi'] = pd.to_datetime(df['Test tarihi'], errors='coerce')
            df['Hafta Numarası'] = df['Test tarihi'].dt.isocalendar().week
            
            ay_sozlugu = {
                1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 
                5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos', 
                9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
            }
            df['Ay'] = df['Test tarihi

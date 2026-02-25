import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# ==========================================
# 🌌 YENİ NESİL KOYU MOD VE BUZLU CAM CSS (GLASSMORPHISM)
# ==========================================
st.markdown("""
<style>
    /* Göz yormayan derin Slate (Koyu Lacivert/Antrasit) arka plan */
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }
    
    /* Buzlu Cam (Glassmorphism) Metrik Kartları */
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        border-radius: 16px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: rgba(46, 149, 110, 0.5); /* Fareyle gelince DİAGEN yeşili parlama */
    }
    
    /* Metrik Sayıları (Canlı Nane Yeşili) */
    div[data-testid="stMetricValue"] {
        color: #10b981;
        font-weight: 800;
        text-shadow: 0px 0px 10px rgba(16, 185, 129, 0.2);
    }
    
    /* Metrik Başlıkları (Açık Gri) */
    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
        font-size: 1.1rem;
    }

    /* Şık Butonlar */
    .stButton>button {
        border-radius: 30px;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
        border: none;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0px 0px 15px rgba(16, 185, 129, 0.4);
        color: white;
    }
    
    /* Sol Menü Arka Planı */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Başlıkların Rengi */
    h1, h2, h3 {
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)
# ==========================================

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- GİRİŞ EKRANI ---
if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True) # Boşluk
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

    st.sidebar.header(f"{karsilama}, Admin!")
    st.sidebar.markdown("İşte laboratuvarın son durumu.")
    st.sidebar.divider()
    
    st.sidebar.button("🚪 Sistemden Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))
    st.sidebar.divider()

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
            
            ay_sozlugu = {
                1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 
                5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos', 
                9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
            }
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
        
        mevcut_aylar = df_ham['Ay'].dropna().unique().tolist()
        mevcut_aylar = sorted(mevcut_aylar, key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)
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
            # --- TEMEL METRİKLER (KPI) ---
            toplam_gelen = int(df['Gelen Numune Sayısı'].sum())
            toplam_islenen = int(df['Numune adedi (işlenen numune)'].sum())
            toplam_kurum = df['Kurum/Numune Sahibi'].nunique()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🐄 Gelen Numune Sayısı", f"{toplam_gelen:,.0f}")
            c2.metric("🧪 İşlenen Test Adedi", f"{toplam_islenen:,.0f}")
            c3.metric("🚜 Hizmet Verilen Kurum", f"{toplam_kurum}")

            st.divider()

            # --- GRAFİKLER İÇİN KOYU MOD ŞABLONU ---
            koyu_tema = "plotly_dark"
            renk_paleti_1 = px.colors.sequential.Teal
            renk_paleti_2 = px.colors.sequential.Mint

            # --- KURUM ANALİZLERİ ---
            st.subheader("🏢 Performans ve Yoğunluk Analizi")
            k1, k2 = st.columns(2)
            
            with k1:
                kurum_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index()
                kurum_gelen = kurum_gelen.sort_values(by='Gelen Numune Sayısı', ascending=False).head(10)
                fig_gelen = px.bar(kurum_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi', orientation='h', 
                                   title='En Çok Numune Gönderenler', text_auto=True, color='Gelen Numune Sayısı', color_continuous_scale=renk_paleti_1, template=koyu_tema)
                fig_gelen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_gelen, use_container_width=True)
                
            with k2:
                haftalik_aylik = df.groupby(['Ay', 'Hafta Metni'])['Numune adedi (işlenen numune)'].sum().reset_index()
                siralama_ayari = {'Ay': ay_sirasi, 'Hafta Metni': hafta_sirasi}
                fig_zaman = px.area(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                                    title='Aylara Göre Test Yoğunluğu (Alan)', category_orders=siralama_ayari, template=koyu_tema, color_discrete_sequence=px.colors.qualitative.Set2)
                fig_zaman.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_zaman, use_container_width=True)

            # --- HASTALIK/TEST PANELLERİ ---
            st.divider()
            st.subheader("🧬 Test Panelleri ve Laboratuvar Canlı Akışı")
            
            z1, z2 = st.columns([2, 1]) # Sol taraf daha geniş
            
            with z1:
                test_ozet = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index()
                test_ozet = test_ozet.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
                fig_testler = px.funnel(test_ozet, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)',
                                        title='En Çok Çalışılan Hastalık Panelleri', template=koyu_tema)
                fig_testler.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_testler, use_container_width=True)

            with z2:
                # --- YARATICI FİKİR: CANLI RADAR ---
                st.markdown("### 📡 Son Düşen İşlemler")
                st.caption("Excel dosyasına işlenen en güncel 5 hareket.")
                
                # Tarihe göre en yeni 5 işlemi sıralama
                son_islemler = df_ham.sort_values(by='Test tarihi', ascending=False).head(5)
                
                for index, row in son_islemler.iterrows():
                    # Streamlit info kutularıyla şık bir besleme (feed) görünümü
                    kurum = str(row['Kurum/Numune Sahibi'])[:15] + "..." if len(str(row['Kurum/Numune Sahibi'])) > 15 else str(row['Kurum/Numune Sahibi'])
                    test = str(row['Test (MARKA ve PARAMETRE)'])
                    tarih = row['Test tarihi'].strftime("%d.%m.%Y") if pd.notnull(row['Test tarihi']) else "-"
                    
                    st.info(f"📅 **{tarih}**\n\n🏢 {kurum}\n\n🧪 **Test:** {test}")

            # Footer
            st.divider()
            st.caption("⚙️ Sistem Durumu: Çevrimiçi | Veriler 'veri.xlsx' dosyasından anlık beslenmektedir.")

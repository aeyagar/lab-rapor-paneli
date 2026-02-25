import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🐄", layout="wide")

# ==========================================
# 🎨 ÖZEL CSS İLE GÖRÜNÜMÜ GÜÇLENDİRME
# ==========================================
st.markdown("""
<style>
    /* Ana sayfa arka planını çok açık, göz yormayan bir medikal gri yapalım */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Üstteki Metrik (Sayı) Kutularını kartvizit gibi şık bir kutu içine alalım */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.03);
        transition: transform 0.2s;
    }
    /* Kutuların üzerine fareyle gelince hafifçe yukarı kalkma efekti */
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 2px 6px 15px rgba(0,0,0,0.08);
    }
    
    /* Metrik sayılarının rengi (Canlı Kurumsal Yeşil) */
    div[data-testid="stMetricValue"] {
        color: #2e956e;
        font-weight: bold;
    }

    /* Tüm Butonların (Giriş, Çıkış vs.) Görünümü */
    .stButton>button {
        border-radius: 25px; /* Yuvarlak köşeler */
        background-color: #2e956e;
        color: white;
        border: none;
        padding: 10px 24px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        font-weight: bold;
        transition: all 0.3s ease;
    }
    /* Butonun üzerine fareyle gelince renginin koyulaşması */
    .stButton>button:hover {
        background-color: #1b6649;
        box-shadow: 0px 6px 10px rgba(0,0,0,0.2);
        color: #ffffff;
    }
    
    /* Sol Menü (Sidebar) Ayarları */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 2px solid #f1f3f5;
    }
    
    /* Uyarı ve Bilgi Kutularının köşe ayarları */
    .stAlert {
        border-radius: 10px;
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
    
    # --- SOL MENÜ GÖRSELLERİ ---
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.divider()
    
    if os.path.exists("ruminant.png"):
        st.sidebar.image("ruminant.png", use_container_width=True, caption="Ruminant Sağlığı Merkezi")
        st.sidebar.divider()

    # --- KULLANICI GÖRÜNÜM AYARLARI ---
    st.sidebar.header("🎨 Grafik Renk Ayarları")
    secilen_tema = st.sidebar.selectbox("Grafik Renk Teması", ["Kurumsal (Mavi & Turkuaz)", "Sıcak (Kırmızı & Turuncu)", "Doğa (Yeşil Tonları)", "Canlı (Pastel & Karışık)"])
    grafik_tarzi = st.sidebar.radio("Zaman Çizelgesi Tarzı", ["Çubuk (Bar)", "Çizgi (Line)", "Alan (Area)"])
    
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
    
    st.sidebar.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))
    st.sidebar.divider()

    st.title("🐄 DİAGEN Veteriner LAB Rapor İzleme Paneli")
    st.markdown("Büyükbaş ve küçükbaş numune akışını, kurum performanslarını ve test yoğunluklarını analiz edin.")

    # --- VERİ YÜKLEME ---
    @st.cache_data(ttl=60)
    def veri_getir():
        try:
            df = pd.read_excel("veri.xlsx")
            df.columns = df.columns.str.strip()
            
            df['Test tarihi'] = pd.to_datetime(df['Test tarihi'], errors='coerce')
            
            # ISO Calendar Mantığı (Hatasız Yıl/Hafta)
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
        
        # --- FİLTRELER (AY VE HAFTA) ---
        st.sidebar.header("🔍 Veri Filtreleri")
        
        mevcut_aylar = df_ham['Ay'].dropna().unique().tolist()
        mevcut_aylar = sorted(mevcut_aylar, key=lambda x: ay_sirasi.index(x) if x in ay_sirasi else 99)
        
        mevcut_haftalar = sorted(df_ham['Hafta Numarası'].dropna().unique().tolist())
        hafta_sirasi = [f"{h}. Hafta" for h in mevcut_haftalar]
        
        secilen_aylar = st.sidebar.multiselect("İncelenecek Ayları Seçin:", mevcut_aylar, default=mevcut_aylar)
        secilen_haftalar = st.sidebar.multiselect("İncelenecek Haftaları Seçin:", hafta_sirasi, default=hafta_sirasi)
        
        df = df_ham.copy()
        if secilen_aylar:
            df = df[df['Ay'].isin(secilen_aylar)]
        if secilen_haftalar:
            df = df[df['Hafta Metni'].isin(secilen_haftalar)]
        
        if df.empty:
            st.warning("Seçili filtrelere uygun veri bulunamadı! Lütfen sol menüden farklı aylar veya haftalar seçin.")
        else:
            # --- OTOMATİK İÇGÖRÜLER ---
            st.subheader("💡 GENEL VERİLER")
            
            en_yogun_ay = df.groupby('Ay')['Numune adedi (işlenen numune)'].sum().idxmax()
            en_cok_is_yapan_kurum = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().idxmax()
            en_populer_test = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().idxmax()
            
            i1, i2, i3 = st.columns(3)
            i1.info(f"📅 **En Yoğun Ay (Seçili Veride):**\n\n {en_yogun_ay} ayında testler zirve yaptı.")
            i2.success(f"🏢 **En Çok Numune Gönderen:**\n\n {en_cok_is_yapan_kurum}")
            i3.warning(f"🔬 **En Popüler Test:**\n\n {en_populer_test} paneli en çok çalışılan işlem oldu.")
            
            st.divider()

            # --- TEMEL METRİKLER (KPI) ---
            toplam_gelen = int(df['Gelen Numune Sayısı'].sum())
            toplam_islenen = int(df['Numune adedi (işlenen numune)'].sum())
            toplam_kurum = df['Kurum/Numune Sahibi'].nunique()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🐄 Toplam Gelen Numune", f"{toplam_gelen:,.0f} Adet")
            c2.metric("🧪 İşlenen Test Adedi", f"{toplam_islenen:,.0f} Adet")
            c3.metric("🚜 Hizmet Verilen Çiftlik/Kurum", f"{toplam_kurum} Adet")

            st.divider()

            # --- KURUM ANALİZLERİ ---
            st.subheader("🏢 Kurum ve Çiftlik Performans Analizi")
            k1, k2 = st.columns(2)
            
            with k1:
                kurum_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index()
                kurum_gelen = kurum_gelen[kurum_gelen['Gelen Numune Sayısı'] > 0]
                kurum_gelen = kurum_gelen.sort_values(by='Gelen Numune Sayısı', ascending=False).head(10)
                
                fig_gelen = px.bar(kurum_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi',
                                   orientation='h', title='En Çok Numune GÖNDEREN Kurumlar',
                                   text_auto=True, color='Gelen Numune Sayısı', color_continuous_scale=renk_paleti_1)
                fig_gelen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_gelen, use_container_width=True)
                
            with k2:
                kurum_islenen = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().reset_index()
                kurum_islenen = kurum_islenen[kurum_islenen['Numune adedi (işlenen numune)'] > 0]
                kurum_islenen = kurum_islenen.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
                
                fig_islenen = px.bar(kurum_islenen, x='Numune adedi (işlenen numune)', y='Kurum/Numune Sahibi',
                                     orientation='h', title='En Çok Test İŞLENEN Kurumlar',
                                     text_auto=True, color='Numune adedi (işlenen numune)', color_continuous_scale=renk_paleti_2)
                fig_islenen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_islenen, use_container_width=True)

            st.divider()

            # --- ZAMAN ÇİZELGESİ VE YOĞUNLUK ANALİZİ ---
            st.subheader("⏳ Aylara Göre Haftalık Test Yoğunluğu")
            
            haftalik_aylik = df.groupby(['Ay', 'Hafta Metni'])['Numune adedi (işlenen numune)'].sum().reset_index()
            siralama_ayari = {'Ay': ay_sirasi, 'Hafta Metni': hafta_sirasi}
            
            if grafik_tarzi == "Çubuk (Bar)":
                fig_zaman = px.bar(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                                   text_auto=True, barmode='group', category_orders=siralama_ayari,
                                   color_discrete_sequence=zaman_renkleri)
            elif grafik_tarzi == "Çizgi (Line)":
                fig_zaman = px.line(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                                    markers=True, category_orders=siralama_ayari,
                                    color_discrete_sequence=zaman_renkleri)
            else:
                fig_zaman = px.area(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                                    category_orders=siralama_ayari,
                                    color_discrete_sequence=zaman_renkleri)
                
            fig_zaman.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_zaman, use_container_width=True)
            
            st.divider()
            
            # --- HASTALIK / TEST PANELLERİ ---
            st.subheader("🐑 Hastalık / Test Panelleri Dağılımı")
            
            test_ozet = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index()
            test_ozet = test_ozet.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
            
            fig_testler = px.funnel(test_ozet, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)',
                                    title='En Çok Çalışılan Hastalık/Test Panelleri (İlk 10)',
                                    color_discrete_sequence=zaman_renkleri)
            fig_testler.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_testler, use_container_width=True)

            # Footer
            st.caption("Veriler 'veri.xlsx' dosyasından anlık olarak beslenmektedir. Son güncelleme: " + datetime.datetime.now().strftime("%H:%M:%S"))

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="DİAGEN Veteriner LAB Paneli", page_icon="🧬", layout="wide")

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- GİRİŞ EKRANI ---
if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Giriş ekranına da logo ekleyelim (Eğer yüklendiyse)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=250)
            
        st.title("🔒 Sisteme Giriş")
        st.markdown("Lütfen DİAGEN Laboratuvar paneline erişmek için bilgilerinizi girin.")
        
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
    # Yan menüye logo ekleme
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
        st.sidebar.divider()
        
    st.sidebar.button("🚪 Çıkış Yap", on_click=lambda: st.session_state.update({'giris_yapildi': False}))
    st.sidebar.divider()

    # BAŞLIK DEĞİŞİKLİĞİ 2
    st.title("🧬 DİAGEN Veteriner LAB Rapor İzleme Paneli")
    st.markdown("Aylık ve haftalık bazda numune akışını, kurum performanslarını ve test yoğunluklarını analiz edin.")

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
            df['Ay'] = df['Test tarihi'].dt.month.map(ay_sozlugu)
            
            df['Gelen Numune Sayısı'] = pd.to_numeric(df['Gelen Numune Sayısı'], errors='coerce').fillna(0)
            df['Numune adedi (işlenen numune)'] = pd.to_numeric(df['Numune adedi (işlenen numune)'], errors='coerce').fillna(0)
            
            return df
        except Exception as e:
            st.error(f"SİSTEMİN GERÇEK HATASI: {e}")
            return pd.DataFrame()

    df_ham = veri_getir()

    if not df_ham.empty:
        # --- YAN MENÜ (FİLTRELER) ---
        st.sidebar.header("🔍 Filtreleme Seçenekleri")
        
        mevcut_aylar = df_ham['Ay'].dropna().unique().tolist()
        secilen_aylar = st.sidebar.multiselect("İncelenecek Ayları Seçin:", mevcut_aylar, default=mevcut_aylar)
        
        if secilen_aylar:
            df = df_ham[df_ham['Ay'].isin(secilen_aylar)]
        else:
            df = df_ham
        
        if df.empty:
            st.warning("Seçili filtrelere uygun veri bulunamadı!")
        else:
            # BAŞLIK DEĞİŞİKLİĞİ 1
            st.subheader("💡 GENEL VERİLER")
            
            en_yogun_ay = df.groupby('Ay')['Numune adedi (işlenen numune)'].sum().idxmax()
            en_cok_is_yapan_kurum = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().idxmax()
            en_populer_test = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().idxmax()
            en_yogun_hafta = df.groupby('Hafta Numarası')['Numune adedi (işlenen numune)'].sum().idxmax()
            
            i1, i2, i3, i4 = st.columns(4)
            i1.info(f"📅 **En Yoğun Ay:**\n\n {en_yogun_ay} ayı test kapasitesinin zirvesi oldu.")
            i2.success(f"🏆 **En Çok İşlem Yapılan Kurum:**\n\n {en_cok_is_yapan_kurum}")
            i3.warning(f"🧪 **En Popüler Test:**\n\n {en_populer_test} en çok talep gören işlem.")
            i4.error(f"🔥 **Zirve Yapan Hafta:**\n\n Yılın {en_yogun_hafta}. Haftası en çok mesai harcanan hafta oldu.")
            
            st.divider()

            # --- TEMEL METRİKLER (KPI) ---
            toplam_gelen = int(df['Gelen Numune Sayısı'].sum())
            toplam_islenen = int(df['Numune adedi (işlenen numune)'].sum())
            toplam_kurum = df['Kurum/Numune Sahibi'].nunique()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Gelen Numune (Seçili Dönem)", f"{toplam_gelen:,.0f} Adet")
            c2.metric("Toplam Yapılan Test (Seçili Dönem)", f"{toplam_islenen:,.0f} Adet")
            c3.metric("Hizmet Verilen Kurum Sayısı", f"{toplam_kurum} Kurum")

            st.divider()

            # --- KURUM ANALİZLERİ ---
            st.subheader("🏢 Kurum Performans ve Talep Analizi")
            k1, k2 = st.columns(2)
            
            with k1:
                kurum_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index()
                kurum_gelen = kurum_gelen[kurum_gelen['Gelen Numune Sayısı'] > 0]
                kurum_gelen = kurum_gelen.sort_values(by='Gelen Numune Sayısı', ascending=False).head(10)
                
                fig_gelen = px.bar(kurum_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi',
                                   orientation='h', title='En Çok Numune GÖNDEREN Kurumlar',
                                   text_auto=True, color='Gelen Numune Sayısı', color_continuous_scale='Blues')
                fig_gelen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig_gelen, use_container_width=True)
                
            with k2:
                kurum_islenen = df.groupby('Kurum/Numune Sahibi')['Numune adedi (işlenen numune)'].sum().reset_index()
                kurum_islenen = kurum_islenen[kurum_islenen['Numune adedi (işlenen numune)'] > 0]
                kurum_islenen = kurum_islenen.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
                
                fig_islenen = px.bar(kurum_islenen, x='Numune adedi (işlenen numune)', y='Kurum/Numune Sahibi',
                                     orientation='h', title='En Çok Test İŞLENEN Kurumlar',
                                     text_auto=True, color='Numune adedi (işlenen numune)', color_continuous_scale='Teal')
                fig_islenen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig_islenen, use_container_width=True)

            st.divider()

            # --- ZAMAN ÇİZELGESİ VE YOĞUNLUK ANALİZİ ---
            st.subheader("⏳ Aylık ve Haftalık Yoğunluk Dağılımı")
            z1, z2 = st.columns(2)
            
            with z1:
                haftalik_aylik = df.groupby(['Ay', 'Hafta Numarası'])['Numune adedi (işlenen numune)'].sum().reset_index()
                haftalik_aylik['Hafta Metni'] = haftalik_aylik['Hafta Numarası'].astype(str) + ". Hafta"
                
                fig_zaman = px.bar(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                                   title='Aylara Göre Haftalık Test Yoğunluğu', text_auto=True,
                                   barmode='group')
                st.plotly_chart(fig_zaman, use_container_width=True)
                
            with z2:
                test_ozet = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index()
                test_ozet = test_ozet.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
                
                fig_testler = px.funnel(test_ozet, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)',
                                        title='En Çok Tercih Edilen Testler (Huni Dağılımı)')
                st.plotly_chart(fig_testler, use_container_width=True)

            st.caption("Veriler 'veri.xlsx' dosyasından anlık olarak beslenmektedir. Son güncelleme: " + datetime.datetime.now().strftime("%H:%M:%S"))

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Laboratuvar Yönetim Paneli", page_icon="🧬", layout="wide")

st.title("🧬 Laboratuvar İş Zekası ve Yönetim Paneli")
st.markdown("Aylık ve haftalık bazda numune akışını, kurum performanslarını ve test yoğunluklarını analiz edin.")

# --- VERİ YÜKLEME VE TEMİZLEME ---
@st.cache_data(ttl=60)
def veri_getir():
    try:
        df = pd.read_excel("veri.xlsx")
        df.columns = df.columns.str.strip()
        
        # Tarih ve zaman ayarları
        df['Test tarihi'] = pd.to_datetime(df['Test tarihi'], errors='coerce')
        # Haftayı Yıl-Hafta formatında alalım ki yıllar karışmasın
        df['Hafta Numarası'] = df['Test tarihi'].dt.isocalendar().week
        df['Ay'] = df['Test tarihi'].dt.month_name(locale='tr_TR.utf8')
        
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
    
    # Aylar için filtre
    mevcut_aylar = df_ham['Ay'].dropna().unique().tolist()
    secilen_aylar = st.sidebar.multiselect("İncelenecek Ayları Seçin:", mevcut_aylar, default=mevcut_aylar)
    
    # Veriyi filtrele
    if secilen_aylar:
        df = df_ham[df_ham['Ay'].isin(secilen_aylar)]
    else:
        df = df_ham
    
    if df.empty:
        st.warning("Seçili filtrelere uygun veri bulunamadı!")
    else:
        # --- OTOMATİK İÇGÖRÜLER (ZENGİN METİN) ---
        st.subheader("💡 Yapay Zeka Özeti ve Öne Çıkanlar")
        
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
            # En çok numune GÖNDEREN kurumlar
            kurum_gelen = df.groupby('Kurum/Numune Sahibi')['Gelen Numune Sayısı'].sum().reset_index()
            kurum_gelen = kurum_gelen[kurum_gelen['Gelen Numune Sayısı'] > 0]
            kurum_gelen = kurum_gelen.sort_values(by='Gelen Numune Sayısı', ascending=False).head(10)
            
            fig_gelen = px.bar(kurum_gelen, x='Gelen Numune Sayısı', y='Kurum/Numune Sahibi',
                               orientation='h', title='En Çok Numune GÖNDEREN Kurumlar',
                               text_auto=True, color='Gelen Numune Sayısı', color_continuous_scale='Blues')
            fig_gelen.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_gelen, use_container_width=True)
            
        with k2:
            # En çok numune İŞLENEN kurumlar
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
            # Aylara ve Haftalara Göre Test Dağılımı (Sütun Grafik)
            haftalik_aylik = df.groupby(['Ay', 'Hafta Numarası'])['Numune adedi (işlenen numune)'].sum().reset_index()
            # Hafta numarasını metne çevirelim ki grafikte düzgün dursun
            haftalik_aylik['Hafta Metni'] = haftalik_aylik['Hafta Numarası'].astype(str) + ". Hafta"
            
            fig_zaman = px.bar(haftalik_aylik, x='Ay', y='Numune adedi (işlenen numune)', color='Hafta Metni',
                               title='Aylara Göre Haftalık Test Yoğunluğu', text_auto=True,
                               barmode='group')
            st.plotly_chart(fig_zaman, use_container_width=True)
            
        with z2:
            # En Popüler Testler (Hangi Testler Daha Çok Yapılıyor)
            test_ozet = df.groupby('Test (MARKA ve PARAMETRE)')['Numune adedi (işlenen numune)'].sum().reset_index()
            test_ozet = test_ozet.sort_values(by='Numune adedi (işlenen numune)', ascending=False).head(10)
            
            fig_testler = px.funnel(test_ozet, x='Numune adedi (işlenen numune)', y='Test (MARKA ve PARAMETRE)',
                                    title='En Çok Tercih Edilen Testler (Huni Dağılımı)')
            # Huni grafik sayıları varsayılan olarak içinde net gösterir
            st.plotly_chart(fig_testler, use_container_width=True)

        # Alt Bilgi

        st.caption("Veriler 'veri.xlsx' dosyasından anlık olarak beslenmektedir. Son güncelleme: " + datetime.datetime.now().strftime("%H:%M:%S"))

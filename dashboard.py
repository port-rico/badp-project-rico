import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

import pkg_resources
installed = sorted([p.project_name for p in pkg_resources.working_set])
print("Installed packages:", installed)

# —–– Fungsi load data dari HuggingFace
@st.cache_data(show_spinner="🔄 Mengunduh dataset dari HuggingFace…")
def load_data():
    try:
        url = "https://huggingface.co/datasets/port-rico/badp-project/resolve/main/main_data.csv"
        df = pd.read_csv(url)
        # Validasi kolom penting
        required_cols = ["order_purchase_timestamp", "product_qty", "item_revenue", "product_category_name_english_x", "product_category_name", "customer_city", "customer_state", "delivery_days"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"❌ Kolom '{col}' tidak ditemukan dalam dataset.")
                return None
        # Tambah kolom tambahan jika belum ada
        if "product_qty" not in df.columns:
            df["product_qty"] = 1
        # Kombinasi kategori produk
        df["category_final"] = df["product_category_name_english_x"].fillna(df["product_category_name"])
        # Konversi ke datetime
        df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
        # Buat kolom bulan
        df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
        return df
    except Exception as e:
        st.error(f"❌ Gagal memuat dataset: {e}")
        return None

# —–– Sidebar untuk interaksi user
st.sidebar.header("🗂 Filter Data")

# Tombol load data
if st.sidebar.button("🔍 Load Data"):
    df = load_data()
    if df is None:
        st.stop()
else:
    st.sidebar.info("Klik tombol “Load Data” untuk mulai.")
    st.stop()

# Sidebar filter: rentang tanggal
min_date = df["order_purchase_timestamp"].min()
max_date = df["order_purchase_timestamp"].max()
date_range = st.sidebar.date_input(
    "Pilih Rentang Tanggal Pembelian",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Sidebar filter: kategori produk
kategori_list = sorted(df["category_final"].dropna().unique())
kategori_pilihan = st.sidebar.multiselect(
    "Pilih Kategori Produk",
    options=kategori_list,
    default=kategori_list
)

# Apply filter ke dataframe
df_filtered = df[
    (df["order_purchase_timestamp"] >= pd.to_datetime(date_range[0])) &
    (df["order_purchase_timestamp"] <= pd.to_datetime(date_range[1])) &
    (df["category_final"].isin(kategori_pilihan))
]

# —–– Judul aplikasi
st.title("📦 E-Commerce Analytics Dashboard")
st.write("Dashboard analisis produk & kota berdasarkan dataset E-Commerce Public Dataset.")

# —–– Top 10 kategori
st.header("Top 10 Kategori Produk Paling Laris & Menghasilkan Revenue")
top_qty = (
    df_filtered.groupby("category_final")["product_qty"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)
top_rev = (
    df_filtered.groupby("category_final")["item_revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

def highlight_top(series):
    return ["#F39C12" if i == series.idxmax() else "#BDBDBD" for i in series.index]

fig1 = px.bar(
    top_qty,
    orientation="h",
    color=top_qty.index,
    color_discrete_sequence=highlight_top(top_qty),
    title="Top 10 Kategori dengan Jumlah Pembelian Terbanyak",
)
fig1.update_layout(showlegend=False)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.bar(
    top_rev,
    orientation="h",
    color=top_rev.index,
    color_discrete_sequence=highlight_top(top_rev),
    title="Top 10 Kategori dengan Revenue Terbesar",
)
fig2.update_layout(showlegend=False)
st.plotly_chart(fig2, use_container_width=True)

# —–– Tren penjualan bulanan
st.header("Tren Penjualan Produk per Bulan")
monthly_sales = df_filtered.groupby("order_month")["item_revenue"].sum().reset_index()
fig3 = px.line(
    monthly_sales,
    x="order_month",
    y="item_revenue",
    title="Tren Revenue Bulanan",
    markers=True,
)
st.plotly_chart(fig3, use_container_width=True)

# —–– Kota pelanggan
st.header("Analisis Kota: Pelanggan vs Transaksi")
top_customers = df_filtered["customer_city"].value_counts().head(10)
top_transactions = df_filtered["customer_city"].value_counts().head(10)

def highlight_top_city(series):
    max_city = series.idxmax()
    return ["#F39C12" if idx == max_city else "#BDBDBD" for idx in series.index]

fig4 = px.bar(
    top_customers,
    orientation="h",
    color=top_customers.index,
    color_discrete_sequence=highlight_top_city(top_customers),
    title="Top 10 Kota dengan Pelanggan Terbanyak",
)
fig4.update_layout(showlegend=False, yaxis=dict(categoryorder="total ascending"))
st.plotly_chart(fig4, use_container_width=True)

fig5 = px.bar(
    top_transactions,
    orientation="h",
    color=top_transactions.index,
    color_discrete_sequence=highlight_top_city(top_transactions),
    title="Top 10 Kota dengan Transaksi Terbanyak (berdasarkan alamat customer)",
)
fig5.update_layout(showlegend=False, yaxis=dict(categoryorder="total ascending"))
st.plotly_chart(fig5, use_container_width=True)

# —–– Peta rata-rata waktu pengiriman
st.header("Peta Rata-rata Waktu Pengiriman per Negara Bagian (Brazil)")
shipping_state = df_filtered.groupby("customer_state")["delivery_days"].mean().reset_index()

BR_GEOJSON = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/main/public/data/brazil-states.geojson"
m = folium.Map(location=[-14.235, -51.925], zoom_start=4)
folium.Choropleth(
    geo_data=BR_GEOJSON,
    name="choropleth",
    data=shipping_state,
    columns=["customer_state", "delivery_days"],
    key_on="feature.properties.sigla",
    fill_color="YlOrRd",
    fill_opacity=0.8,
    line_opacity=0.3,
    legend_name="Rata-rata Waktu Pengiriman (hari)",
).add_to(m)
st_folium(m, width=700, height=450)




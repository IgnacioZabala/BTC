import streamlit as st
import pandas as pd
import requests
import datetime
import os
import re

st.set_page_config(page_title="Analizador BingX - DCA & Futuros", layout="wide")

@st.cache_data(ttl=60)
def get_live_btc_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url, timeout=3)
        data = response.json()
        if "bitcoin" in data and "usd" in data["bitcoin"]:
            return float(data["bitcoin"]["usd"]), "CoinGecko"
    except Exception:
        pass

    try:
        url = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=3)
        data = response.json()
        if "price" in data:
            return float(data["price"]), "Binance Vision"
    except Exception:
        pass

    return 83408.0, "Manual / Sin conexión"

@st.cache_data(ttl=3600)
def get_bitcoin_2yr_ma():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=730&interval=daily"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "prices" in data and len(data["prices"]) > 0:
                precios = [item[1] for item in data["prices"]]
                ma_2yr = sum(precios) / len(precios)
                return ma_2yr, ma_2yr * 5
    except Exception:
        pass

    try:
        url_binance = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=730"
        response = requests.get(url_binance, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            precios = [float(item[4]) for item in data]
            if len(precios) > 0:
                ma_2yr = sum(precios) / len(precios)
                return ma_2yr, ma_2yr * 5
    except Exception:
        pass

    return None, None

def encontrar_columna(df, palabras_clave):
    for col in df.columns:
        if any(palabra in str(col).lower() for palabra in palabras_clave):
            return col
    return None

def obtener_url_descarga_drive(url):
    if not url:
        return None
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

st.title("📈 Analizador de Estrategia BTC: DCA + Futuros (M-Moneda)")

if 'precio_manual' not in st.session_state:
    st.session_state.precio_manual = None

precio_api, fuente_precio = get_live_btc_price()

# --- CONFIGURACIÓN DE GOOGLE DRIVE ---
st.sidebar.header("🔗 Conexión a Google Drive")
st.sidebar.markdown("Pega aquí los enlaces compartidos de tus archivos CSV.")

URL_DEFECTO_SPOT = "https://drive.google.com/file/d/1fdaxnayNzqE9XNBMfO1K6JDvcfowizzq/view?usp=drive_link" 
URL_DEFECTO_FUTUROS = "https://drive.google.com/file/d/1rgbrxHV40-Q5_ic3C1umWKfIanT2VTSA/view?usp=sharing"

link_spot = st.sidebar.text_input("Enlace CSV Spot", URL_DEFECTO_SPOT)
link_futuros = st.sidebar.text_input("Enlace CSV Futuros", URL_DEFECTO_FUTUROS)

st.sidebar.markdown("---")
st.sidebar.header("💵 Conversión a USD")
precio_venta_usdt = 1.04
st.sidebar.info(f"Cotización fijada (1 USDT = **{precio_venta_usdt}** USD billete).")

col1, col2 = st.columns([2, 1])
with col1:
    st.info("🔄 Los datos se sincronizan automáticamente desde Google Drive.")
with col2:
    sub_c1, sub_c2 = st.columns([3, 1])
    with sub_c1:
        val_inicial = st.session_state.precio_manual if st.session_state.precio_manual is not None else float(precio_api)
        current_btc_price = st.number_input(
            "Precio actual de BTC (USDT Exchange)", 
            min_value=1.0, 
            value=val_inicial, 
            step=100.0,
            key="input_precio_btc"
        )
        st.session_state.precio_manual = current_btc_price
    with sub_c2:
        st.write("") 
        st.write("") 
        if st.button("🔄", help="Forzar actualización de precio"):
            get_

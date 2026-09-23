import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Analizador BingX - DCA & Futuros", layout="wide")

def get_live_btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=5)
        return float(response.json()['price'])
    except Exception:
        return 65000.0

# Función segura para encontrar columnas sin que la app colapse
def encontrar_columna(df, palabras_clave):
    for col in df.columns:
        if any(palabra in col.lower() for palabra in palabras_clave):
            return col
    return None

st.title("📈 Analizador de Estrategia BTC: DCA + Futuros (M-Moneda)")

precio_actual_real = get_live_btc_price()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Sube tu archivo CSV general de BingX", type=["csv"])
with col2:
    current_btc_price = st.number_input(
        "Precio actual de BTC (USD)", 
        min_value=1.0, value=precio_actual_real, step=100.0
    )
    st.caption(f"🟢 Precio cargado: ${precio_actual_real:,.2f}")

if uploaded_file is not None:
    # Intentamos leer el archivo
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        st.error("❌ El archivo no se pudo leer. Asegúrate de que sea un CSV válido.")
        st.stop()

    if df.empty:
        st.warning("⚠️ El archivo está vacío (no tiene operaciones).")
        st.stop()

    # Buscar columnas de forma segura
    account_col = encontrar_columna(df, ["cuenta", "account", "tipo", "type"])
    side_col = encontrar_columna(df, ["side", "lado", "dirección", "direction"])
    amount_col = encontrar_columna(df, ["amount", "monto", "executed", "ejecutado", "cantidad"])
    price_col = encontrar_columna(df, ["price", "precio"])

    # Validar que existan las columnas mínimas
    if not account_col:
        st.error(f"❌ No se pudo identificar la columna de 'Cuenta'. Las columnas de tu archivo son: {', '.join(df.columns)}")
        st.stop()

    if not amount_col or not price_col:
        st.error("❌ No se encontraron las columnas de 'Monto' o 'Precio'. Verifica que sea el historial de órdenes.")
        st.stop()

    # --- 1. ANÁLISIS SPOT ---
    df_spot = df[df[account_col].astype(str).str.contains("Spot", case=False, na=False)]
    
    total_btc_comprados = 0.0
    total_usdt_invertidos = 0.0
    dca_promedio = 0.0

    if not df_spot.empty and side_col:
        df_spot_buy = df_spot[
            (df_spot[side_col].astype(str).str.contains("Buy", case=False, na=False) | 
             df_spot[side_col].astype(str).str.contains("Compra", case=False, na=False))
        ].copy()
        
        # Filtro de BTC si existe la columna de par
        par_col = encontrar_columna(df, ["par", "symbol"])
        if par_col:
            df_spot_buy = df_spot_buy[df_spot_buy[par_col].astype(str).str.contains("BTC", case=False, na=False)]
        
        df_spot_buy[amount_col] = pd.to_numeric(df_spot_buy[amount_col], errors='coerce').fillna(0)
        df_spot_buy[price_col] = pd.to_numeric(df_spot_buy[price_col], errors='coerce').fillna(0)
        df_spot_buy['USDT_Invertidos'] = df_spot_buy[amount_col] * df_spot_buy[price_col]
        
        total_btc_comprados = df_spot_buy[amount_col].sum()
        total_usdt_invertidos = df_spot_buy['USDT_Invertidos'].sum()
        dca_promedio = total_usdt_invertidos / total_btc_comprados if total_btc_comprados > 0 else 0

    # --- 2. ANÁLISIS FUTUROS ---
    df_m_moneda = df[df[account_col].astype(str).str.contains("M-Moneda|Perpetuo|Coin-M", case=False, na=False)].copy()
    total_btc_ganados_futuros = 0.0
    
    if not df_m_moneda.empty:
        pnl_col = encontrar_columna(df_m_moneda, ["pnl", "ganancia", "profit", "realized"])
        if pnl_col:
            df_m_moneda['PnL_BTC'] = pd.to_numeric(df_m_moneda[pnl_col], errors='coerce').fillna(0)
            total_btc_ganados_futuros = df_m_moneda['PnL_BTC'].sum()

    # --- 3. RESULTADOS GLOBALES ---
    patrimonio_total_btc = total_btc_comprados + total_btc_ganados_futuros
    valor_actual_usd = patrimonio_total_btc * current_btc_price
    ganancia_neta_usd = valor_actual_usd - total_usdt_invertidos

    st.markdown("---")
    st.header("💡 Resultados de tu Estrategia")
    m1, m2, m3 = st.columns(3)
    m1.metric("Precio Promedio Compra (DCA)", f"${dca_promedio:,.2f}")
    m2.metric("Total USDT Invertido", f"${total_usdt_invertidos:,.2f}")
    m3.metric("BTC Comprados (Spot)", f"₿ {total_btc_comprados:,.6f}")
    
    st.markdown("---")
    m4, m5, m6 = st.columns(3)
    m4.metric("BTC Ganados (Futuros M-Moneda)", f"₿ {total_btc_ganados_futuros:,.6f}")
    m5.metric("Patrimonio Total Actual", f"₿ {patrimonio_total_btc:,.6f}")
    m6.metric("Valorización Actual (USD)", f"${valor_actual_usd:,.2f}")
    
    st.markdown("---")
    st.subheader(f"🚀 Ganancia Neta Total en USD: ${ganancia_neta_usd:,.2f}")

    # --- 4. SIMULADOR DE SALIDA ---
    st.markdown("---")
    st.header("🎯 Simulador de Toma de Ganancias")
    precio_objetivo = st.slider("¿A qué precio planeas vender? (USD)", min_value=int(current_btc_price), max_value=300000, value=180000, step=5000)
    valor_futuro_usd = patrimonio_total_btc * precio_objetivo
    ganancia_futura_usd = valor_futuro_usd - total_usdt_invertidos

    c1, c2 = st.columns(2)
    c1.info(f"**Valor del Portafolio a ${precio_objetivo:,}:** \n\n ### ${valor_futuro_usd:,.2f}")
    c2.success(f"**Ganancia Neta Proyectada:** \n\n ### ${ganancia_futura_usd:,.2f}")

# --- 5. CALCULADORA DE MARGEN ---
st.markdown("---")
st.header("🛡️ Calculadora de Margen de Seguridad (M-Moneda)")
c3, c4 = st.columns(2)
with c3:
    precio_entrada = st.number_input("Precio de Entrada del Long (USD)", value=int(current_btc_price), step=100)
    tamano_posicion_usd = st.number_input("Tamaño de la Posición (Valor del contrato en USD)", value=1000, step=100)
with c4:
    apalancamiento = st.number_input("Apalancamiento (x)", value=10, min_value=1, step=1)
    caida_protegida = st.slider("Protección de Caída Deseada (%)", min_value=10, max_value=80, value=30, step=1) / 100.0

if precio_entrada > 0:
    precio_liquidacion_objetivo = precio_entrada * (1 - caida_protegida)
    margen_inicial_btc = (tamano_posicion_usd / precio_entrada) / apalancamiento
    perdida_btc_en_caida = tamano_posicion_usd * ((1 / precio_liquidacion_objetivo) - (1 / precio_entrada))
    margen_extra_necesario = perdida_btc_en_caida - margen_inicial_btc

    st.write(f"- 📉 **Precio de Liquidación que buscas (-{caida_protegida*100}%):** ${precio_liquidacion_objetivo:,.2f}")
    if margen_extra_necesario > 0:
        st.success(f"➕ **MARGEN EXTRA A AGREGAR MANUALMENTE:** ₿ {margen_extra_necesario:,.6f}")
    else:
        st.success("✅ Tu margen inicial ya cubre esta caída.")

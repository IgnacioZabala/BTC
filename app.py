import streamlit as st
import pandas as pd
import requests

# Configuración inicial de la página
st.set_page_config(page_title="Analizador BingX - DCA & Futuros", layout="wide")

# Función para obtener el precio en vivo de BTC
def get_live_btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data['price'])
    except Exception:
        return 65000.0  # Precio de respaldo en caso de fallo de conexión

st.title("📈 Analizador de Estrategia BTC: DCA + Futuros (M-Moneda)")

# Cargar precio actual
precio_actual_real = get_live_btc_price()

# Diseño superior: Carga de archivo y ajuste de precio
col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Sube tu archivo CSV general de BingX", type=["csv"])
with col2:
    current_btc_price = st.number_input(
        "Precio actual de BTC (USD)", 
        min_value=1.0, 
        value=precio_actual_real,
        step=100.0,
        help="Este es el precio actual en vivo. Puedes cambiarlo para simular escenarios."
    )
    st.caption(f"🟢 Conectado al mercado. Precio cargado: ${precio_actual_real:,.2f}")

# PROCESAMIENTO DEL ARCHIVO CSV
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Identificación dinámica de columnas (por si BingX cambia los nombres)
    account_col = [c for c in df.columns if "cuenta" in c.lower() or "account" in c.lower()][0]
    side_col = [c for c in df.columns if "side" in c.lower() or "lado" in c.lower() or "dirección" in c.lower()][0]
    amount_col = [c for c in df.columns if "amount" in c.lower() or "monto" in c.lower() or "executed" in c.lower()][0]
    price_col = [c for c in df.columns if "price" in c.lower() or "precio" in c.lower()][0]
    
    # --- 1. ANÁLISIS SPOT (DCA) ---
    df_spot = df[df[account_col].astype(str).str.contains("Spot", case=False, na=False)]
    
    # Filtrar compras de BTC
    df_spot_buy = df_spot[
        (df_spot[side_col].astype(str).str.contains("Buy", case=False, na=False) | 
         df_spot[side_col].astype(str).str.contains("Compra", case=False, na=False))
    ].copy()
    
    # Filtrar por símbolo/par si la columna existe
    if 'Par' in df.columns:
         df_spot_buy = df_spot_buy[df_spot_buy['Par'].astype(str).str.contains("BTC", case=False, na=False)]
    elif 'Symbol' in df.columns:
         df_spot_buy = df_spot_buy[df_spot_buy['Symbol'].astype(str).str.contains("BTC", case=False, na=False)]
         
    df_spot_buy[amount_col] = pd.to_numeric(df_spot_buy[amount_col], errors='coerce').fillna(0)
    df_spot_buy[price_col] = pd.to_numeric(df_spot_buy[price_col], errors='coerce').fillna(0)
    df_spot_buy['USDT_Invertidos'] = df_spot_buy[amount_col] * df_spot_buy[price_col]
    
    total_btc_comprados = df_spot_buy[amount_col].sum()
    total_usdt_invertidos = df_spot_buy['USDT_Invertidos'].sum()
    dca_promedio = total_usdt_invertidos / total_btc_comprados if total_btc_comprados > 0 else 0

    # --- 2. ANÁLISIS FUTUROS (M-Moneda) ---
    df_m_moneda = df[df[account_col].astype(str).str.contains("M-Moneda", case=False, na=False)].copy()
    
    try:
        pnl_col = [c for c in df_m_moneda.columns if "pnl" in c.lower() or "ganancia" in c.lower()][0]
        df_m_moneda['PnL_BTC'] = pd.to_numeric(df_m_moneda[pnl_col], errors='coerce').fillna(0)
        total_btc_ganados_futuros = df_m_moneda['PnL_BTC'].sum()
    except IndexError:
        total_btc_ganados_futuros = 0.0

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
    st.caption("Esta ganancia incluye la apreciación de los BTC comprados y el valor de los BTC ganados haciendo trading a 10x.")

    # --- 4. SIMULADOR DE SALIDA ---
    st.markdown("---")
    st.header("🎯 Simulador de Toma de Ganancias")
    st.write("Calcula el valor de tu portafolio si BTC alcanza tu objetivo del ciclo.")

    precio_objetivo = st.slider(
        "¿A qué precio planeas vender? (USD)",
        min_value=int(current_btc_price),
        max_value=300000,
        value=180000,
        step=5000
    )

    valor_futuro_usd = patrimonio_total_btc * precio_objetivo
    ganancia_futura_usd = valor_futuro_usd - total_usdt_invertidos

    c1, c2 = st.columns(2)
    c1.info(f"**Valor del Portafolio a ${precio_objetivo:,}:** \n\n ### ${valor_futuro_usd:,.2f}")
    c2.success(f"**Ganancia Neta Proyectada:** \n\n ### ${ganancia_futura_usd:,.2f}")

# --- 5. CALCULADORA DE MARGEN (Siempre visible en la parte inferior) ---
st.markdown("---")
st.header("🛡️ Calculadora de Margen de Seguridad (M-Moneda)")
st.write("Calcula los satoshis exactos que debes inyectar como margen para soportar caídas bruscas sin liquidación.")

c3, c4 = st.columns(2)
with c3:
    precio_entrada = st.number_input("Precio de Entrada del Long (USD)", value=int(current_btc_price), step=100)
    tamano_posicion_usd = st.number_input("Tamaño de la Posición (Valor del contrato en USD)", value=1000, step=100)
with c4:
    apalancamiento = st.number_input("Apalancamiento (x)", value=10, min_value=1, step=1)
    caida_protegida = st.slider("Protección de Caída Deseada (%)", min_value=10, max_value=80, value=30, step=1) / 100.0

if precio_entrada > 0:
    precio_liquidacion_objetivo = precio_entrada * (1 - caida_protegida)
    tamano_btc = tamano_posicion_usd / precio_entrada
    margen_inicial_btc = tamano_btc / apalancamiento
    perdida_btc_en_caida = tamano_posicion_usd * ((1 / precio_liquidacion_objetivo) - (1 / precio_entrada))
    margen_extra_necesario = perdida_btc_en_caida - margen_inicial_btc

    st.info(f"**Escenario para un Long de ${tamano_posicion_usd:,} a {apalancamiento}x (Entrada: ${precio_entrada:,}):**")
    st.write(f"- 📉 **Precio de Liquidación que buscas (-{caida_protegida*100}%):** ${precio_liquidacion_objetivo:,.2f}")
    st.write(f"- 🔒 **Margen Inicial (Requerido por BingX):** ₿ {margen_inicial_btc:,.6f}")
    st.write(f"- ⚠️ **Pérdida en BTC si cae a ${precio_liquidacion_objetivo:,.0f}:** ₿ {perdida_btc_en_caida:,.6f}")
    
    st.markdown("---")
    if margen_extra_necesario > 0:
        st.success(f"➕ **MARGEN EXTRA A AGREGAR MANUALMENTE:** \n\n ### ₿ {margen_extra_necesario:,.6f}")
        costo_extra_usd_hoy = margen_extra_necesario * current_btc_price
        st.caption(f"*(Añadir este margen te cuesta aprox. ${costo_extra_usd_hoy:,.2f} al precio simulado de hoy)*")
    else:
        st.success("✅ Tu apalancamiento es tan bajo que tu margen inicial ya cubre esta caída.")

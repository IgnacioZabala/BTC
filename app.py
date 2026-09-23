import streamlit as st
import pandas as pd
import requests
import datetime

st.set_page_config(page_title="Analizador BingX - DCA & Futuros", layout="wide")

def get_live_btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=5)
        return float(response.json()['price'])
    except Exception:
        return 65000.0

def encontrar_columna(df, palabras_clave):
    for col in df.columns:
        if any(palabra in str(col).lower() for palabra in palabras_clave):
            return col
    return None

st.title("📈 Analizador de Estrategia BTC: DCA + Futuros (M-Moneda)")
precio_actual_real = get_live_btc_price()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_files = st.file_uploader(
        "Sube tus archivos CSV de BingX", 
        type=["csv"], 
        accept_multiple_files=True
    )
with col2:
    current_btc_price = st.number_input("Precio actual de BTC (USD)", min_value=1.0, value=precio_actual_real, step=100.0)
    st.caption(f"🟢 Precio cargado: ${precio_actual_real:,.2f}")

if uploaded_files:
    total_btc_neto_spot = 0.0
    total_usdt_neto_invertido = 0.0
    total_btc_ganados_futuros = 0.0
    fechas_operaciones = []
    archivos_procesados = []

    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
        except Exception:
            continue
        
        if df.empty:
            continue

        nombre_archivo = file.name.lower()
        time_col = encontrar_columna(df, ["time", "fecha", "date"])

        if time_col:
            df['Fecha_Clean'] = pd.to_datetime(df[time_col], errors='coerce')
            fechas_operaciones.extend(df['Fecha_Clean'].dropna().tolist())

        # --- 1. PROCESAR SPOT ---
        if "spot" in nombre_archivo and "chain" not in nombre_archivo:
            side_col = encontrar_columna(df, ["side", "lado", "dirección", "direction", "tipo", "type", "action", "acción"])
            amount_col = encontrar_columna(df, ["amount", "monto", "executed", "ejecutado", "cantidad", "filled", "volume", "volumen"])
            price_col = encontrar_columna(df, ["price", "precio", "average", "avg", "promedio"])
            par_col = encontrar_columna(df, ["par", "symbol", "símbolo", "pair", "coin", "asset", "activo"])

            if amount_col and price_col and side_col:
                if par_col:
                    df_btc = df[df[par_col].astype(str).str.contains("BTC", case=False, na=False)].copy()
                else:
                    df_btc = df.copy()
                
                df_btc[amount_col] = pd.to_numeric(df_btc[amount_col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
                df_btc[price_col] = pd.to_numeric(df_btc[price_col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
                df_btc['Valor_USD'] = df_btc[amount_col] * df_btc[price_col]
                
                is_buy = df_btc[side_col].astype(str).str.contains("Buy|Compra|buy", case=False, na=False)
                is_sell = df_btc[side_col].astype(str).str.contains("Sell|Venta|sell", case=False, na=False)
                
                btc_comprado = df_btc.loc[is_buy, amount_col].sum()
                usd_invertido = df_btc.loc[is_buy, 'Valor_USD'].sum()
                btc_vendido = df_btc.loc[is_sell, amount_col].sum()
                usd_recuperado = df_btc.loc[is_sell, 'Valor_USD'].sum()
                
                total_btc_neto_spot += (btc_comprado - btc_vendido)
                total_usdt_neto_invertido += (usd_invertido - usd_recuperado)
                archivos_procesados.append(file.name)

        # --- 2. PROCESAR FUTUROS M-MONEDA ---
        elif "coin_m" in nombre_archivo or "m_moneda" in nombre_archivo:
            pnl_col = encontrar_columna(df, ["pnl", "ganancia", "profit", "realized", "realizado"])
            if pnl_col:
                df['PnL_BTC'] = pd.to_numeric(df[pnl_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                total_btc_ganados_futuros += df['PnL_BTC'].sum()
                archivos_procesados.append(file.name)

    if len(archivos_procesados) > 0:
        st.success(f"✅ Archivos analizados con éxito: {', '.join(archivos_procesados)}")
        
        dca_promedio = total_usdt_neto_invertido / total_btc_neto_spot if total_btc_neto_spot > 0 else 0
        patrimonio_total_btc = total_btc_neto_spot + total_btc_ganados_futuros
        valor_actual_usd = patrimonio_total_btc * current_btc_price
        ganancia_neta_usd = valor_actual_usd - total_usdt_neto_invertido

        # --- CÁLCULO DE RENTABILIDAD ANUALIZADA ---
        anos_inversion = 1.0
        if fechas_operaciones:
            primera_fecha = min(fechas_operaciones)
            hoy = pd.Timestamp.now()
            dias_transcurridos = (hoy - primeira_fecha).days
            if dias_transcurridos > 30:
                anos_inversion = dias_transcurridos / 365.25

        # Rentabilidad Total (%) y Tasa Anualizada (CAGR)
        rentabilidad_total_pct = (valor_actual_usd / total_usdt_neto_invertido - 1) * 100 if total_usdt_neto_invertido > 0 else 0
        if total_usdt_neto_invertido > 0 and valor_actual_usd > 0 and anos_inversion > 0:
            cagr = (((valor_actual_usd / total_usdt_neto_invertido) ** (1 / anos_inversion)) - 1) * 100
        else:
            cagr = 0.0

        st.markdown("---")
        st.header("💡 Resultados y Rentabilidad Histórica")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total USDT Invertido (Neto)", f"${total_usdt_neto_invertido:,.2f}")
        m2.metric("Patrimonio Total Actual", f"₿ {patrimonio_total_btc:,.6f}")
        m3.metric("Valorización Actual (USD)", f"${valor_actual_usd:,.2f}")
        
        st.markdown("---")
        m4, m5, m6 = st.columns(3)
        m4.metric("Ganancia Neta Total", f"${ganancia_neta_usd:,.2f}", f"{rentabilidad_total_pct:,.1f}%")
        m5.metric("Rentabilidad Anualizada (CAGR)", f"{cagr:,.1f}% anual")
        m6.metric("Antigüedad del Historial", f"{anos_inversion*12:,.1f} meses")

        # --- PROYECCIÓN DE CRECIMIENTO ---
        st.markdown("---")
        st.header("📊 Proyección Futura Basada en tu Rendimiento")
        st.write("Simulación de crecimiento estimada para los próximos años aplicando una tasa compuesta alineada con tu historial:")

        col_p1, col_p2, col_p3 = st.columns(3)
        
        # Proyecciones a 1, 2 y 3 años usando el CAGR histórico (o limitándolo si es muy volátil)
        tasa_proyeccion = max(min(cagr, 150.0), 10.0) # Tope conservador/realista para evitar saltos locos si el historial es muy corto
        
        val_1_ano = valor_actual_usd * (1 + (tasa_proyeccion / 100))
        val_2_anos = val_1_ano * (1 + (tasa_proyeccion / 100))
        val_3_anos = val_2_anos * (1 + (tasa_proyeccion / 100))

        col_p1.info(f"**Proyección a 1 Año:** \n\n ### ${val_1_ano:,.2f}")
        col_p2.info(f"**Proyección a 2 Años:** \n\n ### ${val_2_anos:,.2f}")
        col_p3.info(f"**Proyección a 3 Años:** \n\n ### ${val_3_anos:,.2f}")

        # --- SIMULADOR DE SALIDA ---
        st.markdown("---")
        st.header("🎯 Simulador de Toma de Ganancias (Objetivo de Ciclo)")
        precio_objetivo = st.slider("¿A qué precio planeas vender? (USD)", min_value=int(current_btc_price), max_value=300000, value=180000, step=5000)
        valor_futuro_usd = patrimonio_total_btc * precio_objetivo
        ganancia_futura_usd = valor_futuro_usd - total_usdt_neto_invertido

        c1, c2 = st.columns(2)
        c1.info(f"**Valor del Portafolio a ${precio_objetivo:,}:** \n\n ### ${valor_futuro_usd:,.2f}")
        c2.success(f"**Ganancia Neta Proyectada:** \n\n ### ${ganancia_futura_usd:,.2f}")
    else:
        st.warning("⚠️ Sube los archivos CSV correspondientes de BingX.")

# --- CALCULADORA DE MARGEN ---
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

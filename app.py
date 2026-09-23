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
    total_btc_comprados = 0.0
    total_usdt_invertidos = 0.0
    total_btc_ganados_futuros = 0.0
    archivos_procesados = []
    errores_debug = []

    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
        except Exception:
            continue
        
        if df.empty:
            continue

        nombre_archivo = file.name.lower()

        # --- 1. PROCESAR COMPRAS SPOT ---
        if "spot" in nombre_archivo and "chain" not in nombre_archivo: # Ignorar el ChainSpot que es para retiros/depósitos
            # Búsqueda súper ampliada de columnas
            side_col = encontrar_columna(df, ["side", "lado", "dirección", "direction", "tipo", "type", "action", "acción"])
            amount_col = encontrar_columna(df, ["amount", "monto", "executed", "ejecutado", "cantidad", "filled", "volume", "volumen"])
            price_col = encontrar_columna(df, ["price", "precio", "average", "avg", "promedio"])
            par_col = encontrar_columna(df, ["par", "symbol", "símbolo", "pair", "coin", "asset", "activo"])

            if amount_col and price_col and side_col:
                # Filtrar solo compras (Buy)
                df_buy = df[df[side_col].astype(str).str.contains("Buy|Compra|buy", case=False, na=False)].copy()
                
                # Filtrar solo Bitcoin
                if par_col:
                    df_buy = df_buy[df_buy[par_col].astype(str).str.contains("BTC", case=False, na=False)]
                
                # SÚPER LIMPIEZA DE NÚMEROS (eliminar comas y espacios ocultos)
                df_buy[amount_col] = pd.to_numeric(df_buy[amount_col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
                df_buy[price_col] = pd.to_numeric(df_buy[price_col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
                
                df_buy['USDT_Invertidos'] = df_buy[amount_col] * df_buy[price_col]
                
                if df_buy[amount_col].sum() > 0:
                    total_btc_comprados += df_buy[amount_col].sum()
                    total_usdt_invertidos += df_buy['USDT_Invertidos'].sum()
                    archivos_procesados.append(file.name)
                else:
                    errores_debug.append(f"El archivo {file.name} se procesó, pero no se detectaron compras de BTC en el rango de fechas. (Tal vez exportaste un rango donde no compraste Spot).")
            else:
                errores_debug.append(f"En {file.name} no se identificaron las columnas necesarias. Nombres exactos en tu archivo: {list(df.columns)}")

        # --- 2. PROCESAR FUTUROS M-MONEDA ---
        elif "coin_m" in nombre_archivo or "m_moneda" in nombre_archivo:
            pnl_col = encontrar_columna(df, ["pnl", "ganancia", "profit", "realized", "realizado"])
            if pnl_col:
                df['PnL_BTC'] = pd.to_numeric(df[pnl_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                total_btc_ganados_futuros += df['PnL_BTC'].sum()
                archivos_procesados.append(file.name)
            else:
                errores_debug.append(f"Falta columna de PnL en {file.name}. Columnas detectadas: {list(df.columns)}")

    # MOSTRAR RESULTADOS
    if len(archivos_procesados) > 0:
        st.success(f"✅ Archivos analizados con éxito: {', '.join(archivos_procesados)}")
        
        # Mostrar panel de depuración si hubo problemas con algún archivo
        if errores_debug:
            with st.expander("🛠️ Ver detalles de archivos no procesados (Haz clic aquí)"):
                for err in errores_debug:
                    st.warning(err)
        
        dca_promedio = total_usdt_invertidos / total_btc_comprados if total_btc_comprados > 0 else 0
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

        # --- SIMULADOR DE SALIDA ---
        st.markdown("---")
        st.header("🎯 Simulador de Toma de Ganancias")
        precio_objetivo = st.slider("¿A qué precio planeas vender? (USD)", min_value=int(current_btc_price), max_value=300000, value=180000, step=5000)
        valor_futuro_usd = patrimonio_total_btc * precio_objetivo
        ganancia_futura_usd = valor_futuro_usd - total_usdt_invertidos

        c1, c2 = st.columns(2)
        c1.info(f"**Valor del Portafolio a ${precio_objetivo:,}:** \n\n ### ${valor_futuro_usd:,.2f}")
        c2.success(f"**Ganancia Neta Proyectada:** \n\n ### ${ganancia_futura_usd:,.2f}")
    else:
        st.warning("⚠️ No se encontraron datos válidos. Revisa el archivo subido.")

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

import streamlit as st
import pandas as pd
import pdfplumber
from openai import OpenAI

# Configuración de la app
st.set_page_config(page_title="AI Agent CFO - FitBoost", layout="wide")
st.title("💼 Hola FitBoost, soy tu CFO digital")
st.write("Subí uno o más archivos de Excel o PDF y preguntame lo que necesites saber considerando todos.")

# Subir múltiples archivos
uploaded_files = st.file_uploader(
    "📤 Subí tus archivos (.xlsx o .pdf)",
    type=["xlsx", "pdf"],
    accept_multiple_files=True
)

# Acumuladores
dfs_all = []
extracted_text = ""

# Función: extrae tablas de Excel automáticamente
def extract_from_excel(file):
    sheets = pd.read_excel(file, sheet_name=None, header=None)
    dfs = []
    for sheet_name, raw in sheets.items():
        # Quitar filas vacías
        non_empty = raw.dropna(how='all')
        if non_empty.empty:
            continue
        # Primera fila con datos -> encabezado
        header = non_empty.iloc[0].fillna('').astype(str).tolist()
        # Asegurar nombres únicos
        seen = {}
        headers_unique = []
        for h in header:
            if h in seen:
                seen[h] += 1
                headers_unique.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                headers_unique.append(h)
        data = non_empty.iloc[1:].reset_index(drop=True)
        data.columns = headers_unique
        st.markdown(f"- Hoja: **{sheet_name}**")
        st.dataframe(data)
        dfs.append(data)
    return dfs

# Función: extrae tablas de PDF
def extract_from_pdf(file):
    global extracted_text
    dfs = []
    st.markdown("- Extrayendo tablas de PDF")
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if table:
                    df_temp = pd.DataFrame(table[1:], columns=table[0])
                    st.write(f"  • Tabla página {i+1}")
                    st.dataframe(df_temp)
                    dfs.append(df_temp)
                    extracted_text += df_temp.to_string(index=False) + "\n"
    return dfs

# Procesar archivos subidos
if uploaded_files:
    st.markdown("---")
    for f in uploaded_files:
        st.markdown(f"### Archivo: {f.name}")
        if f.name.lower().endswith(".xlsx"):
            dfs_all.extend(extract_from_excel(f))
        else:
            dfs_all.extend(extract_from_pdf(f))

    if dfs_all:
        df = pd.concat(dfs_all, ignore_index=True, sort=False)
        st.success(f"Se combinaron {len(dfs_all)} tablas/hojas en un único DataFrame con {len(df)} filas.")

        # NORMALIZAR NOMBRES DE COLUMNAS
        df.columns = [str(c).strip().upper() for c in df.columns]

        # DETECTAR COLUMNAS CLAVE
        rev_col = next((c for c in df.columns if 'INGRESO' in c), None)
        cost_col = next((c for c in df.columns if 'COSTO' in c), None)
        qty_col = next((c for c in df.columns if 'CANTIDAD' in c or 'QTY' in c), None)
        prod_col = next((c for c in df.columns if 'PRODUCTO' in c), None)

        # CALCULAR UTILIDAD SI ES POSIBLE
        if rev_col and cost_col:
            df['PROFIT'] = pd.to_numeric(df[rev_col], errors='coerce').fillna(0) - pd.to_numeric(df[cost_col], errors='coerce').fillna(0)

        # RESUMEN DE MÉTRICAS CLAVE
        summary = {}
        if rev_col:
            summary['Total ingresos'] = df[rev_col].astype(float).sum()
        if cost_col:
            summary['Total costos'] = df[cost_col].astype(float).sum()
        if 'PROFIT' in df:
            summary['Total utilidad'] = df['PROFIT'].sum()
            if 'Total ingresos' in summary and summary['Total ingresos']:
                summary['Margen utilidad %'] = summary['Total utilidad']/summary['Total ingresos']*100

        st.subheader("📊 Métricas clave")
        st.table(pd.DataFrame.from_dict(summary, orient='index', columns=['Valor']))

        # TOP 5 PRODUCTOS
        if prod_col and qty_col:
            top_qty = df.groupby(prod_col)[qty_col].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Cantidad")
            st.table(top_qty.astype(int))
        if prod_col and rev_col:
            top_rev = df.groupby(prod_col)[rev_col].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Ingresos")
            st.table(top_rev)
        if prod_col and 'PROFIT' in df:
            top_prof = df.groupby(prod_col)['PROFIT'].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Utilidad")
            st.table(top_prof)
    else:
        df = None

    # PREGUNTA AL CFO
st.subheader("💬 Preguntale a tu CFO sobre todos los datos")
pregunta = st.text_input("¿Qué querés saber?")

if pregunta:
    # Respuestas automáticas basadas en pandas para preguntas comunes
    respuesta_auto = None
    q = pregunta.lower()
    # Producto más vendido
    if 'producto más vendido' in q or 'mas vendido' in q:
        if prod_col and qty_col:
            top_prod = df.groupby(prod_col)[qty_col].sum().idxmax()
            respuesta_auto = f"El producto más vendido fue '{top_prod}'."
    # Cliente que más gastó
    if respuesta_auto is None and ('cliente' in q and 'gast' in q):
        if rev_col:
            top_client = df.groupby('CLIENTE' if 'CLIENTE' in df.columns else df.columns[0])[rev_col].sum().idxmax()
            respuesta_auto = f"El cliente que más gastó fue '{top_client}'."
    # Periodo de mayor venta (mes)
    if respuesta_auto is None and ('mes' in q and 'venta' in q):
        if 'FECHA' in df.columns:
            df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
            df['MES'] = df['FECHA'].dt.month_name()
            top_mes = df.groupby('MES')[rev_col].sum().idxmax()
            respuesta_auto = f"El mes con mayores ventas fue {top_mes}."

    if respuesta_auto:
        st.write(f"🧮 Respuesta automática: {respuesta_auto}")
        # Complemento por LLM
        prompt = f"Dame un breve análisis financiero sobre este hallazgo: {respuesta_auto}"
    else:
                # Generar prompt con resumen general
        prompt = ""  # iniciamos vacío
        prompt += "Resumen de métricas y top productos ha sido calculado.
"
        prompt += f"Pregunta: {pregunta}

"
        # Incluir el resumen para contexto
        prompt += "Resumen de métricas:
"
        for k, v in summary.items():
            prompt += f"{k}: {v}
"
        if 'top_qty' in locals():
            prompt += "
Top 5 Cantidad:
" + top_qty.to_string() + "
"
        if 'top_rev' in locals():
            prompt += "
Top 5 Ingresos:
" + top_rev.to_string() + "
"
        if 'top_prof' in locals():
            prompt += "
Top 5 Utilidad:
" + top_prof.to_string() + "
"

    # Ahora llamamos al cliente API
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    st.write("### 🧠 Respuesta del CFO:")
    st.write(response.choices[0].message.content)
else:
    st.info("Escribí una pregunta para que tu CFO digital la responda.")



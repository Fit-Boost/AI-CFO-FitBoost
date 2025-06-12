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
        non_empty = raw.dropna(how='all')
        if non_empty.empty:
            continue
        header = non_empty.iloc[0].fillna('').astype(str).tolist()
        # Asegurar nombres únicos
        seen = {}
        headers_unique = []
        for h in header:
            key = h or 'COL'
            if key in seen:
                seen[key] += 1
                headers_unique.append(f"{key}_{seen[key]}")
            else:
                seen[key] = 0
                headers_unique.append(key)
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

        # Normalizar nombres de columnas
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Detectar columnas clave
        rev_col = next((c for c in df.columns if 'INGRESO' in c or 'VENTA' in c), None)
        cost_col = next((c for c in df.columns if 'COSTO' in c), None)
        qty_col = next((c for c in df.columns if 'CANTIDAD' in c or 'QTY' in c), None)
        prod_col = next((c for c in df.columns if 'PRODUCTO' in c), None)
        date_col = next((c for c in df.columns if 'FECHA' in c), None)
        client_col = next((c for c in df.columns if 'CLIENTE' in c), None)

        # Calcular profit
        if rev_col and cost_col:
            df['PROFIT'] = (
                pd.to_numeric(df[rev_col], errors='coerce').fillna(0)
                - pd.to_numeric(df[cost_col], errors='coerce').fillna(0)
            )

        # Resumen de métricas clave
        t_summary = {}
        if rev_col:
            t_summary['Total ingresos'] = df[rev_col].astype(float).sum()
        if cost_col:
            t_summary['Total costos'] = df[cost_col].astype(float).sum()
        if 'PROFIT' in df:
            t_summary['Total utilidad'] = df['PROFIT'].sum()
        if t_summary.get('Total ingresos'):
            t_summary['Margen utilidad %'] = t_summary['Total utilidad'] / t_summary['Total ingresos'] * 100

        st.subheader("📊 Métricas clave")
        st.table(pd.DataFrame.from_dict(t_summary, orient='index', columns=['Valor']))

        # Top 5
        top_qty = None
        top_rev = None
        top_prof = None
        if prod_col and qty_col:
            top_qty = df.groupby(prod_col)[qty_col].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Cantidad")
            st.table(top_qty)
        if prod_col and rev_col:
            top_rev = df.groupby(prod_col)[rev_col].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Ingresos")
            st.table(top_rev)
        if prod_col and 'PROFIT' in df:
            top_prof = df.groupby(prod_col)['PROFIT'].sum().nlargest(5)
            st.subheader("🏅 Top 5 Productos por Utilidad")
            st.table(top_prof)

        # Pregunta al CFO
        st.subheader("💬 Preguntale a tu CFO sobre todos los datos")
        pregunta = st.text_input("¿Qué querés saber?")
        if pregunta:
            # Intentar respuesta automática basada en pandas
            respuesta_auto = None
            q = pregunta.lower()
            if prod_col and qty_col and ('mas vendido' in q or 'producto más vendido' in q):
                respuesta_auto = f"Producto más vendido: {top_qty.idxmax()}"
            elif client_col and rev_col and ('cliente' in q and 'gast' in q):
                gasto_cliente = df.groupby(client_col)[rev_col].sum().idxmax()
                respuesta_auto = f"Cliente que más gastó: {gasto_cliente}"
            elif date_col and rev_col and ('mes' in q and 'venta' in q):
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df['MES'] = df[date_col].dt.month_name()
                mes_top = df.groupby('MES')[rev_col].sum().idxmax()
                respuesta_auto = f"Mes con mayores ventas: {mes_top}"

            # Construir prompt
            if respuesta_auto:
                st.write(f"🧮 Respuesta automática: {respuesta_auto}")
                prompt = f"Analiza este hallazgo de forma breve y profesional: {respuesta_auto}\n"
            else:
                prompt_lines = ["Resumen de métricas clave:"]
                for k, v in t_summary.items():
                    prompt_lines.append(f"- {k}: {v}")
                if top_qty is not None:
                    prompt_lines.append("\nTop 5 Cantidad:")
                    prompt_lines.append(top_qty.to_string())
                if top_rev is not None:
                    prompt_lines.append("\nTop 5 Ingresos:")
                    prompt_lines.append(top_rev.to_string())
                if top_prof is not None:
                    prompt_lines.append("\nTop 5 Utilidad:\n")
                    prompt_lines.append(top_prof.to_string())
                prompt_lines.append(f"\nPregunta: {pregunta}")
                prompt = "\n".join(prompt_lines)

            # Llamada al API
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            st.write("### 🧠 Respuesta del CFO:")
            st.write(response.choices[0].message.content)
        else:
            st.info("Escribí una pregunta para que tu CFO digital la responda.")
    else:
        st.info("Por favor subí al menos un archivo para empezar.")




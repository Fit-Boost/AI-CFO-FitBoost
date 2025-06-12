import streamlit as st
import pandas as pd
import pdfplumber
from openai import OpenAI

# Configurar la app
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
all_dfs = []
extracted_text = ""

# Función para extraer de Excel con detección automática de encabezado
def extract_from_excel(file):
    raw_sheets = pd.read_excel(file, sheet_name=None, header=None)
    dfs = []
    for sheet_name, raw in raw_sheets.items():
        # Eliminar filas totalmente vacías
        non_empty = raw.dropna(how='all')
        if non_empty.empty:
            continue
        # Primera fila no vacía como encabezados
        header = non_empty.iloc[0].fillna('').astype(str).tolist()
        data = non_empty.iloc[1:].reset_index(drop=True)
        data.columns = header
        st.markdown(f"- Hoja: **{sheet_name}**")
        st.dataframe(data)
        dfs.append(data)
    return dfs

# Función para extraer tablas de PDF
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
    for uploaded_file in uploaded_files:
        st.markdown(f"### Archivo: {uploaded_file.name}")
        if uploaded_file.name.lower().endswith(".xlsx"):
            all_dfs.extend(extract_from_excel(uploaded_file))
        else:
            all_dfs.extend(extract_from_pdf(uploaded_file))

    # Combinar todas las tablas/hojas
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True, sort=False)
        st.success(f"Se combinaron {len(all_dfs)} tablas/hojas en un único DataFrame con {len(df)} filas.")
    else:
        df = None

    # Pregunta al CFO
    st.subheader("💬 Preguntale a tu CFO sobre todos los datos")
    pregunta = st.text_input("¿Qué querés saber?")
    if pregunta:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        if df is not None:
            preview = df.head().to_string(index=False)
            prompt = f"Estos son tus datos:\n{preview}\n\nPregunta: {pregunta}"
        else:
            prompt = f"Texto extraído de los PDFs:\n{extracted_text}\n\nPregunta: {pregunta}"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        st.write("### 🧠 Respuesta del CFO:")
        st.write(response.choices[0].message.content)
    else:
        st.info("Escribí una pregunta para que tu CFO digital la responda.")
else:
    st.info("Por favor subí al menos un archivo para empezar.")





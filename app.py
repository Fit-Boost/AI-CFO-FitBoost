import streamlit as st
import pandas as pd
import pdfplumber
from openai import OpenAI

# Configurar la app
st.set_page_config(page_title="AI Agent CFO - FitBoost", layout="wide")
st.title("💼 Hola FitBoost, soy tu CFO digital")
st.write("Subí uno o más archivos de Excel o PDF, y preguntame lo que necesites saber considerando todos.")

# Subir múltiples archivos
uploaded_files = st.file_uploader(
    "📤 Subí tus archivos (.xlsx o .pdf)",
    type=["xlsx", "pdf"],
    accept_multiple_files=True
)

# Listas para almacenar datos
all_dfs = []
extracted_text = ""

def extract_from_excel(file):
    # Leer todas las hojas y devolver lista de DataFrames
    sheets = pd.read_excel(file, sheet_name=None)
    dfs = []
    for sheet_name, sheet_df in sheets.items():
        st.markdown(f"- Hoja: **{sheet_name}**")
        st.dataframe(sheet_df)
        dfs.append(sheet_df)
    return dfs


def extract_from_pdf(file):
    dfs = []
    st.markdown(f"- Extrayendo tablas de PDF")
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if table:
                    df_temp = pd.DataFrame(table[1:], columns=table[0])
                    st.write(f"  • Tabla página {i+1}")
                    st.dataframe(df_temp)
                    dfs.append(df_temp)
                    # Acumula texto para prompts si no hay DataFrame
                    global extracted_text
                    extracted_text += df_temp.to_string(index=False) + "
"
    return dfs

# Procesar los archivos subidos
if uploaded_files:
    st.markdown("---")
    for uploaded_file in uploaded_files:
        st.markdown(f"### Archivo: {uploaded_file.name}")
        if uploaded_file.name.lower().endswith(".xlsx"):
            all_dfs.extend(extract_from_excel(uploaded_file))
        elif uploaded_file.name.lower().endswith(".pdf"):
            all_dfs.extend(extract_from_pdf(uploaded_file))

    if all_dfs:
        # Combinar todos los DataFrames en uno solo
        df = pd.concat(all_dfs, ignore_index=True, sort=False)
        st.success(f"Se combinaron {len(all_dfs)} tablas/hojas en un único DataFrame con {len(df)} filas.")
    else:
        df = None

    # Zona de preguntas
    st.subheader("💬 Preguntale a tu CFO sobre todos los datos")
    pregunta = st.text_input("¿Qué querés saber?")

    if pregunta:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        if df is not None:
            # Previsualizar primeras filas
            preview = df.head().to_string(index=False)
            prompt = f"Estos son tus datos combinados:\n{preview}\n\nPregunta: {pregunta}"
        else:
            prompt = f"Texto extraído de los PDFs:\n{extracted_text}\n\nPregunta: {pregunta}"

        # Llamar a la API de chat
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



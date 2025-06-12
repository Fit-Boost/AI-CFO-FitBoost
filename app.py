import streamlit as st
import pandas as pd
import pdfplumber
from openai import OpenAI

# Configurar la app
st.set_page_config(page_title="AI Agent CFO - FitBoost", layout="wide")
st.title("💼 Hola FitBoost, soy tu CFO digital")
st.write("Subí tu archivo de Excel o PDF, y preguntame lo que necesites saber.")

# Subir archivo
uploaded_file = st.file_uploader("📤 Subí tu archivo (.xlsx o .pdf)", type=["xlsx", "pdf"])

extracted_text = ""
df = None

# Procesar archivo
if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        st.subheader("📊 Vista previa de tus datos Excel")
        st.dataframe(df)
    elif uploaded_file.name.endswith(".pdf"):
        st.subheader("📄 Extrayendo tablas del PDF...")
        all_tables = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        df_temp = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df_temp)
                        st.write("📄 Tabla detectada:")
                        st.dataframe(df_temp)
                        extracted_text += df_temp.to_string(index=False) + "\n"
        # Unir todas las tablas extraídas en un solo DataFrame si es posible
        if all_tables:
            df = pd.concat(all_tables, ignore_index=True)

    # Pregunta
    st.subheader("💬 Preguntale a tu CFO")
    pregunta = st.text_input("¿Qué querés saber?")

    if pregunta:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        if df is not None:
            datos = df.head().to_string(index=False)
            prompt = f"Tus datos:\n{datos}\n\nPregunta: {pregunta}"
        else:
            prompt = f"Texto extraído del PDF:\n{extracted_text}\n\nPregunta: {pregunta}"

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        st.write("🧠 Respuesta del CFO:")
        st.write(response.choices[0].message.content)


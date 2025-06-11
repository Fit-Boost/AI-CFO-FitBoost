import streamlit as st
import pandas as pd
import pdfplumber
from openai import OpenAI

# Configuración inicial de la app
st.set_page_config(page_title="AI Agent CFO - FitBoost", layout="wide")
st.title("💼 Hola FitBoost, soy tu CFO digital")
st.write("Subí tu archivo de Excel o PDF, y preguntame lo que necesites saber.")

# Cargar archivo
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
        st.subheader("📄 Extrayendo datos del PDF...")
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted_text += page.extract_text()
        st.text_area("📋 Texto extraído del PDF", extracted_text, height=300)

    # Campo de pregunta
    st.subheader("💬 Preguntale a tu CFO")
    pregunta = st.text_input("¿Qué querés saber?")

    if pregunta:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        if df is not None:
            prompt = f"Tus datos de ventas:\n{df.head().to_string(index=False)}\n\nPregunta: {pregunta}"
        else:
            prompt = f"Este es el texto extraído del PDF:\n{extracted_text}\n\nPregunta: {pregunta}"

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        st.write("🧠 Respuesta del CFO:")
        st.write(response.choices[0].message.content)







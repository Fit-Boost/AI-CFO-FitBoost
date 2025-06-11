
import streamlit as st
import pandas as pd
import openai

st.set_page_config(page_title="AI Agent CFO - FitBoost", layout="wide")

st.title("💼 Hola FitBoost, soy tu CFO digital")
st.write("Subí tu archivo de Excel y preguntame lo que necesites saber.")

uploaded_file = st.file_uploader("📤 Subí tu archivo Excel de ventas", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📊 Vista previa de tus datos")
    st.dataframe(df)

    st.subheader("💬 Preguntale a tu CFO")
    pregunta = st.text_input("¿Qué querés saber?")
    if pregunta:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        prompt = f"Tus datos de ventas: {df.head().to_string(index=False)}. Pregunta: {pregunta}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        st.write("🧠 Respuesta del CFO:")
        st.write(response.choices[0].message.content)

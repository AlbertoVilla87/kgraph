import streamlit as st

st.title("Predictor de Reclamaciones")
categoria = st.selectbox("Sector", ["Telefonía", "Banca", "Energía"])
archivos = st.file_uploader("Sube tus documentos", accept_multiple_files=True)

if st.button("Analizar") and archivos:
    with st.spinner("Analizando..."):
        # aquí tu lógica / llamada al modelo
        resultado = "Favorable"
    st.success(f"Resolución: {resultado}")
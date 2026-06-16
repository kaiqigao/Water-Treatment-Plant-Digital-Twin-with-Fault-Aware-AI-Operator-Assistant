import streamlit as st

st.set_page_config(page_title="Water Treatment Digital Twin", layout="wide")

st.title("Water Treatment Plant Digital Twin")
st.caption("TUMA206 project scaffold")

left, right = st.columns(2)

with left:
    st.subheader("Live Process State")
    st.metric("Tank level", "50.0 %")
    st.metric("Reactor pH", "7.00")
    st.metric("PLC state", "stopped")

with right:
    st.subheader("Fault Injection")
    st.button("Inject sensor fault")
    st.button("Inject equipment fault")
    st.button("Inject process fault")
    st.button("Inject infrastructure fault")

st.subheader("AI Operator Assistant")
st.info("Assistant recommendations will appear here after fault detection is implemented.")

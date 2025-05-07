import streamlit as st
from app_pages.sharkfin import render as render_sharkfin
from app_pages.snowball import render as render_snowball
from app_pages.phoenix import render as render_phoenix


st.set_page_config(page_title="场外衍生品情景分析",layout="wide")
st.sidebar.title("产品选择")
page=st.sidebar.radio("选择产品：",["鲨鱼鳍","雪球","凤凰/DCN/FCN"])

if page=="鲨鱼鳍":
    render_sharkfin()
elif page=="雪球":
    render_snowball()
elif page=="凤凰/DCN/FCN":
    render_phoenix()
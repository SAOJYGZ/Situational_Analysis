import requests
import streamlit as st

@st.cache_data
def get_price_data(codes: list, start_date: str, end_date: str):
    """获取标的历史价格数据"""
    url = "http://192.168.1.103:60000/api/mkt-accessor-v2/get-price"
    payload = {"codes": codes, "startDate": start_date, "endDate": end_date}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception as e:
        st.error(f"价格数据获取失败: {e}")
        return {}
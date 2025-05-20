import os
import pandas as pd
import streamlit as st

# 动态获取当前脚本（api.py）所在目录作为数据目录
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def get_price_data(codes, start_date, end_date):
    result = {}
    sd = pd.to_datetime(start_date).date()
    ed = pd.to_datetime(end_date).date()

    for code in codes:
        base = code.split('.')[0]
        # 相对路径拼接
        path = os.path.join(BASE_PATH, f"{base}_daily.xlsx")

        if not os.path.exists(path):
            st.error(f"文件不存在：{path}")
            result[code] = []
            continue

        try:
            df = pd.read_excel(path, usecols=['date', 'close'], engine="openpyxl")
        except Exception as e:
            st.error(f"读取失败：{e}")
            result[code] = []
            continue

        # df = df.rename(columns={df.columns[0]:'date', df.columns[1]:'close'})
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df[(df['date']>=sd)&(df['date']<=ed)].sort_values('date')
        result[code] = [
            {'date':d.strftime('%Y-%m-%d'),'close':float(c) if pd.notna(c) else None}
            for d,c in zip(df['date'],df['close'])
        ]
    return result


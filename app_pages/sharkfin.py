import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def sharkfin():
    st.header("鲨鱼鳍期权情景分析")
    st.subheader("标的价格 vs 年化收益率")

    with st.form(key="sharkfin_ann_ret_form_final_conn"):
        st.write("核心参数输入:")
        col1, col2, col3 = st.columns(3)

        with col1:
            direction = st.selectbox("选择方向", ["看涨鲨鱼鳍", "看跌鲨鱼鳍"], index=0)
            strike_price = st.number_input("执行价格 K", min_value=1.0, max_value=10000.0, value=100.0, step=1.0)
            term_months = st.number_input("产品期限 (月)", min_value=1, max_value=120, value=12, step=1)

        with col2:
            barrier_price = st.number_input("障碍价格 B", min_value=1.0, max_value=10000.0, value=110.0, step=1.0)
            participation_rate = st.number_input("参与率 PR (%)", min_value=0.0, max_value=200.0, value=100.0, step=5.0)

        with col3:
            rebate_rate = st.number_input("越过障碍固定年化回报率 R (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.1)

        submit_button = st.form_submit_button("生成分析图表")

    if submit_button:
        term_years = term_months / 12
        pr = participation_rate / 100

        # 参数合法性检查
        valid_inputs = True
        if direction == "看涨鲨鱼鳍" and barrier_price <= strike_price:
            st.error("看涨鲨鱼鳍要求 障碍价格 > 执行价格。")
            valid_inputs = False
        if direction == "看跌鲨鱼鳍" and barrier_price >= strike_price:
            st.error("看跌鲨鱼鳍要求 障碍价格 < 执行价格。")
            valid_inputs = False
        if not valid_inputs:
            st.stop()

        st.subheader("输入参数概要")
        df_params = pd.DataFrame({
            "参数名称": ["方向", "执行价格 K", "障碍价格 B", "参与率 PR", "越障固定回报 R", "产品期限（年）"],
            "参数值": [
                direction, strike_price, barrier_price, f"{participation_rate:.2f}%", f"{rebate_rate:.2f}%", f"{term_years:.2f}年"
            ]
        })
        st.table(df_params.set_index("参数名称"))

        # 绘图数据生成
        fig = go.Figure()

        if direction == "看涨鲨鱼鳍":
            payoff = (barrier_price - strike_price) * pr / term_years

            x_start = strike_price - 10
            x_end = barrier_price + 10
            max_y = max(payoff, rebate_rate) + 10

            # 第一段：执行价以下水平线0%
            fig.add_trace(go.Scatter(
                x=[x_start, strike_price],
                y=[0, 0],
                mode='lines', name='执行价以下水平线',
                line=dict(color='royalblue', width=3)
            ))

            # 第二段：执行价到障碍价的斜线增长
            fig.add_trace(go.Scatter(
                x=[strike_price, barrier_price],
                y=[0, payoff],
                mode='lines', name='斜线增长段',
                line=dict(color='seagreen', width=3)
            ))

            # 第三段：障碍价处跳变到固定回报
            fig.add_trace(go.Scatter(
                x=[barrier_price, barrier_price],
                y=[payoff, rebate_rate],
                mode='lines', name='障碍跳变',
                line=dict(color='crimson', width=3, dash='dot')
            ))

            # 第四段：障碍价之后水平线
            fig.add_trace(go.Scatter(
                x=[barrier_price, x_end],
                y=[rebate_rate, rebate_rate],
                mode='lines', name='障碍后水平线',
                line=dict(color='darkorange', width=3)
            ))

        else:
            # 看跌鲨鱼鳍
            payoff = (strike_price - barrier_price) * pr / term_years

            x_start = barrier_price - 10
            x_end = strike_price + 10
            max_y = max(payoff, rebate_rate) + 10

            # 第一段：障碍价之前水平线0%
            fig.add_trace(go.Scatter(
                x=[x_start, barrier_price],
                y=[0, 0],
                mode='lines', name='障碍价以下水平线',
                line=dict(color='royalblue', width=3)
            ))

            # 第二段：障碍价处跳变到 payoff
            fig.add_trace(go.Scatter(
                x=[barrier_price, barrier_price],
                y=[0, payoff],
                mode='lines', name='障碍跳变',
                line=dict(color='crimson', width=3, dash='dot')
            ))

            # 第三段：障碍价到执行价的斜线下降到 rebate
            fig.add_trace(go.Scatter(
                x=[barrier_price, strike_price],
                y=[payoff, rebate_rate],
                mode='lines', name='斜线下降段',
                line=dict(color='seagreen', width=3)
            ))

            # 第四段：执行价之后水平线
            fig.add_trace(go.Scatter(
                x=[strike_price, x_end],
                y=[rebate_rate, rebate_rate],
                mode='lines', name='执行价后水平线',
                line=dict(color='darkorange', width=3)
            ))

        fig.update_layout(
            title=dict(
                text="鲨鱼鳍年化收益率示意图",
                font=dict(size=24, color='black'),
                x=0.5,
            ),
            xaxis_title="标的价格",
            yaxis_title="年化收益率 (%)",
            xaxis=dict(
                range=[x_start - (x_end - x_start) * 0.1, x_end + (x_end - x_start) * 0.1],
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                zeroline=True,
                zerolinecolor='gray'
            ),
            yaxis=dict(
                range=[0, max_y],
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                zeroline=True,
                zerolinecolor='gray'
            ),
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        **图表说明:**
        - **执行价格 K**: {strike_price}
        - **障碍价格 B**: {barrier_price}
        - 手动选择方向: **{direction}**
        - 绘制了完整的鲨鱼鳍结构变化
        """)

    else:
        st.info("请在上方输入参数，然后点击“生成鲨鱼鳍收益分析图”。")

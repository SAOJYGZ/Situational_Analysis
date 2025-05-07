import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render():
    st.header("雪球情景分析")
    st.subheader("开发中...请勿使用！")

    # 1) 产品类型选择（后续可扩充更多）
    product = st.selectbox("选择产品类型", ["Snowball"], index=0)
    st.subheader(f"{product} 参数输入模板")

    # 2) 参数输入表单
    with st.form(key="params_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            term = st.text_input("期限", value="24M")
            ko_barrier = st.number_input("敲出障碍价格 (%)", min_value=0.0, max_value=200.0, value=105.0)
            ki_barrier = st.number_input("敲入障碍价格 (%)", min_value=0.0, max_value=200.0, value=70.0)
            obs_style = st.selectbox("敲入观察方式", ["每日观察", "到期观察"])
        with col2:
            participation = st.number_input("参与率 (%)", min_value=0.0, max_value=500.0, value=100.0)
            coupon_rate = st.number_input("票息率 (%)", min_value=0.0, max_value=100.0, value=5.0)
            margin_ratio = st.number_input("保证金比例 (%)", min_value=0.0, max_value=100.0, value=100.0)
        with col3:
            max_loss = st.number_input("最大亏损比例 (%)", min_value=0.0, max_value=100.0, value=100.0)
            st.write("")  # 占位
            st.write("")
        submitted = st.form_submit_button("生成分析图表")

    if submitted:
        # 参数汇总表
        params = {
            "期限": term,
            "敲出障碍价格": f"{ko_barrier:.2f}%",
            "敲入障碍价格": f"{ki_barrier:.2f}%",
            "敲入观察方式": obs_style,
            "参与率": f"{participation:.2f}%",
            "票息率": f"{coupon_rate:.2f}%",
            "保证金比例": f"{margin_ratio:.2f}%",
            "最大亏损比例": f"{max_loss:.2f}%"
        }
        df_params = (
            pd.DataFrame.from_dict(params, orient="index", columns=["值"])  
              .reset_index().rename(columns={"index": "参数"})
        )
        st.table(df_params)

        # 解析期限（月数）
        try:
            months = int(term.rstrip("M"))
        except:
            months = 24

        # 时间序列：0 到 months
        time = np.arange(0, months + 1)

        # 模拟标的价格路径（示例随机过程，可替换为真实数据）
        dt = 1/12
        mu = 0.0
        vol = 0.2
        prices = [100]
        for _ in range(months):
            shock = np.random.normal((mu - 0.5 * vol**2) * dt, vol * np.sqrt(dt))
            prices.append(prices[-1] * np.exp(shock))
        prices = np.array(prices)

        # 检测敲入/敲出事件
        ki_events = np.where(prices <= ki_barrier)[0]
        ko_events = np.where(prices >= ko_barrier)[0]
        ki_date = int(ki_events[0]) if ki_events.size > 0 else None
        ko_date = int(ko_events[0]) if ko_events.size > 0 else None

        # 计算事件说明
        if ko_date is not None and ko_date > 0:
            end_msg = f"第{ko_date}月敲出，产品提前结束"
        else:
            if ki_date is not None:
                end_msg = f"到期未敲出，已发生敲入（第{ki_date}月）"
            else:
                end_msg = f"到期未敲出且未敲入"

        # 绘制路径与事件图
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time, y=prices,
            mode='lines', name='标的价格', line=dict(width=2)
        ))
        # 障碍线
        fig.add_shape(type='line', x0=0, x1=months, y0=ki_barrier, y1=ki_barrier,
                      line=dict(color='blue', width=1, dash='dash'))
        fig.add_shape(type='line', x0=0, x1=months, y0=ko_barrier, y1=ko_barrier,
                      line=dict(color='green', width=1, dash='dash'))
        # 事件标记
        if ki_date is not None:
            fig.add_trace(go.Scatter(
                x=[ki_date], y=[prices[ki_date]], mode='markers', name='敲入',
                marker=dict(symbol='x', size=10, color='blue')
            ))
        if ko_date is not None:
            fig.add_trace(go.Scatter(
                x=[ko_date], y=[prices[ko_date]], mode='markers', name='敲出',
                marker=dict(symbol='star', size=12, color='green')
            ))

        fig.update_layout(
            title='标的价格路径与敲入/敲出事件',
            xaxis_title='时间（月）', yaxis_title='标的价格 (%)',
            xaxis=dict(range=[0, months]), yaxis=dict(range=[prices.min()*0.9, prices.max()*1.1]),
            legend=dict(orientation='h', y=1.05, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig, use_container_width=True)

        # 事件说明输出
        st.write(end_msg)

        # ————— 新增：雪球产品收益示意图 —————
        st.subheader("Snowball 产品收益示意图")
        scenario = st.selectbox(
            "选择收益场景", 
            ["到期前敲出", "到期前没有敲入敲出", "敲入未敲出", "敲入后提前敲出"]
        )
        # 场景额外输入
        ko_month = None
        ki_month = None
        final_price = None
        if scenario == "到期前敲出":
            ko_month = st.slider("敲出发生月", 1, months-1, value=int(months/2))
        elif scenario == "敲入未敲出":
            final_price = st.number_input(
                "到期标的价格 (%) (≤ 敲入障碍)", 0.0, float(ki_barrier), value=float(ki_barrier*0.9)
            )
        elif scenario == "敲入后提前敲出":
            ki_month = st.slider("敲入发生月", 1, months-1, value=int(months/4))
            ko_month = st.slider("敲出发生月", ki_month+1, months-1, value=int(months/2))

        # 构建收益曲线
        payoff = np.zeros_like(time, dtype=float)
        # 到期前敲出
        if scenario == "到期前敲出":
            accrual = coupon_rate * (ko_month/12)
            payoff = 100 + coupon_rate * (time/12)
            payoff[time >= ko_month] = 100 + accrual
        # 到期前没有敲入敲出
        elif scenario == "到期前没有敲入敲出":
            payoff = 100 + coupon_rate * (time/12)
        # 敲入未敲出
        elif scenario == "敲入未敲出":
            payoff[:] = 100
            payoff[-1] = final_price
        # 敲入后提前敲出
        elif scenario == "敲入后提前敲出":
            accrual = coupon_rate * (ko_month/12)
            payoff = 100 + coupon_rate * (time/12)
            payoff[time >= ko_month] = 100 + accrual

        # 绘制收益示意图
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=time, y=payoff, mode='lines+markers', name='兑付水平',
            line=dict(width=2)
        ))
        # 障碍线标注
        fig2.add_shape(type='line', x0=0, x1=months, y0=100+coupon_rate, y1=100+coupon_rate,
                       line=dict(color='gray', width=1, dash='dash'))
        fig2.add_annotation(x=months, y=100+coupon_rate, text='本金+票息', showarrow=False, xanchor='right')
        if ko_barrier:
            fig2.add_shape(type='line', x0=0, x1=months, y0=100, y1=100,
                           line=dict(color='black', width=1, dash='dot'))
        fig2.update_layout(
            title='不同场景下 Snowball 产品收益示意',
            xaxis_title='时间（月）', yaxis_title='兑付 (%)',
            xaxis=dict(range=[0, months]),
            yaxis=dict(range=[min(payoff.min(), 90), max(payoff.max(), 110)])
        )
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("请在上方输入参数，然后点击'生成分析图表'")


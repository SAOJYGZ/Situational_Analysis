import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from api import get_price_data

def render():
    
    st.title("雪球结构产品收益模拟与可视化")

    # 1. 参数输入
    st.header("参数输入")

    # 将标的改为下拉预设列表
    PRESET_CODES = ["000016.SH", "000300.SH", "000905.SH", "000852.SH"]
    underlying_code = st.selectbox("挂钩标的代码", PRESET_CODES, index=3)

    knock_in_pct    = st.number_input("敲入障碍价格 (%)", value=70.0, min_value=0.0, max_value=100.0)
    start_price     = st.number_input("产品期初价格 (点位)", value=100.0, min_value=0.0)
    start_date      = st.date_input("产品开始日期", value=pd.to_datetime("2025-05-08").date())

    obs_dates_input = st.text_area(
        "敲出观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/06/09, 2025/07/08, 2025/08/08, 2025/09/08, 2025/10/09\n"
        "2025/11/10, 2025/12/08, 2026/01/08, 2026/02/09, 2026/03/09\n"
        "2026/04/08, 2026/05/08, 2026/06/08, 2026/07/08, 2026/08/10\n"
        "2026/09/08, 2026/10/08, 2026/11/09, 2026/12/08, 2027/01/08\n"
        "2027/02/12, 2027/03/08, 2027/04/08, 2027/05/10"
    )
    obs_barriers_input = st.text_area(
        "对应敲出障碍价格 (%) 列表 (与观察日一一对应)",
        "\n".join(["100.00%"]*24)
    )
    obs_coupons_input = st.text_area(
        "对应敲出票息 (%) 列表 (与观察日一一对应)",
        "\n".join(["2.34%"]*24)
    )
    sim_start_date = st.date_input(
        "模拟数据开始日期 (用于历史模拟)",
        value=pd.to_datetime("2022-03-01").date()
    )

    # ---- 解析输入 ----
    def parse_date_list(s: str):
        parts = [x.strip() for x in s.replace("\n",",").split(",") if x.strip()]
        res = []
        for p in parts:
            try:
                res.append(pd.to_datetime(p).date())
            except:
                st.error(f"日期格式错误: {p}")
                return []
        return res

    def parse_pct_list(s: str):
        parts = [x.strip() for x in s.replace("\n",",").split(",") if x.strip()]
        res = []
        for p in parts:
            if p.endswith("%"):
                p = p[:-1]
            try:
                res.append(float(p)/100.0)
            except:
                st.error(f"百分比格式错误: {p}")
                return []
        return res

    obs_dates    = parse_date_list(obs_dates_input)
    obs_barriers = parse_pct_list(obs_barriers_input)
    obs_coupons  = parse_pct_list(obs_coupons_input)

    if not (len(obs_dates)==len(obs_barriers)==len(obs_coupons)):
        st.error("观察日、障碍价、票息 列表长度必须一致")
        st.stop()

    # 敲入/敲出映射
    knock_in_level    = start_price * (knock_in_pct/100.0)
    obs_barrier_lvls  = [start_price*p for p in obs_barriers]
    obs_dict          = {obs_dates[i]: obs_barrier_lvls[i] for i in range(len(obs_dates))}
    coupon_dict       = {obs_dates[i]: obs_coupons[i]         for i in range(len(obs_dates))}

    # ---- 图1: 理论收益曲线 ----
    st.header("图1：雪球产品理论收益曲线")
    final_coupon_rate = obs_coupons[-1] if obs_coupons else 0.0

    x_perc = np.linspace(0, 1.5, 301)*100  # 0%–150%
    payoff_knockin    = [(min(fp,100)/100)*100 for fp in x_perc]  # 最低保本
    payoff_no_knockin = [(1+final_coupon_rate)*100 for _ in x_perc]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=x_perc, y=payoff_knockin,
        mode="lines", name="快乐的线条", line=dict(color="red")
    ))
    # fig1.add_trace(go.Scatter(
    #     x=x_perc, y=payoff_no_knockin,
    #     mode="lines", name="未发生敲入", line=dict(color="green", dash="dash")
    # ))
    fig1.add_vline(
        x=knock_in_pct, line_dash="dot", line_color="red",
        annotation_text=f"敲入障碍 {knock_in_pct:.1f}%", annotation_position="bottom left"
    )
    fig1.add_vline(
        x=100, line_dash="dot", line_color="gray",
        annotation_text="敲出障碍价格 100%", annotation_position="bottom right"
    )
    fig1.update_layout(
        title="雪球产品理论收益曲线",
        xaxis_title="标的最终价格 / 期初价格 (%)",
        yaxis_title="产品最终收益 (% 相对本金)",
        template="plotly_white"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ---- 图2: 历史模拟价格路径 ----
    st.header("图2：历史模拟价格路径")
    final_date  = obs_dates[-1]
    period_days = (pd.to_datetime(final_date) - pd.to_datetime(start_date)).days

    # 从接口拉取历史
    raw = get_price_data(
        codes=[underlying_code],
        start_date=sim_start_date.strftime("%Y-%m-%d"),
        end_date  =(sim_start_date + datetime.timedelta(days=period_days+30)).strftime("%Y-%m-%d")
    )
    hist = raw.get(underlying_code, [])
    if not hist:
        st.error("无法获取历史数据，请检查接口")
        st.stop()

    df = pd.DataFrame(hist)
    df["date"] = pd.to_datetime(df["date"])
    price_col = "close" if "close" in df else df.columns[1]
    df["price"] = df[price_col].astype(float)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 日收益率
    df["ret"] = df["price"].pct_change()
    rets = df["ret"].dropna().values

    # 构造模拟路径
    sim_prices, sim_dates = [start_price],[pd.to_datetime(start_date)]
    knock_ined=False; knock_out=False
    knock_in_date=knock_out_date=None

    for r in rets:
        if knock_out: break
        new_p = sim_prices[-1]*(1+r)
        next_dt = sim_dates[-1] + pd.tseries.offsets.BDay(1)
        sim_prices.append(new_p)
        sim_dates.append(next_dt)

        if not knock_ined and new_p<knock_in_level:
            knock_ined, knock_in_date = True, next_dt
        if next_dt.date() in obs_dict and not knock_out:
            lvl = obs_dict[next_dt.date()]
            if new_p>=lvl:
                knock_out, knock_out_date = True, next_dt
                break

    if knock_out and knock_out_date:
        idx = sim_dates.index(knock_out_date)
        sim_dates, sim_prices = sim_dates[:idx+1], sim_prices[:idx+1]

    sim_df = pd.DataFrame({"date":sim_dates,"price":sim_prices}).set_index("date")

    # 绘制
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=sim_df.index, y=sim_df["price"],
        mode="lines", name="模拟价格", line=dict(color="#2b6cb0")
    ))
    # 敲入线
    fig2.add_trace(go.Scatter(
        x=[sim_df.index[0], sim_df.index[-1]],
        y=[knock_in_level]*2,
        mode="lines", name="敲入线",
        line=dict(color="red", dash="dash"),
        hovertemplate="敲入障碍: %{y:.2f}<extra></extra>"
    ))
    # 敲出点
    xs, ys = [], []
    for d,lvl in obs_dict.items():
        dt = pd.to_datetime(d)
        if dt in sim_df.index:
            xs.append(dt); ys.append(lvl)
    if xs:
        fig2.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers", name="敲出障碍价",
            marker=dict(symbol="diamond", color="green", size=8),
            hovertemplate="敲出障碍: %{y:.2f}<extra></extra>"
        ))
    # 事件标记
    if knock_in_date:
        fig2.add_vline(x=knock_in_date, line_dash="dot", line_color="red")
        fig2.add_annotation(
            x=knock_in_date, y=max(sim_prices),
            text="敲入发生", showarrow=True, arrowhead=1,
            yanchor="bottom", font=dict(color="red")
        )
    if knock_out_date:
        fig2.add_vline(x=knock_out_date, line_dash="dot", line_color="green")
        fig2.add_annotation(
            x=knock_out_date, y=max(sim_prices),
            text="敲出发生", showarrow=True, arrowhead=1,
            yanchor="bottom", font=dict(color="green")
        )

    fig2.update_layout(
        title="历史模拟价格路径",
        xaxis_title="日期",
        yaxis_title="价格",
        template="plotly_white"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 事件结果
    st.header("事件结果")
    if knock_out_date:
        i = obs_dates.index(knock_out_date.date())
        st.write(f"- 敲出: {knock_out_date.date()}，票息 {obs_coupons[i]*100:.2f}% 并返还本金")
    elif knock_ined:
        st.write(f"- 敲入: {knock_in_date.date()}，最终价格 {sim_prices[-1]:.2f}")
    else:
        st.write("- 未敲入、未敲出；持有至到期，获得全部票息。")

import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from api import get_price_data

def render():
    st.title("雪球结构产品收益模拟")

    # -------------------------------
    # 1. 参数输入
    # -------------------------------
    st.header("参数输入")

    PRESET_CODES = ["000016.SH", "000300.SH", "000905.SH", "000852.SH"]
    underlying_code = st.selectbox("挂钩标的代码", PRESET_CODES, index=3)
    notional_principal = st.number_input("名义本金 (万元)", value=100.0, min_value=0.0)

    knock_in_pct = st.number_input("敲入障碍价格 (%)", value=70.0, min_value=0.0, max_value=100.0)
    start_price  = st.number_input("产品期初价格 (点位)", value=100.0, min_value=0.0)
    start_date   = st.date_input("产品开始日期", value=pd.to_datetime("2025-05-08").date())

    obs_dates_input = st.text_area(
        "敲出观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/06/09,2025/07/08,2025/08/08,2025/09/08,2025/10/09\n"
        "2025/11/10,2025/12/08,2026/01/08,2026/02/09,2026/03/09\n"
        "2026/04/08,2026/05/08,2026/06/08,2026/07/08,2026/08/10\n"
        "2026/09/08,2026/10/08,2026/11/09,2026/12/08,2027/01/08\n"
        "2027/02/12,2027/03/08,2027/04/08,2027/05/10"
    )
    obs_barriers_input = st.text_area(
        "对应敲出障碍价格 (%) 列表 (与观察日一一对应)",
        "\n".join(["100.00%"]*24)
    )
    obs_coupons_input = st.text_area(
        "对应敲出票息 (%) 列表 (与观察日一一对应)",
        "\n".join(["2.34%"]*24)
    )

    dividend_mode = st.selectbox("红利票息来源", ["同敲出票息", "自行输入"], index=0)
    if dividend_mode == "同敲出票息":
        # 解析观察日票息后取最后一期
        def parse_pct_list(s: str):
            parts = [x.strip() for x in s.replace("\n",",").split(",") if x.strip()]
            return [float(p.rstrip("%"))/100.0 for p in parts]
        dividend_input = parse_pct_list(obs_coupons_input)
        dividend_rate = dividend_input[-1] if dividend_input else 0.0
    else:
        dividend_input = st.number_input("红利票息 (%)", value=2.34, min_value=0.0)
        dividend_rate = dividend_input / 100.0

    margin_input = st.number_input("保证金比例 (%)", value=100.0, min_value=0.0, max_value=100.0)
    margin_ratio = margin_input / 100.0

    max_loss_input = st.number_input("最大亏损比例 (%)", value=100.0, min_value=0.0, max_value=100.0)
    max_loss_ratio = max_loss_input / 100.0

    
    # ---- 解析敲出列表 ----
    def parse_date_list(s: str):
        parts = [x.strip() for x in s.replace("\n",",").split(",") if x.strip()]
        return [pd.to_datetime(p).date() for p in parts]

    def parse_pct_list(s: str):
        parts = [x.strip() for x in s.replace("\n",",").split(",") if x.strip()]
        return [float(p.rstrip("%"))/100.0 for p in parts]

    obs_dates    = parse_date_list(obs_dates_input)
    obs_barriers = parse_pct_list(obs_barriers_input)
    obs_coupons  = parse_pct_list(obs_coupons_input)

    if not (len(obs_dates)==len(obs_barriers)==len(obs_coupons)):
        st.error("观察日、障碍价、票息 列表长度必须一致")
        return

    # 映射
    knock_in_level   = start_price * (knock_in_pct/100.0)
    obs_barrier_lvls = [start_price*p for p in obs_barriers]
    obs_dict         = dict(zip(obs_dates, obs_barrier_lvls))

    # -------------------------------
    # 2. 图1: 理论收益曲线（需修改）
    # -------------------------------
    st.header("图1：雪球产品理论收益曲线")
    final_coupon_rate = dividend_rate

    x_perc = np.linspace(0,1.5,301)*100
    payoff_knockin    = [(min(fp,100)/100)*100 for fp in x_perc]
    payoff_no_knockin = [(1+final_coupon_rate)*100 for _ in x_perc]

    # 考虑保证金比例：收益相对于初始保证金
    payoff_knockin   = [100 + (v-100)*margin_ratio for v in payoff_knockin]
    payoff_no_knockin= [100 + (v-100)*margin_ratio for v in payoff_no_knockin]

    # 考虑最大亏损比例：敲入后的最小收益不会低于 (1 - max_loss_ratio)*100
    min_payoff = (1 - max_loss_ratio)*100
    payoff_knockin = [max(v, min_payoff) for v in payoff_knockin]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=x_perc, y=payoff_knockin, mode="lines",
                              name="敲入已触发", line=dict(color="red")))
    fig1.add_trace(go.Scatter(x=x_perc, y=payoff_no_knockin, mode="lines",
                              name="未发生敲入", line=dict(color="green", dash="dash")))
    fig1.add_vline(x=knock_in_pct, line_dash="dot", line_color="red",
                   annotation_text=f"敲入障碍 {knock_in_pct:.1f}%", annotation_position="bottom left")
    fig1.add_vline(x=100, line_dash="dot", line_color="gray",
                   annotation_text="期初价 100%", annotation_position="bottom right")
    fig1.update_layout(title="雪球产品理论收益曲线",
                       xaxis_title="标的最终价格 / 期初价格 (%)",
                       yaxis_title="收益 (% 相对保证金)", template="plotly_white")
    st.plotly_chart(fig1, use_container_width=True)

    # -------------------------------
    # 3. 图2: 历史模拟价格路径
    # -------------------------------
    st.header("图2：历史模拟价格路径")
    final_obs = obs_dates[-1]

    # 1) 天数
    period_days = (pd.to_datetime(final_obs) - pd.to_datetime(start_date)).days

    sim_start_date = st.date_input(
        "模拟数据开始日期 (用于历史模拟)",
        value=pd.to_datetime("2022-03-01").date()
    )

    # 2) 拉取历史
    fetch_end = sim_start_date + datetime.timedelta(days=period_days+90)
    raw = get_price_data([underlying_code],
                         sim_start_date.strftime("%Y-%m-%d"),
                         fetch_end.strftime("%Y-%m-%d"))
    hist = raw.get(underlying_code, [])
    if not hist:
        st.error("无法获取历史数据")
        return

    df = pd.DataFrame(hist)
    df["date"]  = pd.to_datetime(df["date"])
    price_col   = "close" if "close" in df else df.columns[1]
    df["price"] = df[price_col].astype(float)
    df.sort_values("date",inplace=True)
    df.reset_index(drop=True,inplace=True)

    # 3) 日度收益率
    df["ret"] = df["price"].pct_change()
    rets = df["ret"].dropna().values

    # 4) 生成交易日
    sim_dates = pd.bdate_range(start_date, final_obs)
    N = len(sim_dates)

    # 5) 补齐或截取
    if len(rets) < N-1:
        rets = np.concatenate([rets, np.zeros(N-1-len(rets))])
    else:
        rets = rets[:N-1]

    # 6) 滚动模拟
    sim_prices = [start_price]
    knock_ined = False
    knock_out  = False
    knock_in_date = knock_out_date = None

    for i,r in enumerate(rets):
        if knock_out: break
        new_p = sim_prices[-1] * (1 + r)
        today = sim_dates[i+1]
        sim_prices.append(new_p)

        if not knock_ined and new_p < knock_in_level:
            knock_ined, knock_in_date = True, today
        if today.date() in obs_dict and not knock_out:
            if new_p >= obs_dict[today.date()]:
                knock_out, knock_out_date = True, today
                break

    if knock_out and knock_out_date:
        idx = list(sim_dates).index(knock_out_date)
        sim_dates = sim_dates[:idx+1]
        sim_prices= sim_prices[:idx+1]

    sim_df = pd.DataFrame({"price":sim_prices}, index=sim_dates)

    # 7) 绘制图2
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df.index, y=sim_df["price"],
                              mode="lines", name="模拟价格"))
    fig2.add_trace(go.Scatter(
        x=[sim_df.index[0], sim_df.index[-1]],
        y=[knock_in_level]*2,
        mode="lines", name="敲入线",
        line=dict(color="red", dash="dash"),
        hovertemplate="敲入: %{y:.2f}<extra></extra>"
    ))
    xs, ys = [], []
    for d,lvl in obs_dict.items():
        dt = pd.to_datetime(d)
        if dt in sim_df.index:
            xs.append(dt); ys.append(lvl)
    if xs:
        fig2.add_trace(go.Scatter(x=xs, y=ys, mode="markers",
                                  name="敲出障碍价",
                                  marker=dict(size=8, color="green"),
                                  hovertemplate="敲出: %{y:.2f}<extra></extra>"))
    if knock_in_date:
        fig2.add_vline(x=knock_in_date, line_dash="dot", line_color="red")
        fig2.add_annotation(x=knock_in_date, y=max(sim_prices),
                            text="敲入", showarrow=True, arrowhead=1, font=dict(color="red"))
    if knock_out_date:
        fig2.add_vline(x=knock_out_date, line_dash="dot", line_color="green")
        fig2.add_annotation(x=knock_out_date, y=max(sim_prices),
                            text="敲出", showarrow=True, arrowhead=1, font=dict(color="green"))

    fig2.update_layout(title="历史模拟价格路径",
                       xaxis_title="日期", yaxis_title="价格",
                       template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

    # -------------------------------
    # 4. 事件结果
    # -------------------------------
    st.header("事件结果")
    if knock_out_date:
        # 找到敲出对应的票息
        idx = obs_dates.index(knock_out_date.date())
        coupon = obs_coupons[idx]  # 小数形式，例如0.0234
        
        # 计算存续工作日天数：sim_df 的索引到敲出日位置 +1
        active_days = sim_df.index.get_loc(knock_out_date) + 1
        
        # 计算收益（万元）
        payoff = notional_principal * coupon * active_days / 365
        
        st.write(
            f"- 敲出发生日期：{knock_out_date.date()}  \n"
            f"- 产品存续工作日：{active_days} 天  \n"
            f"- 敲出票息（年化）：{coupon*100:.2f}%  \n"
            f"- 收益：{payoff:.2f} 万元"
        )
    elif knock_ined:
        # 敲入发生但未敲出
        final_price = sim_prices[-1]
        # 计算亏损百分比 = (期初点位 - 最后观察日点位) / 期初点位
        loss_pct = (start_price - final_price) / start_price
        # 最大亏损限额 = max_loss_ratio
        capped_loss_pct = min(loss_pct, max_loss_ratio)
        # 亏损金额（万元）
        loss_amount = capped_loss_pct * notional_principal

        st.write(
            f"- 敲入发生日期：{knock_in_date.date()}  \n"
            f"- 最后观察日价格：{final_price:.2f}  \n"
            f"- 按(期初价 - 最后价)/期初价 计算亏损：{loss_pct*100:.2f}%  \n"
            f"- 应用最大亏损上限：{capped_loss_pct*100:.2f}%  \n"
            f"- 亏损金额：{loss_amount:.2f} 万元"
        )
    else:
        payoff = notional_principal * dividend_rate * margin_ratio
        st.write(f"- 产品到期，未敲入未敲出，获得红利票息收益 {payoff:.2f} 万元")
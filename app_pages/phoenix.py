import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from api import get_price_data

def render():
    st.title("凤凰结构产品收益模拟")

    # -------------------------------
    # 1. 参数输入
    # -------------------------------
    st.header("参数输入")

    PRESET_CODES = ["000016.SH","000300.SH","000905.SH","000852.SH","513180.SH"]
    underlying_code          = st.selectbox("挂钩标的代码", PRESET_CODES, index=3)
    notional_principal       = st.number_input("名义本金 (万元)", value=100.0, min_value=0.0)

    knock_in_pct             = st.number_input("敲入障碍价格 (%)", value=70.0, min_value=0.0, max_value=100.0)
    dividend_barrier_pct     = st.number_input("派息障碍价格 (%)", value=70.0, min_value=0.0, max_value=500.0)/100.0
    start_price              = st.number_input("产品期初价格 (点位)", value=100.0, min_value=0.0)
    start_date               = st.date_input("产品开始日期", value=pd.to_datetime("2025-05-20").date())

    # 派息观察日列表
    obs_dividend_dates_input = st.text_area(
        "派息观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/06/20,2025/07/21,2025/08/20,2025/09/22,2025/10/20\n"
        "2025/11/20,2025/12/22,2026/01/20,2026/02/24,2026/03/20\n"
        "2026/04/20,2026/05/20,2026/06/22,2026/07/20,2026/08/20\n"
        "2026/09/21,2026/10/20,2026/11/20,2026/12/21,2027/01/20\n"
        "2027/02/22,2027/03/22,2027/04/20,2027/05/20"
    )
    # 每月绝对派息率输入
    obs_dividend_rates_input = st.text_area(
        "每月绝对派息率 (%) 列表 (与派息观察日一一对应)",
        "\n".join(["1.16%"]*24)
    )
    # 敲出观察日列表
    obs_dates_input          = st.text_area(
        "敲出观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/08/20,2025/09/22,2025/10/20,2025/11/20,2025/12/22\n"
        "2026/01/20,2026/02/24,2026/03/20,2026/04/20,2026/05/20\n"
        "2026/06/22,2026/07/20,2026/08/20,2026/09/21,2026/10/20\n"
        "2026/11/20,2026/12/21,2027/01/20,2027/02/22,2027/03/22\n"
        "2027/04/20,2027/05/20"
    )
    # 敲出障碍价格列表
    obs_barriers_input        = st.text_area(
        "敲出障碍价格 (%) 列表 (与观察日一一对应)",
        "\n".join([
            "100.00%","99.50%","99.00%","98.50%","98.00%","97.50%","97.00%","96.50%","96.00%","95.50%",
            "95.00%","94.50%","94.00%","93.50%","93.00%","92.50%","92.00%","91.50%","91.00%","90.50%",
            "90.00%","89.50%"
        ])
    )

    max_loss_ratio            = st.number_input("最大亏损比例 (%)", value=100.0, min_value=0.0, max_value=100.0)/100.0
    knock_in_strike_pct       = st.number_input("敲入执行价格 (%)", value=100.0, min_value=0.0, max_value=200.0) / 100.0
    participation_rate        = st.number_input("敲入参与率 (%)", value=100.0, min_value=0.0, max_value=500.0) / 100.0
    knock_in_style            = st.selectbox("敲入观察方式", ["每日观察","到期观察"], index=0)
    sim_start_date            = st.date_input(
        "模拟数据开始日期 (用于历史模拟)",
        value=pd.to_datetime("2022-03-01").date()
    )

    # 等待按钮触发
    if not st.button("生成分析图表"):
        st.info("请填写完参数后，点击“生成分析图表”")
        return

    # ---- 解析文本输入 ----
    def parse_date_list(s: str):
        out = []
        for x in s.replace("\n",",").split(","):
            x = x.strip()
            if not x: continue
            try:
                out.append(pd.to_datetime(x).date())
            except:
                continue
        return out

    def parse_pct_list(s: str):
        out = []
        for x in s.replace("\n",",").split(","):
            x = x.strip().rstrip("%")
            if not x: continue
            try:
                out.append(float(x)/100.0)
            except:
                continue
        return out

    # 解析后的派息列表
    obs_dividend_dates        = parse_date_list(obs_dividend_dates_input)
    obs_dividend_rates        = parse_pct_list(obs_dividend_rates_input)
    # 解析后的敲出列表
    obs_dates                 = parse_date_list(obs_dates_input)
    obs_barriers              = parse_pct_list(obs_barriers_input)

    # 校验长度
    if len(obs_dividend_dates) != len(obs_dividend_rates):
        st.error("派息观察日与派息率列表长度不一致")
        return
    if len(obs_dates) != len(obs_barriers):
        st.error("敲出观察日与敲出障碍价列表长度不一致")
        return

    # 构造映射
    dividend_dict             = dict(zip(obs_dividend_dates, obs_dividend_rates))
    obs_barrier_levels        = [start_price * p for p in obs_barriers]
    obs_dict                  = dict(zip(obs_dates, obs_barrier_levels))
    knock_in_level            = start_price * knock_in_pct / 100.0

    # -------------------------------
    # 2. 图1：收益示意（待实现）
    # -------------------------------
    st.header("图1：收益示意（待实现）")

    # -------------------------------
    # 3. 图2：历史模拟价格路径
    # -------------------------------
    st.header("图2：历史模拟价格路径")
    final_obs                 = obs_dates[-1]
    period_days               = (pd.to_datetime(final_obs) - pd.to_datetime(start_date)).days
    fetch_end                 = sim_start_date + datetime.timedelta(days=period_days + 90)

    # 拉取历史
    raw                       = get_price_data([underlying_code],
                                               sim_start_date.strftime("%Y-%m-%d"),
                                               fetch_end.strftime("%Y-%m-%d"))
    hist                      = raw.get(underlying_code, [])
    if not hist:
        st.error("无法获取历史数据")
        return

    df = pd.DataFrame(hist)
    df["date"]              = pd.to_datetime(df["date"])
    price_col                = "close" if "close" in df else df.columns[1]
    df["price"]            = df[price_col].astype(float)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["ret"]              = df["price"].pct_change().fillna(0)

    # 生成工作日索引
    sim_dates                = pd.bdate_range(start_date, final_obs)
    N                        = len(sim_dates)
    rets                     = df["ret"].values
    rets                     = np.concatenate([rets, np.zeros(max(0, N-1-len(rets)))])[:N-1]

    sim_prices               = [start_price]
    knock_ined               = False
    knock_out                = False
    knock_in_date            = knock_out_date = None
    dividend_events          = []

    # 模拟演算
    for i, r in enumerate(rets):
        if knock_out: break
        new_price             = sim_prices[-1] * (1 + r)
        today                 = sim_dates[i+1]
        sim_prices.append(new_price)

        # 敲入检测
        if knock_in_style == "每日观察" and not knock_ined and new_price < knock_in_level:
            knock_ined, knock_in_date = True, today
        # 敲出检测
        if today.date() in obs_dict and new_price >= obs_dict[today.date()]:
            knock_out, knock_out_date = True, today
            break
        # 派息检测
        if today.date() in dividend_dict:
            rate               = dividend_dict[today.date()]
            paid               = new_price >= start_price * dividend_barrier_pct
            amount             = notional_principal * rate
            dividend_events.append((today.date(), paid, rate, amount))

    # 到期敲入检测
    if not knock_out and knock_in_style == "到期观察" and sim_prices[-1] < knock_in_level:
        knock_ined, knock_in_date = True, sim_dates[-1]
    # 到期最后一次派息
    last_date               = sim_dates[-1].date()
    if last_date in dividend_dict and all(d[0] != last_date for d in dividend_events):
        rate               = dividend_dict[last_date]
        paid               = sim_prices[-1] >= start_price * dividend_barrier_pct
        amount             = notional_principal * rate
        dividend_events.append((last_date, paid, rate, amount))

    # 如提前敲出则截断序列
    if knock_out_date:
        idx                = sim_dates.get_indexer([knock_out_date])[0]
        sim_dates          = sim_dates[:idx+1]
        sim_prices         = sim_prices[:idx+1]

    sim_df                  = pd.DataFrame({"price": sim_prices}, index=sim_dates)

    # 绘制图2
    fig2 = go.Figure()
    # 价格路径
    fig2.add_trace(go.Scatter(x=sim_df.index, y=sim_df["price"], mode="lines", name="模拟价格"))
    # 敲入水平线
    fig2.add_shape(type="line",
                   x0=sim_df.index[0], x1=sim_df.index[-1],
                   y0=knock_in_level, y1=knock_in_level,
                   line=dict(color="red", dash="dash"))
    # 敲出点
    xs, ys = [], []
    for d, lvl in obs_dict.items():
        dt = pd.to_datetime(d)
        if dt in sim_df.index:
            xs.append(dt); ys.append(lvl)
    if xs:
        fig2.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name="敲出障碍价",
                                  marker=dict(color="green", size=8)))
    # 派息事件
    paid_x, paid_y, paid_cd     = [], [], []
    unpaid_x, unpaid_y, unpaid_cd = [], [], []
    for d, paid, rate, amount in dividend_events:
        dt = pd.to_datetime(d)
        if dt in sim_df.index:
            if paid:
                paid_x.append(dt); paid_y.append(sim_df.loc[dt, "price"]); paid_cd.append([rate, amount])
            else:
                unpaid_x.append(dt); unpaid_y.append(sim_df.loc[dt, "price"]); unpaid_cd.append([rate, amount])
    # 派息成功
    if paid_x:
        fig2.add_trace(go.Scatter(x=paid_x, y=paid_y, mode="markers", name="派息成功",
                                  marker=dict(symbol="star", color="red", size=12),
                                  hovertemplate="日期: %{x|%Y-%m-%d}<br>派息率: %{customdata[0]:.2%}<br>派息金额: %{customdata[1]:.2f} 万元<extra></extra>",
                                  customdata=paid_cd))
    # 未派息
    if unpaid_x:
        fig2.add_trace(go.Scatter(x=unpaid_x, y=unpaid_y, mode="markers", name="未派息",
                                  marker=dict(symbol="star", color="lightgray", size=12),
                                  hovertemplate="日期: %{x|%Y-%m-%d}<br>派息率: %{customdata[0]:.2%}<br>派息金额: %{customdata[1]:.2f} 万元<extra></extra>",
                                  customdata=unpaid_cd))
    # 敲入/敲出垂线
    if knock_in_date:
        fig2.add_shape(type="line", x0=knock_in_date, x1=knock_in_date,
                       y0=min(sim_prices), y1=max(sim_prices), line=dict(color="red", dash="dot"))
        fig2.add_annotation(x=knock_in_date, y=max(sim_prices), text="敲入", font=dict(color="red"), showarrow=True, arrowhead=1)
    if knock_out_date:
        fig2.add_shape(type="line", x0=knock_out_date, x1=knock_out_date,
                       y0=min(sim_prices), y1=max(sim_prices), line=dict(color="green", dash="dot"))
        fig2.add_annotation(x=knock_out_date, y=max(sim_prices), text="敲出", font=dict(color="green"), showarrow=True, arrowhead=1)
    fig2.update_layout(title="历史模拟价格路径", xaxis_title="日期", yaxis_title="价格", template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

    # -------------------------------
    # 4. 事件结果
    # -------------------------------
    st.header("事件结果")
    if knock_out_date:
        st.write(f"- 敲出日期：{knock_out_date.date()}，产品结束")
    elif knock_ined:
        # 敲入但未敲出：基于“敲入执行价格”和“敲入参与率”计算亏损
        final_price     = sim_prices[-1]
        final_pct       = final_price / start_price
        # 若 final_pct >= knock_in_strike_pct，则不亏；否则亏损 = strike - final_pct
        raw_loss_pct    = max(0.0, knock_in_strike_pct - final_pct)
        capped_loss_pct = min(raw_loss_pct, max_loss_ratio)
        loss_amt        = capped_loss_pct * notional_principal * participation_rate

        st.write(
            f"- 敲入发生日期：{knock_in_date.date()}  \n"
            f"- 最后观察日价格：{final_price:.2f}  \n"
            f"- 敲入执行价格：{knock_in_strike_pct*100:.2f}%  \n"
            f"- 按(执行价格-期末价格)/期初价 计算亏损：{raw_loss_pct*100:.2f}%  \n"
            f"- 应用最大亏损上限：{capped_loss_pct*100:.2f}%  \n"
            f"- 敲入参与率：{participation_rate*100:.2f}%  \n"
            f"- 亏损金额：{loss_amt:.2f} 万元"
        )
    else:
        st.write("- 未敲入/未敲出，产品结束")

    st.subheader("派息记录")
    if not dividend_events:
        st.write("无派息")
    else:
        # 仅输出“派息”/“未派息”和对应金额
        for d, paid, rate, amt in dividend_events:
            if paid:
                st.write(f" - {d} 派息 {amt:.2f} 万元")
            else:
                st.write(f" - {d} 未派息")

        st.write(
            f"- 共计应派息 {sum(d[3] for d in dividend_events):.2f} 万元，"
            f"获得派息 {sum(d[3] for d in dividend_events if d[1]):.2f} 万元，"
            f"未派息 {sum(d[3] for d in dividend_events if not d[1]):.2f} 万元"
        )

import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# 假设 api.py 文件和 get_price_data 函数已正确导入
from api import get_price_data # 假设这个导入在您的实际代码中存在


def calculate_theoretical_payoff(
    current_price, snowball_type, start_price,
    knock_in_pct, knock_in_strike_pct, participation_rate,
    guaranteed_return, max_loss_ratio,
    last_obs_barrier_pct, last_obs_coupon, dividend_rate, term_in_years
):
    """
    计算给定期末价格下的理论年化收益百分比。
    current_price: 标的资产在期末的价格
    返回值：理论年化收益百分比 (例如，收益10%返回0.10)
    """
    relative_price = current_price / start_price
    annualized_payoff_ratio = 0.0 # 默认值，如果未触发任何条件，可视为0

    # 1. 敲出区：如果期末价格达到或超过最后一个敲出障碍
    if relative_price >= last_obs_barrier_pct:
        annualized_payoff_ratio = last_obs_coupon # 直接是年化票息
    # 2. 无事件区：如果期末价格在敲入障碍和敲出障碍之间
    elif relative_price > knock_in_pct: # 并且相对价格 < last_obs_barrier_pct (由上面的if语句隐式涵盖)
        annualized_payoff_ratio = dividend_rate # 直接是年化红利票息
    # 3. 敲入区：如果期末价格低于或等于敲入障碍
    else: # relative_price <= knock_in_pct
        if snowball_type == "雪球":
            raw_loss_pct = max(0.0, knock_in_strike_pct - relative_price)
            capped_loss_pct = min(raw_loss_pct, max_loss_ratio)
            total_loss_ratio = capped_loss_pct * participation_rate
            # 将总损失年化，如果期限为0则避免除以0
            if term_in_years > 0:
                annualized_payoff_ratio = -total_loss_ratio / term_in_years
            else: # 理论上不应该出现term_in_years=0，但为健壮性考虑
                annualized_payoff_ratio = -total_loss_ratio
        else: # 三元雪球
            annualized_payoff_ratio = guaranteed_return # 三元雪球的敲入收益率通常就是年化的

    return annualized_payoff_ratio

def plot_theoretical_payoff(params):
    """
    绘制雪球产品理论年化收益曲线。
    params: 包含所有必要参数的字典
    """
    snowball_type = params["snowball_type"]
    # notional_principal = params["notional_principal"] # 不再需要，因为是百分比
    start_price = params["start_price"]
    knock_in_pct = params["knock_in_pct"]
    knock_in_strike_pct = params["knock_in_strike_pct"]
    participation_rate = params["participation_rate"]
    guaranteed_return = params["guaranteed_return"]
    max_loss_ratio = params["max_loss_ratio"]
    obs_dates = params["obs_dates"]
    obs_barriers = params["obs_barriers"]
    obs_coupons = params["obs_coupons"]
    dividend_rate = params["dividend_rate"]
    start_date = params["start_date"]

    if not obs_dates:
        st.warning("缺少敲出观察日列表，无法绘制理论收益曲线。")
        return

    final_obs_date = obs_dates[-1]
    last_obs_barrier_pct = obs_barriers[-1] if obs_barriers else 1.0
    last_obs_coupon = obs_coupons[-1] if obs_coupons else 0.0

    term_in_years = (pd.to_datetime(final_obs_date) - pd.to_datetime(start_date)).days / 365.0
    if term_in_years <= 0:
        st.error("产品开始日期晚于或等于最后一个敲出观察日，无法计算期限。请检查日期设置。")
        return

    min_price_factor = min(knock_in_pct * 0.8, 0.5)
    max_price_factor = max(last_obs_barrier_pct * 1.2, 1.5)
    price_range = np.linspace(start_price * min_price_factor, start_price * max_price_factor, 500) # 增加点数使曲线更平滑

    # 初始化三个独立的列表来绘制不同区域的曲线
    knock_in_region_x, knock_in_region_y = [], []
    no_event_region_x, no_event_region_y = [], []
    knock_out_region_x, knock_out_region_y = [], []

    for p in price_range:
        relative_price = p / start_price
        
        # 判断当前价格点属于哪个区域，并添加到相应的列表中
        if relative_price >= last_obs_barrier_pct:
            # 敲出区
            payoff = calculate_theoretical_payoff(
                p, snowball_type, start_price,
                knock_in_pct, knock_in_strike_pct, participation_rate,
                guaranteed_return, max_loss_ratio,
                last_obs_barrier_pct, last_obs_coupon, dividend_rate, term_in_years
            ) * 100 # 转换为百分比显示
            knock_out_region_x.append(p)
            knock_out_region_y.append(payoff)
        elif relative_price > knock_in_pct:
            # 无事件区
            payoff = calculate_theoretical_payoff(
                p, snowball_type, start_price,
                knock_in_pct, knock_in_strike_pct, participation_rate,
                guaranteed_return, max_loss_ratio,
                last_obs_barrier_pct, last_obs_coupon, dividend_rate, term_in_years
            ) * 100 # 转换为百分比显示
            no_event_region_x.append(p)
            no_event_region_y.append(payoff)
        else: # relative_price <= knock_in_pct
            # 敲入区
            payoff = calculate_theoretical_payoff(
                p, snowball_type, start_price,
                knock_in_pct, knock_in_strike_pct, participation_rate,
                guaranteed_return, max_loss_ratio,
                last_obs_barrier_pct, last_obs_coupon, dividend_rate, term_in_years
            ) * 100 # 转换为百分比显示
            knock_in_region_x.append(p)
            knock_in_region_y.append(payoff)

    fig = go.Figure()

    # 绘制敲入区曲线
    if knock_in_region_x: # 只有当列表非空时才添加trace
        fig.add_trace(go.Scatter(x=knock_in_region_x, y=knock_in_region_y, mode='lines', name='敲入区', line=dict(width=3, color='red')))
    # 绘制无事件区曲线
    if no_event_region_x: # 只有当列表非空时才添加trace
        fig.add_trace(go.Scatter(x=no_event_region_x, y=no_event_region_y, mode='lines', name='无事件区', line=dict(width=3, color='blue')))
    # 绘制敲出区曲线
    if knock_out_region_x: # 只有当列表非空时才添加trace
        fig.add_trace(go.Scatter(x=knock_out_region_x, y=knock_out_region_y, mode='lines', name='敲出区', line=dict(width=3, color='green')))


    # 添加关键的垂直和水平线
    fig.add_vline(x=start_price, line_dash="dot", line_color="grey",
                    annotation_text=f"期初价格({start_price:.2f})", annotation_position="top right")
    fig.add_vline(x=start_price * knock_in_pct, line_dash="dash", line_color="red",
                    annotation_text=f"敲入障碍({start_price * knock_in_pct:.2f})", annotation_position="bottom right")
    fig.add_vline(x=start_price * last_obs_barrier_pct, line_dash="dash", line_color="green",
                    annotation_text=f"敲出障碍({start_price * last_obs_barrier_pct:.2f})", annotation_position="top left")

    # 添加零收益线 (本金线)
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, annotation_text="本金线 (0% 年化收益)", annotation_position="top right")

    # 获取固定收益率值
    ko_yield = last_obs_coupon * 100 # 敲出年化收益率
    no_event_yield = dividend_rate * 100 # 无事件区年化收益率
    
    # 获取当前Y轴显示范围，用于调整注释位置
    all_payoffs = [val for sublist in [knock_in_region_y, no_event_region_y, knock_out_region_y] for val in sublist if val is not None]
    if all_payoffs:
        current_y_range = [min(all_payoffs), max(all_payoffs)]
    else:
        current_y_range = [0, 10] # 默认范围，以防万一

    # 调整注释的Y位置，避免重叠
    if current_y_range[1] == current_y_range[0]: # 避免除以0
        annotation_y_pos_dynamic = current_y_range[0] + 5 # 稍微向上偏移
    else:
        annotation_y_pos_dynamic = current_y_range[0] + (current_y_range[1] - current_y_range[0]) * 0.4 # 放在 Y 轴中下部

    # 添加区域注释和收益率
    # 敲出区注释
    if knock_out_region_x: # 确保敲出区有数据才添加注释
        fig.add_annotation(
            x=knock_out_region_x[0] + (knock_out_region_x[-1] - knock_out_region_x[0]) / 2, # 区域中心
            y=ko_yield, # 放置在固定收益线上
            text=f"敲出区<br>({ko_yield:.2f}% 年化)",
            showarrow=False,
            font=dict(color="green", size=10),
            yshift=20 # 向上微调
        )
    
    # 无事件区注释
    if no_event_region_x: # 确保无事件区有数据才添加注释
        fig.add_annotation(
            x=no_event_region_x[0] + (no_event_region_x[-1] - no_event_region_x[0]) / 2, # 区域中心
            y=no_event_yield, # 放置在固定收益线上
            text=f"无事件区<br>({no_event_yield:.2f}% 年化)",
            showarrow=False,
            font=dict(color="blue", size=10),
            yshift=20 # 向上微调
        )
    
    # 敲入区注释
    if knock_in_region_x: # 确保敲入区有数据才添加注释
        if snowball_type == "雪球":
            fig.add_annotation(
                x=knock_in_region_x[0] + (knock_in_region_x[-1] - knock_in_region_x[0]) / 2, # 区域中心
                y=annotation_y_pos_dynamic, # 放置在动态位置
                text="敲入区<br>(亏损扩大)",
                showarrow=False,
                font=dict(color="red", size=10)
            )
        else: # 三元雪球
            guaranteed_annual_yield = guaranteed_return * 100 # 将收益率转为百分比
            fig.add_annotation(
                x=knock_in_region_x[0] + (knock_in_region_x[-1] - knock_in_region_x[0]) / 2, # 区域中心
                y=guaranteed_annual_yield, # 放置在固定收益线上
                text=f"敲入区<br>(保底 {guaranteed_annual_yield:.2f}% 年化)",
                showarrow=False,
                font=dict(color="red", size=10),
                yshift=20
            )


    fig.update_layout(
        title="雪球产品理论年化收益曲线",
        xaxis_title="期末价格 (点位)",
        yaxis_title="理论年化收益百分比 (%)",
        template="plotly_white",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------
# render() 函数保持不变，因为理论绘图函数的调用方式没有变
# -------------------------------
def render():
    st.title("👑雪球结构产品收益模拟👑")

    # -------------------------------
    # 1. 参数输入
    # -------------------------------
    st.header("参数输入")

    PRESET_CODES = ["000016.SH", "000300.SH", "000905.SH", "000852.SH", "513180.SH"]
    snowball_types = ["雪球", "三元雪球"]
    snowball_type      = st.selectbox("雪球产品类型", snowball_types, index=0)
    underlying_code    = st.selectbox("挂钩标的代码", PRESET_CODES, index=3)
    notional_principal = st.number_input("名义本金 (万元)", value=1000, min_value=0)
    start_date         = st.date_input("产品开始日期", value=pd.to_datetime("2025-05-08").date())
    knock_in_pct       = st.number_input("敲入障碍价格 (%)", value=70.0, min_value=0.0, max_value=100.0)/100.0
    
    knock_in_strike_pct = 1.0 # 默认值，如果不是雪球类型则不使用
    participation_rate = 1.0 # 默认值
    guaranteed_return = 0.01 # 默认值
    
    if snowball_type == "雪球":
        knock_in_strike_pct  = st.number_input("敲入执行价格 (%)", value=100.0, min_value=0.0, max_value=200.0) / 100.0
        participation_rate   = st.number_input("敲入参与率 (%)", value=100.0, min_value=0.0, max_value=500.0) / 100.0
    else:
        guaranteed_return = st.number_input("敲入收益率 (%)", value=1.0, min_value=0.0, max_value=100.0) / 100.0

    knock_in_style       = st.selectbox("敲入观察方式", ["每日观察", "到期观察"], index=0)

    max_loss_ratio       = st.number_input("最大亏损比例 (%)", value=100.0, min_value=0.0, max_value=100.0) / 100.0
    
    obs_dates_input    = st.text_area(
        "敲出观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/06/09,2025/07/08,2025/08/08,2025/09/08,2025/10/09\n"
        "2025/11/10,2025/12/08,2026/01/08,2026/02/09,2026/03/09\n"
        "2026/04/08,2026/05/08,2026/06/08,2026/07/08,2026/08/10\n"
        "2026/09/08,2026/10/08,2026/11/09,2026/12/08,2027/01/08\n"
        "2027/02/12,2027/03/08,2027/04/08,2027/05/10"
    )
    obs_barriers_input  = st.text_area(
        "对应敲出障碍价格 (%) 列表 (与观察日一一对应)",
        "\n".join(["100.00%"]*24)
    )
    
    obs_coupons_input    = st.text_area(
        "对应敲出票息 (%) 列表 (与观察日一一对应)",
        "\n".join(["2.34%"]*24)
    )
    
    dividend_mode        = st.selectbox("红利票息来源", ["同敲出票息", "自行输入"], index=0)
    dividend_rate = 0.0 # 默认值
    if dividend_mode == "同敲出票息":
        tmp = [float(p.rstrip("%"))/100.0 for p in obs_coupons_input.replace("\n",",").split(",") if p.strip()]
        dividend_rate = tmp[-1] if tmp else 0.0
    else:
        dividend_rate = st.number_input("红利票息 (%)", value=2.34, min_value=0.0) / 100.0
    
    start_price            = st.number_input("产品期初价格 (点位)", value=100.0, min_value=0.0)
    sim_start_date       = st.date_input("模拟数据开始日期 (用于历史模拟)",
                                          value=pd.to_datetime("2022-03-01").date())

    # 等待按钮触发
    if not st.button("生成分析图表"):
        st.info("请填写完参数后，点击“生成分析图表”")
        return

    # ---- 解析敲出列表 ----
    def parse_date_list(s: str):
        return [pd.to_datetime(x).date() for x in s.replace("\n",",").split(",") if x.strip()]

    def parse_pct_list(s: str):
        return [float(x.rstrip("%"))/100.0 for x in s.replace("\n",",").split(",") if x.strip()]

    obs_dates    = parse_date_list(obs_dates_input)
    obs_barriers = parse_pct_list(obs_barriers_input)
    obs_coupons  = parse_pct_list(obs_coupons_input)

    if not (len(obs_dates)==len(obs_barriers)==len(obs_coupons)):
        st.error("观察日、障碍价、票息 列表长度必须一致")
        return

    # 映射
    knock_in_level   = start_price * knock_in_pct
    obs_barrier_lvls = [start_price * p for p in obs_barriers]
    obs_dict         = dict(zip(obs_dates, obs_barrier_lvls))

    # -------------------------------
    # 2. 图1: 理论年化收益曲线
    # -------------------------------
    st.header("👑图1：雪球产品理论年化收益曲线👑")
    
    # 收集参数传递给绘图函数
    params = {
        "snowball_type": snowball_type,
        "notional_principal": notional_principal,
        "start_price": start_price,
        "knock_in_pct": knock_in_pct,
        "knock_in_strike_pct": knock_in_strike_pct,
        "participation_rate": participation_rate,
        "guaranteed_return": guaranteed_return,
        "max_loss_ratio": max_loss_ratio,
        "obs_dates": obs_dates,
        "obs_barriers": obs_barriers,
        "obs_coupons": obs_coupons,
        "dividend_rate": dividend_rate,
        "start_date": start_date
    }
    plot_theoretical_payoff(params)
    
    st.markdown("""
    **本图展示了在产品到期时，挂钩标的资产的最终价格（横轴）与产品实现的理论年化收益百分比（纵轴）之间的关系。**
    * **横轴 (期末价格)**：表示产品到期时，挂钩标的资产所处的价格点位。
    * **纵轴 (理论年化收益百分比)**：表示产品年化后的盈亏比例。正值代表盈利，负值代表亏损。
    * **本金线 (0% 年化收益)**：黑色的水平线，代表您收回本金，不赚不亏的状态。
    * **敲入障碍 (红色虚线)**：当期末价格**跌破此线**时，可能触发敲入事件。
    * **敲出障碍 (绿色虚线)**：当期末价格**达到或超过此线**时，可能触发敲出事件。

    **不同收益区间解读：**
    1.  **敲出区 (图右侧，绿色曲线)**：当期末价格**高于敲出障碍线**时，产品将按照敲出条款结算，实现一个**固定的年化收益率**。
    2.  **无事件区 (图中间，蓝色曲线)**：当期末价格**介于敲入障碍线和敲出障碍线之间**时，产品未敲出也未敲入，最终按照产品约定的**固定年化红利票息**进行结算。
    3.  **敲入区 (图左侧，红色曲线)**：当期末价格**低于敲入障碍线**时，产品触发敲入。
        * **雪球产品**：曲线通常呈现**向下倾斜的趋势**，表示随着标的资产价格的下跌，亏损会逐渐扩大。
        * **三元雪球产品**：曲线在此区域表现为一条**水平线**，表示即使触发敲入，您仍能获得一个**固定的保底年化收益率**。
    """)


    # -------------------------------
    # 3. 图2: 历史模拟价格路径
    # -------------------------------
    st.header("👑图2：历史模拟价格路径👑")
    final_obs    = obs_dates[-1]
    period_days  = (pd.to_datetime(final_obs) - pd.to_datetime(start_date)).days
    fetch_end    = sim_start_date + datetime.timedelta(days=period_days+90)

    raw  = get_price_data([underlying_code],
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
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["ret"]   = df["price"].pct_change().fillna(0)
    rets        = df["ret"].values

    sim_dates = pd.bdate_range(start_date, final_obs)
    N         = len(sim_dates)
    # 确保retes的长度足够，或截断
    rets      = np.concatenate([rets, np.zeros(max(0,(N-1)-len(rets)))])[:N-1]

    sim_prices    = [start_price]
    knock_ined    = False
    knock_out     = False
    knock_in_date = knock_out_date = None

    for i, r in enumerate(rets):
        if knock_out: break
        new_p = sim_prices[-1] * (1 + r)
        today = sim_dates[i+1]
        sim_prices.append(new_p)

        if knock_in_style == "每日观察" and not knock_ined and new_p < knock_in_level:
            knock_ined, knock_in_date = True, today

        if today.date() in obs_dict and new_p >= obs_dict[today.date()]:
            knock_out, knock_out_date = True, today
            break

    if not knock_out and knock_in_style == "到期观察":
        final_p = sim_prices[-1]
        if final_p < knock_in_level:
            knock_ined, knock_in_date = True, sim_dates[-1]

    if knock_out:
        idx = list(sim_dates).index(knock_out_date)
        sim_dates    = sim_dates[:idx+1]
        sim_prices = sim_prices[:idx+1]

    sim_df = pd.DataFrame({"price": sim_prices}, index=sim_dates)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df.index, y=sim_df["price"],
                              mode="lines", name="模拟价格"))
    fig2.add_trace(go.Scatter(x=[sim_df.index[0], sim_df.index[-1]],
                              y=[knock_in_level]*2,
                              mode="lines", name="敲入线",
                              line=dict(color="red", dash="dash")))
    xs, ys = [], []
    for d, lvl in obs_dict.items():
        dt = pd.to_datetime(d)
        if dt in sim_df.index:
            xs.append(dt); ys.append(lvl)
    if xs:
        fig2.add_trace(go.Scatter(x=xs, y=ys, mode="markers",
                                  name="敲出障碍价",
                                  marker=dict(color="green", size=8)))
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
        idx         = obs_dates.index(knock_out_date.date())
        coupon      = obs_coupons[idx]
        active_days = sim_df.index.get_loc(knock_out_date) + 1
        payoff      = notional_principal  * coupon * active_days / 365
        st.write(
            f"- 敲出日期：{knock_out_date.date()}  \n"
            f"- 存续交易日：{active_days} 天  \n"
            f"- 年化票息：{coupon*100:.2f}%  \n"
            f"- 收益：{payoff:.2f} 万元"
        )
    elif knock_ined:
        if snowball_type == "雪球":
            final_price     = sim_prices[-1]
            final_pct       = final_price / start_price
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
                f"- 亏损金额：-{loss_amt:.2f} 万元"
            )
        else:
            st.write(
                f"- 敲入发生日期：{knock_in_date.date()}  \n"
                f"- 获得敲入收益：{guaranteed_return * notional_principal:.2f}万元 "
            )
    else:
        term_in_years_final = (pd.to_datetime(obs_dates[-1]) - pd.to_datetime(start_date)).days / 365.0
        payoff = notional_principal * dividend_rate * term_in_years_final
        st.write(f"- 产品到期，未触发敲出或敲入事件，获得红利票息收益：{payoff:.2f} 万元")
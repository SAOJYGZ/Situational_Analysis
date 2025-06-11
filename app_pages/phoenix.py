import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from api import get_price_data

def calculate_phoenix_payoff(
    final_price_level, start_price, notional_principal,
    knock_in_pct, knock_in_strike_pct, participation_rate, max_loss_ratio,
    dividend_barrier_pct, obs_dividend_dates, obs_dividend_rates,
    obs_barriers, # 敲出障碍用于判断敲出区
    product_term_in_years # 新增参数：产品总期限（年）
):
    """
    计算凤凰结构产品在期末价格为 final_price_level 时的理论年化收益率。
    注意：这里的计算是基于产品运行到期末（或敲出）的情况，并假设期间派息条件均满足。
    实际派息是分期进行的，此处为理论汇总。
    """
    relative_price = final_price_level / start_price
    
    # 计算在理论曲线中，所有可能获得的派息总额（如果条件满足）
    total_potential_dividend_amount = 0
    for rate in obs_dividend_rates:
        total_potential_dividend_amount += notional_principal * rate

    final_total_cash_payoff = 0 # 最终的总收益金额

    # 1. 敲出区：如果期末价格达到或超过最后一个敲出障碍
    last_obs_barrier_pct = obs_barriers[-1] if obs_barriers else 1.0 # 使用最晚敲出障碍
    if relative_price >= last_obs_barrier_pct:
        # 凤凰产品敲出通常是返还本金，收益为已收到的派息总和
        # 理论曲线上，如果达到敲出障碍，视为已获得所有派息
        final_total_cash_payoff = total_potential_dividend_amount
    
    # 2. 敲入区：如果期末价格低于或等于敲入障碍
    elif relative_price <= knock_in_pct:
        raw_loss_pct = max(0.0, knock_in_strike_pct - relative_price)
        capped_loss_pct = min(raw_loss_pct, max_loss_ratio)
        total_loss_amount = capped_loss_pct * notional_principal * participation_rate
        # 敲入后，派息停止。总收益为负值 (本金损失)
        # 这里假设一旦敲入，即使之前有派息，也忽略其对最终收益的贡献，只看本金损失
        # 这是理论曲线的简化，实际中已派息不会收回
        final_total_cash_payoff = -total_loss_amount
        
    # 3. 无敲出，无敲入区 (中间区域)
    else: # knock_in_pct < relative_price < last_obs_barrier_pct
        if relative_price >= dividend_barrier_pct:
            # 如果最终价格高于派息障碍，假设所有派息都收到了
            final_total_cash_payoff = total_potential_dividend_amount
        else:
            # 如果最终价格低于派息障碍但高于敲入障碍，未敲入也未派息，收益为0 (收回本金)
            final_total_cash_payoff = 0.0

    # 将总收益金额转换为年化收益率
    # 避免除以零的情况
    if notional_principal == 0 or product_term_in_years == 0:
        return 0.0
    
    annualized_return_pct = (final_total_cash_payoff / notional_principal) / product_term_in_years * 100
    return annualized_return_pct


def plot_phoenix_payoff(params):
    """
    绘制凤凰结构产品理论年化收益率曲线。
    params: 包含所有必要参数的字典
    """
    notional_principal = params["notional_principal"]
    start_price = params["start_price"]
    knock_in_pct = params["knock_in_pct"]
    knock_in_strike_pct = params["knock_in_strike_pct"]
    participation_rate = params["participation_rate"]
    max_loss_ratio = params["max_loss_ratio"]
    dividend_barrier_pct = params["dividend_barrier_pct"]
    obs_dividend_dates = params["obs_dividend_dates"]
    obs_dividend_rates = params["obs_dividend_rates"]
    obs_dates = params["obs_dates"]
    obs_barriers = params["obs_barriers"]
    product_term_in_years = params["product_term_in_years"] # 新增参数

    if not obs_dates or not obs_dividend_dates:
        st.warning("缺少敲出观察日或派息观察日列表，无法绘制理论收益曲线。")
        return

    # 获取最晚敲出障碍百分比，用于定义敲出区边界
    last_obs_barrier_pct = obs_barriers[-1] if obs_barriers else 1.0

    # 确定价格范围，确保覆盖所有关键障碍点
    min_price_factor = min(knock_in_pct * 0.8, dividend_barrier_pct * 0.8, 0.5)
    max_price_factor = max(last_obs_barrier_pct * 1.2, 1.5)
    price_range = np.linspace(start_price * min_price_factor, start_price * max_price_factor, 500)

    # 初始化用于不同区域的列表
    knock_in_region_x, knock_in_region_y = [], []
    no_event_paid_region_x, no_event_paid_region_y = [], []
    no_event_unpaid_region_x, no_event_unpaid_region_y = [], []
    knock_out_region_x, knock_out_region_y = [], []

    for p in price_range:
        annualized_payoff_pct = calculate_phoenix_payoff(
            p, start_price, notional_principal,
            knock_in_pct, knock_in_strike_pct, participation_rate, max_loss_ratio,
            dividend_barrier_pct, obs_dividend_dates, obs_dividend_rates,
            obs_barriers, product_term_in_years
        )

        relative_price = p / start_price # 再次计算相对价格用于判断区域
        if relative_price >= last_obs_barrier_pct:
            knock_out_region_x.append(p)
            knock_out_region_y.append(annualized_payoff_pct)
        elif relative_price <= knock_in_pct:
            knock_in_region_x.append(p)
            knock_in_region_y.append(annualized_payoff_pct)
        else: # knock_in_pct < relative_price < last_obs_barrier_pct
            if relative_price >= dividend_barrier_pct:
                no_event_paid_region_x.append(p)
                no_event_paid_region_y.append(annualized_payoff_pct)
            else:
                no_event_unpaid_region_x.append(p)
                no_event_unpaid_region_y.append(annualized_payoff_pct)

    fig = go.Figure()

    # 绘制各区域曲线
    if knock_in_region_x:
        fig.add_trace(go.Scatter(x=knock_in_region_x, y=knock_in_region_y, mode='lines', name='敲入区 (亏损)', line=dict(width=3, color='red')))
    if no_event_unpaid_region_x:
        fig.add_trace(go.Scatter(x=no_event_unpaid_region_x, y=no_event_unpaid_region_y, mode='lines', name='无事件区 (无收益)', line=dict(width=3, color='gray')))
    if no_event_paid_region_x:
        fig.add_trace(go.Scatter(x=no_event_paid_region_x, y=no_event_paid_region_y, mode='lines', name='无事件区 (派息)', line=dict(width=3, color='blue')))
    if knock_out_region_x:
        fig.add_trace(go.Scatter(x=knock_out_region_x, y=knock_out_region_y, mode='lines', name='敲出区 (派息)', line=dict(width=3, color='green')))

    # 添加关键的垂直和水平线
    fig.add_vline(x=start_price, line_dash="dot", line_color="grey",
                  annotation_text=f"期初价格({start_price:.2f})", annotation_position="top right")
    fig.add_vline(x=start_price * knock_in_pct, line_dash="dash", line_color="red",
                  annotation_text=f"敲入障碍({start_price * knock_in_pct:.2f})", annotation_position="bottom right")
    fig.add_vline(x=start_price * dividend_barrier_pct, line_dash="dash", line_color="purple",
                  annotation_text=f"派息障碍({start_price * dividend_barrier_pct:.2f})", annotation_position="top left")
    
    # 敲出障碍由于可能阶梯式下移，这里标注最晚的敲出障碍
    fig.add_vline(x=start_price * last_obs_barrier_pct, line_dash="dash", line_color="green",
                  annotation_text=f"最终敲出障碍({start_price * last_obs_barrier_pct:.2f})", annotation_position="top left")

    # 添加零收益线 (本金线)
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, annotation_text="0% 年化收益率 (盈亏平衡)", annotation_position="top right")

    # 获取所有有效的收益值来调整注释Y轴位置
    all_payoffs = [val for sublist in [knock_in_region_y, no_event_paid_region_y, no_event_unpaid_region_y, knock_out_region_y] for val in sublist if val is not None]
    if all_payoffs:
        min_y, max_y = min(all_payoffs), max(all_payoffs)
    else:
        min_y, max_y = -50, 50 # 默认值以防列表为空

    # 调整注释的Y位置
    annotation_y_pos_low = min_y * 0.8
    annotation_y_pos_high = max_y * 0.8
    annotation_y_pos_mid = min_y + (max_y - min_y) * 0.4


    # 添加区域注释和收益率
    # 敲出区注释
    if knock_out_region_x:
        avg_payoff = np.mean(knock_out_region_y) if knock_out_region_y else 0
        fig.add_annotation(
            x=knock_out_region_x[0] + (knock_out_region_x[-1] - knock_out_region_x[0]) / 2,
            y=avg_payoff, # 取该区域的收益值
            text=f"敲出区<br>({avg_payoff:.2f}%)",
            showarrow=False,
            font=dict(color="green", size=10),
            yshift=20
        )
    
    # 无事件区（已派息）注释
    if no_event_paid_region_x:
        avg_payoff = np.mean(no_event_paid_region_y) if no_event_paid_region_y else 0
        fig.add_annotation(
            x=no_event_paid_region_x[0] + (no_event_paid_region_x[-1] - no_event_paid_region_x[0]) / 2,
            y=avg_payoff, # 取该区域的收益值
            text=f"无事件区<br>(派息: {avg_payoff:.2f}%)",
            showarrow=False,
            font=dict(color="blue", size=10),
            yshift=20
        )
    
    # 无事件区（未派息）注释
    if no_event_unpaid_region_x:
        avg_payoff = np.mean(no_event_unpaid_region_y) if no_event_unpaid_region_y else 0
        fig.add_annotation(
            x=no_event_unpaid_region_x[0] + (no_event_unpaid_region_x[-1] - no_event_unpaid_region_x[0]) / 2,
            y=avg_payoff, # 通常为0
            text=f"无事件区<br>(无收益: {avg_payoff:.2f}%)",
            showarrow=False,
            font=dict(color="gray", size=10),
            yshift=20
        )
    
    # 敲入区注释
    if knock_in_region_x:
        fig.add_annotation(
            x=knock_in_region_x[0] + (knock_in_region_x[-1] - knock_in_region_x[0]) / 2,
            y=annotation_y_pos_low, # 动态调整位置
            text="敲入区<br>(亏损扩大)",
            showarrow=False,
            font=dict(color="red", size=10)
        )

    fig.update_layout(
        title="凤凰结构产品理论年化收益率曲线",
        xaxis_title="期末价格 (点位)",
        yaxis_title="理论年化收益率 (%)",
        template="plotly_white",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)


def render():
    st.title("👑凤凰结构产品收益模拟👑")

    # -------------------------------
    # 1. 参数输入
    # -------------------------------
    st.header("参数输入")

    PRESET_CODES = ["000016.SH","000300.SH","000905.SH","000852.SH","513180.SH"]
    underlying_code     = st.selectbox("挂钩标的代码", PRESET_CODES, index=3)
    notional_principal  = st.number_input("名义本金 (万元)", value=1000, min_value=0)
    start_date          = st.date_input("产品开始日期", value=pd.to_datetime("2025-05-20").date())
    knock_in_pct        = st.number_input("敲入障碍价格 (%)", value=70, min_value=0, max_value=100)/100
    dividend_barrier_pct= st.number_input("派息障碍价格 (%)", value=70, min_value=0, max_value=100)/100
    max_loss_ratio      = st.number_input("最大亏损比例 (%)", value=100.0, min_value=0.0, max_value=100.0)/100.0
    knock_in_strike_pct = st.number_input("敲入执行价格 (%)", value=100.0, min_value=0.0, max_value=200.0) / 100.0
    participation_rate  = st.number_input("敲入参与率 (%)", value=100.0, min_value=0.0, max_value=500.0) / 100.0
    knock_in_style      = st.selectbox("敲入观察方式", ["每日观察","到期观察"], index=0)
    
    
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
    obs_dates_input         = st.text_area(
        "敲出观察日列表 (YYYY/MM/DD，用逗号或换行分隔)",
        "2025/08/20,2025/09/22,2025/10/20,2025/11/20,2025/12/22\n"
        "2026/01/20,2026/02/24,2026/03/20,2026/04/20,2026/05/20\n"
        "2026/06/22,2026/07/20,2026/08/20,2026/09/21,2026/10/20\n"
        "2026/11/20,2026/12/21,2027/01/20,2027/02/22,2027/03/22\n"
        "2027/04/20,2027/05/20"
    )
    # 敲出障碍价格列表
    obs_barriers_input      = st.text_area(
        "敲出障碍价格 (%) 列表 (与观察日一一对应)",
        "\n".join([
            "100.00%","99.50%","99.00%","98.50%","98.00%","97.50%","97.00%","96.50%","96.00%","95.50%",
            "95.00%","94.50%","94.00%","93.50%","93.00%","92.50%","92.00%","91.50%","91.00%","90.50%",
            "90.00%","89.50%"
        ])
    )

    start_price             = st.number_input("产品期初价格 (点位/%)", value=100.0, min_value=0.0)
    sim_start_date          = st.date_input(
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

    # 计算产品总期限（年）
    if obs_dates:
        product_term_in_years = (pd.to_datetime(obs_dates[-1]) - pd.to_datetime(start_date)).days / 365.0
        if product_term_in_years <= 0: # 避免除以零或负数期限
            st.error("产品总期限必须大于0年，请检查产品开始日期和敲出观察日列表。")
            return
    else:
        st.error("请至少输入一个敲出观察日以确定产品期限。")
        return


    # 构造映射
    dividend_dict             = dict(zip(obs_dividend_dates, obs_dividend_rates))
    obs_barrier_levels        = [start_price * p for p in obs_barriers]
    obs_dict                  = dict(zip(obs_dates, obs_barrier_levels))
    knock_in_level            = start_price * knock_in_pct
    dividend_barrier_level    = start_price * dividend_barrier_pct

    # -------------------------------
    # 2. 图1：凤凰产品理论年化收益率曲线
    # -------------------------------
    st.header("图1：凤凰结构产品理论年化收益率曲线")
    
    # 收集参数传递给绘图函数
    params = {
        "notional_principal": notional_principal,
        "start_price": start_price,
        "knock_in_pct": knock_in_pct,
        "knock_in_strike_pct": knock_in_strike_pct,
        "participation_rate": participation_rate,
        "max_loss_ratio": max_loss_ratio,
        "dividend_barrier_pct": dividend_barrier_pct,
        "obs_dividend_dates": obs_dividend_dates,
        "obs_dividend_rates": obs_dividend_rates,
        "obs_dates": obs_dates,
        "obs_barriers": obs_barriers,
        "product_term_in_years": product_term_in_years # 传递产品总期限
    }
    plot_phoenix_payoff(params)

    st.markdown("""
    **本图展示了在产品到期时，挂钩标的资产的最终价格（横轴）与产品实现的理论年化收益率（纵轴）之间的关系。**

    * **横轴 (期末价格)**：表示产品到期时，挂钩标的资产所处的价格点位。
    * **纵轴 (理论年化收益率)**：表示产品最终实现的年化收益率百分比。正值代表盈利，负值代表亏损。
    * **0% 年化收益率 (盈亏平衡)**：黑色的水平线，代表您收回本金，不赚不亏的状态。
    * **敲入障碍 (红色虚线)**：当期末价格**跌破此线**时，触发敲入事件。
    * **派息障碍 (紫色虚线)**：当期末价格需**高于此线**，才能在观察日获得派息（如果未敲入）。
    * **最终敲出障碍 (绿色虚线)**：当期末价格**达到或超过此线**时，表示产品已敲出。

    **不同收益区间解读：**
    1.  **敲出区 (图右侧，绿色曲线)**：当期末价格**高于最晚的敲出障碍线**时，产品已敲出。您的年化收益率是**敲出前所有已成功派发的总金额进行年化**。
    2.  **无事件区 (派息) (图中间，蓝色曲线)**：当期末价格**介于敲入障碍和最晚敲出障碍之间，且高于派息障碍**时，产品既未敲出也未敲入，但期间获得了所有派息。年化收益率是**所有派息金额之和进行年化**。
    3.  **无事件区 (无收益) (图中间，灰色曲线)**：当期末价格**介于敲入障碍和最晚敲出障碍之间，但低于派息障碍**时，产品既未敲出也未敲入，且期间**没有获得派息**。年化收益率为**0%** (收回本金)。
    4.  **敲入区 (图左侧，红色曲线)**：当期末价格**低于敲入障碍线**时，产品触发敲入。年化收益表现为**已派息金额减去因敲入造成的亏损后的总金额进行年化**。曲线呈现**向下倾斜的趋势**，表示随着标的资产价格的下跌，亏损会逐渐扩大。
    """)

    # -------------------------------
    # 3. 图2：历史模拟价格路径
    # -------------------------------
    st.header("👑图2：历史模拟价格路径👑")
    final_obs   = obs_dates[-1] # 使用敲出观察日的最后一个日期作为产品期限
    period_days = (pd.to_datetime(final_obs) - pd.to_datetime(start_date)).days
    fetch_end   = sim_start_date + datetime.timedelta(days=period_days + 90)

    raw  = get_price_data([underlying_code],
                          sim_start_date.strftime("%Y-%m-%d"),
                          fetch_end.strftime("%Y-%m-%d"))
    hist = raw.get(underlying_code, [])
    if not hist:
        st.error("无法获取历史数据"); return

    df = pd.DataFrame(hist)
    df["date"]  = pd.to_datetime(df["date"])
    price_col   = "close" if "close" in df else df.columns[1]
    df["price"] = df[price_col].astype(float)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["ret"]   = df["price"].pct_change().fillna(0)

    sim_dates       = pd.bdate_range(start_date, final_obs)
    rets            = df["ret"].values
    # 确保 rets 的长度与模拟天数匹配
    rets            = np.concatenate([rets, np.zeros(max(0, len(sim_dates)-1-len(rets)))])[:len(sim_dates)-1]

    sim_prices      = [start_price]
    knock_ined      = False
    knock_out       = False
    knock_in_date   = knock_out_date = None
    dividend_events = [] # (日期, 是否派息, 派息率, 派息金额)

    for i, r in enumerate(rets):
        if knock_out: break # 如果已敲出，则停止模拟
        new_price = sim_prices[-1] * (1 + r)
        today     = sim_dates[i+1] # 当前模拟日期
        sim_prices.append(new_price)

        # 敲入检测 (每日观察)
        if knock_in_style=="每日观察" and not knock_ined and new_price<knock_in_level:
            knock_ined, knock_in_date = True, today
            # 如果敲入，后续派息通常停止，但已派发的不会收回
            # 为简化模拟，这里假设敲入后不再派息
            # dividend_events = [d for d in dividend_events if d[0] < today.date()] # 移除敲入后的派息事件

        # 敲出检测
        if today.date() in obs_dict and new_price>=obs_dict[today.date()]:
            knock_out, knock_out_date = True, today
            break # 敲出后产品结束

        # 派息检测 (如果未敲入，且未敲出)
        if not knock_ined and today.date() in dividend_dict:
            rate   = dividend_dict[today.date()]
            # 派息条件：未敲入 且 价格高于派息障碍
            paid   = new_price >= dividend_barrier_level
            amount = notional_principal * rate
            dividend_events.append((today.date(), paid, rate, amount))

    # 到期敲入 (如果到期观察)
    if not knock_out and knock_in_style=="到期观察" and sim_prices[-1]<knock_in_level:
        knock_ined, knock_in_date = True, sim_dates[-1]

    # 最后一次派息（如果到期观察并且未敲出未敲入）
    # 检查最后一个派息日是否已经被处理过，如果没有，且满足条件，则添加
    last_dividend_date = obs_dividend_dates[-1] if obs_dividend_dates else None
    if not knock_out and not knock_ined and last_dividend_date and last_dividend_date == sim_dates[-1].date():
        if last_dividend_date not in [d[0] for d in dividend_events]: # 避免重复添加
            rate   = dividend_dict[last_dividend_date]
            paid   = sim_prices[-1] >= dividend_barrier_level
            amount = notional_principal * rate
            dividend_events.append((last_dividend_date, paid, rate, amount))


    # 提前敲出截断数据
    if knock_out_date:
        idx = sim_dates.get_indexer([knock_out_date])[0]
        sim_dates  = sim_dates[:idx+1]
        sim_prices = sim_prices[:idx+1]
        # 截断派息事件列表，只保留敲出日之前的派息
        dividend_events = [d for d in dividend_events if d[0] <= knock_out_date.date()]

    sim_df = pd.DataFrame({"price": sim_prices}, index=sim_dates)

    # ==== 绘图 ====
    fig2 = go.Figure()
    # 价格路径
    fig2.add_trace(go.Scatter(x=sim_df.index, y=sim_df["price"],
                               mode="lines", name="模拟价格"))
    # 敲入水平线
    fig2.add_trace(go.Scatter(
        x=[sim_df.index[0], sim_df.index[-1]],
        y=[knock_in_level, knock_in_level],
        mode="lines", name="敲入线",
        line=dict(color="red", dash="dash")
    ))
    # 派息障碍水平线
    fig2.add_trace(go.Scatter(
        x=[sim_df.index[0], sim_df.index[-1]],
        y=[dividend_barrier_level, dividend_barrier_level],
        mode="lines", name="派息障碍线",
        line=dict(color="purple", dash="dash")
    ))

    # 敲出障碍点
    xs, ys = [], []
    for d, lvl in obs_dict.items():
        dt = pd.to_datetime(d)
        if dt in sim_df.index: # 确保日期在模拟范围内
            xs.append(dt); ys.append(lvl)
    if xs:
        fig2.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name="敲出障碍价",
                                    marker=dict(color="green", size=8)))
    # 派息事件
    paid_x, paid_y, paid_cd = [], [], []
    unpaid_x, unpaid_y, unpaid_cd = [], [], []
    for d, paid, rate, amount in dividend_events:
        dt = pd.to_datetime(d)
        if dt in sim_df.index: # 确保日期在模拟范围内
            if paid:
                paid_x.append(dt); paid_y.append(sim_df.loc[dt,"price"]); paid_cd.append([rate, amount])
            else:
                unpaid_x.append(dt); unpaid_y.append(sim_df.loc[dt,"price"]); unpaid_cd.append([rate, amount])
    if paid_x:
        fig2.add_trace(go.Scatter(x=paid_x, y=paid_y, mode="markers", name="派息成功",
                                    marker=dict(symbol="star", color="red", size=12),
                                    customdata=paid_cd,
                                    hovertemplate="日期:%{x|%Y-%m-%d}<br>派息金额:%{customdata[1]:.2f} 万元<extra></extra>"))
    if unpaid_x:
        fig2.add_trace(go.Scatter(x=unpaid_x, y=unpaid_y, mode="markers", name="未派息",
                                    marker=dict(symbol="star", color="lightgray", size=12),
                                    customdata=unpaid_cd,
                                    hovertemplate="日期:%{x|%Y-%m-%d}<br>派息金额:%{customdata[1]:.2f} 万元<extra></extra>"))
    # 敲入/敲出竖线
    if knock_in_date:
        fig2.add_shape(type="line",
                       x0=knock_in_date, x1=knock_in_date,
                       y0=min(sim_prices), y1=max(sim_prices), # Y轴范围根据模拟价格动态调整
                       line=dict(color="red", dash="dot"))
        fig2.add_annotation(x=knock_in_date, y=max(sim_prices), text="敲入",
                             showarrow=True, arrowhead=1, font=dict(color="red"))
    if knock_out_date:
        fig2.add_shape(type="line",
                       x0=knock_out_date, x1=knock_out_date,
                       y0=min(sim_prices), y1=max(sim_prices), # Y轴范围根据模拟价格动态调整
                       line=dict(color="green", dash="dot"))
        fig2.add_annotation(x=knock_out_date, y=max(sim_prices), text="敲出",
                             showarrow=True, arrowhead=1, font=dict(color="green"))

    fig2.update_layout(title="历史模拟价格路径",
                       xaxis_title="日期", yaxis_title="价格",
                       template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

    # -------------------------------
    # 4. 事件结果
    # -------------------------------
    st.header("事件结果")
    
    # 汇总已获得的派息
    total_paid_dividend_amount = sum(d[3] for d in dividend_events if d[1])
    
    st.subheader("派息记录")
    if not dividend_events:
        st.write("无派息")
    else:
        total_months = len(dividend_events)
        paid_months  = sum(1 for _, paid, _, _ in dividend_events if paid)
        unpaid_months= total_months - paid_months
        
        for d, paid, rate, amt in dividend_events:
            if paid:
                st.write(f" - {d} **派息成功**，金额：{amt:.2f} 万元")
            else:
                st.write(f" - {d} **未派息** (价格低于派息障碍或已敲入)")

        st.write(
            f"""
            - **总计应观察派息期数**：{total_months} 期 
            - **已获得派息期数**：{paid_months} 期，总金额：**{total_paid_dividend_amount:.2f} 万元**
            - **未派息期数**：{unpaid_months} 期 
            """
        )

    st.subheader("产品最终状态")
    if knock_out_date:
        # 产品实际运行天数，用于年化
        actual_product_days = (knock_out_date - pd.to_datetime(start_date)).days
        if actual_product_days <= 0: actual_product_days = 1 # 避免除以零
        actual_product_years = actual_product_days / 365.0
        
        annualized_return_at_knock_out = (total_paid_dividend_amount / notional_principal) / actual_product_years * 100

        st.write(
            f"- 产品状态：**已敲出**\n"
            f"- 敲出日期：{knock_out_date.date()}\n"
            f"- 已获得派息总额：**{total_paid_dividend_amount:.2f} 万元**\n"
            f"- 产品实际运行期限：{actual_product_days} 天 ({actual_product_years:.2f} 年)\n"
            f"- 最终年化收益率：**{annualized_return_at_knock_out:.2f}%**"
        )
    elif knock_ined:
        # 敲入但未敲出：基于“敲入执行价格”和“敲入参与率”计算亏损
        final_price     = sim_prices[-1]
        final_pct       = final_price / start_price
        
        raw_loss_pct    = max(0.0, knock_in_strike_pct - final_pct)
        capped_loss_pct = min(raw_loss_pct, max_loss_ratio)
        loss_amt        = capped_loss_pct * notional_principal * participation_rate

        # 最终总收益金额 = 已获得派息 - 亏损本金
        final_total_payoff_amount = total_paid_dividend_amount - loss_amt

        # 产品实际运行天数（到期）
        actual_product_days = (sim_dates[-1] - pd.to_datetime(start_date)).days
        if actual_product_days <= 0: actual_product_days = 1 # 避免除以零
        actual_product_years = actual_product_days / 365.0

        annualized_return_at_knock_in = (final_total_payoff_amount / notional_principal) / actual_product_years * 100

        st.write(
            f"""
            - 产品状态：**已敲入**
            - 敲入发生日期：{knock_in_date.date()}
            - 最后观察日价格：{final_price:.2f}
            - 敲入执行价格：{knock_in_strike_pct*100:.2f}%
            - 按(执行价格-期末价格)/期初价 计算亏损：{raw_loss_pct*100:.2f}%
            - 应用最大亏损上限：{capped_loss_pct*100:.2f}%
            - 敲入参与率：{participation_rate*100:.2f}%
            - 因敲入而损失本金金额：**-{loss_amt:.2f} 万元**
            - 已获得派息总额：**{total_paid_dividend_amount:.2f} 万元**
            - 产品实际运行期限：{actual_product_days} 天 ({actual_product_years:.2f} 年)
            - 产品**最终年化收益率**：**{annualized_return_at_knock_in:.2f}%**
            """
        )
    else:
        # 未敲入未敲出，产品到期
        # 产品实际运行天数（到期）
        actual_product_days = (sim_dates[-1] - pd.to_datetime(start_date)).days
        if actual_product_days <= 0: actual_product_days = 1 # 避免除以零
        actual_product_years = actual_product_days / 365.0
        
        annualized_return_at_maturity = (total_paid_dividend_amount / notional_principal) / actual_product_years * 100

        st.write(
            f"- 产品状态：**到期未敲出也未敲入**\n"
            f"- 已获得派息总额：**{total_paid_dividend_amount:.2f} 万元**\n"
            f"- 产品实际运行期限：{actual_product_days} 天 ({actual_product_years:.2f} 年)\n"
            f"- 最终年化收益率：**{annualized_return_at_maturity:.2f}%**"
        )
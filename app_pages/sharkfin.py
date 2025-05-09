import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render():
    st.header("鲨鱼鳍期权情景分析")
    st.subheader("美式鲨鱼鳍期权 (简化收益展示)") 

    # 1) 产品参数
    s0 = 100.0 

    with st.form(key="sharkfin_params_form_single"):
        st.write("鲨鱼鳍期权参数输入:")
        col1, col2, col3 = st.columns(3)

        with col1:
            direction = st.selectbox("选择方向 (Direction)", ["看涨鲨鱼鳍 (Bullish)", "看跌鲨鱼鳍 (Bearish)"], index=0)
            strike_price_pct = st.number_input("执行价格 K (% of initial)", min_value=50.0, max_value=150.0, value=100.0, step=1.0, help="相对于初始价格的百分比，例如100代表平价。")
            barrier_price_pct = st.number_input("障碍价格 B (% of initial)", min_value=50.0, max_value=150.0, value=110.0, step=1.0, help="相对于初始价格的百分比。看涨时通常 B > K；看跌时通常 B < K。")

        with col2:
            rebate_if_barrier_hit_pct = st.number_input("越过障碍固定收益率 R (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.1, help="若到期价格达到或越过障碍B，产品支付的固定收益率。")
            participation_rate_pct = st.number_input("参与率 PR (%)", min_value=0.0, max_value=200.0, value=100.0, step=5.0, help="未越过障碍时，标的价格在[K, B)或(B, K]区间内的收益参与程度。")
            term_str = st.text_input("产品期限 (Term)", value="12M", help="例如: 12M 表示12个月。此参数主要用于情景描述。")

        with col3:
            st.write("障碍观察方式: 美式期权") 
            st.write(f"初始标的价格 $S_0$: {s0:.0f} (基准)")
            margin_ratio_pct = st.number_input("保证金比例 (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0, help="投资者投入的资金占名义本金的比例。")

        submit_button = st.form_submit_button("生成鲨鱼鳍收益分析图")

    if submit_button:
        valid_inputs = True
        if direction == "看涨鲨鱼鳍 (Bullish)" and barrier_price_pct <= strike_price_pct:
            st.error("对于看涨鲨鱼鳍, 障碍价格 (B) 通常应高于执行价格 (K)。请调整参数。")
            valid_inputs = False
        elif direction == "看跌鲨鱼鳍 (Bearish)" and barrier_price_pct >= strike_price_pct:
            st.error("对于看跌鲨鱼鳍, 障碍价格 (B) 通常应低于执行价格 (K)。请调整参数。")
            valid_inputs = False

        if not valid_inputs:
            st.stop()

        params_data = {
            "参数名称": ["方向", "执行价格 K", "障碍价格 B", "越过障碍固定收益率 R", "参与率 PR", "产品期限", "保证金比例", "初始标的价格"],
            "参数值": [
                direction.split(" (")[0],
                f"{strike_price_pct:.2f}% (即价格 {s0 * strike_price_pct/100:.2f})",
                f"{barrier_price_pct:.2f}% (即价格 {s0 * barrier_price_pct/100:.2f})",
                f"{rebate_if_barrier_hit_pct:.2f}%",
                f"{participation_rate_pct:.2f}%",
                term_str,
                f"{margin_ratio_pct:.2f}%",
                f"{s0:.2f}"
            ]
        }
        df_params = pd.DataFrame(params_data)
        st.subheader("输入参数概要")
        st.table(df_params.set_index("参数名称"))

        # --- 收益计算逻辑 (单一收益线) ---
        min_x_val = min(s0 * 0.6, strike_price_pct * 0.8, barrier_price_pct * 0.8)
        max_x_val = max(s0 * 1.4, strike_price_pct * 1.2, barrier_price_pct * 1.2)
        if direction == "看跌鲨鱼鳍 (Bearish)":
             min_x_val = min(s0 * 0.6, barrier_price_pct * 0.8)
        if direction == "看涨鲨鱼鳍 (Bullish)":
            max_x_val = max(s0 * 1.4, barrier_price_pct * 1.2)
        min_x_val = min(min_x_val, strike_price_pct - 20, barrier_price_pct - 20)
        max_x_val = max(max_x_val, strike_price_pct + 20, barrier_price_pct + 20)
        min_x_val = max(0, min_x_val)

        underlying_prices_at_expiry_pct = np.linspace(min_x_val, max_x_val, 301) 
        payoff_line_values = np.zeros_like(underlying_prices_at_expiry_pct)

        K_val = strike_price_pct
        B_val = barrier_price_pct
        PR = participation_rate_pct / 100.0
        fixed_rebate_value = s0 * (1 + rebate_if_barrier_hit_pct / 100.0)

        for i, s_t_pct in enumerate(underlying_prices_at_expiry_pct):
            if direction == "看涨鲨鱼鳍 (Bullish)":
                if s_t_pct < K_val: 
                    payoff_line_values[i] = s0
                elif s_t_pct < B_val: # K <= S_T < B
                    payoff_line_values[i] = s0 + s0 * PR * (s_t_pct - K_val) / 100.0
                else: 
                    payoff_line_values[i] = fixed_rebate_value
            else: # 看跌鲨鱼鳍 (Bearish)
                if s_t_pct > K_val: 
                    payoff_line_values[i] = s0
                elif s_t_pct > B_val: # B < S_T <= K
                    payoff_line_values[i] = s0 + s0 * PR * (K_val - s_t_pct) / 100.0
                else: 
                    payoff_line_values[i] = fixed_rebate_value
            
            if payoff_line_values[i] < 0: payoff_line_values[i] = 0 

        # --- 绘图 ---
        st.subheader("鲨鱼鳍期权到期收益示意图")
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=underlying_prices_at_expiry_pct,
            y=payoff_line_values,
            mode='lines',
            name='鲨鱼鳍到期收益线',
            line=dict(color='deepskyblue', width=2.5) 
        ))

        fig.add_vline(x=strike_price_pct, line_width=1, line_dash="dot", line_color="gray",
                      annotation_text=f"执行价 K: {strike_price_pct:.2f}%", annotation_position="top left")
        fig.add_vline(x=barrier_price_pct, line_width=1, line_dash="dot", line_color="orange",
                      annotation_text=f"障碍价 B: {barrier_price_pct:.2f}%", annotation_position="top right" if direction == "看涨鲨鱼鳍 (Bullish)" else "bottom right")

        fig.add_hline(y=s0, line_width=1, line_dash="solid", line_color="black",
                      annotation_text=f"名义本金: {s0:.2f}", annotation_position="bottom right")
        if fixed_rebate_value != s0 :
             fig.add_hline(y=fixed_rebate_value, line_width=1, line_dash="dashdot", line_color="red",
                      annotation_text=f"固定回报: {fixed_rebate_value:.2f}", annotation_position="bottom left" if fixed_rebate_value < s0 else "top left" )


        min_y_val = min(payoff_line_values.min(), s0, fixed_rebate_value) * 0.90
        max_y_val = max(payoff_line_values.max(), s0, fixed_rebate_value) * 1.10
        if max_y_val <= s0 * 1.05 and max_y_val <= fixed_rebate_value * 1.05 :
            max_y_val = max(s0, fixed_rebate_value) * 1.15
        if min_y_val == 0 and payoff_line_values.min() > -1 : 
            min_y_val = -max_y_val * 0.05


        fig.update_layout(
            title_text=f"{direction.split(' (')[0]} 到期收益结构",
            xaxis_title="到期时标的价格 (占初始价格 $S_0$ 的 %)",
            yaxis_title=f"到期总价值 (基于 $S_0$={s0:.0f})",
            legend_title_text="收益情景",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            yaxis_range=[min_y_val, max_y_val],
            xaxis_range=[underlying_prices_at_expiry_pct.min(), underlying_prices_at_expiry_pct.max()]
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        **图表解读:**
        蓝色实线展示了鲨鱼鳍期权在不同到期标的价格下的最终总价值。此图简化了美式期权路径依赖的复杂性，旨在直观展示其核心收益结构：

        * **对于 {direction.split(' (')[0]}**:
            * 当到期标的价格 ({'S<sub>T</sub> < K' if direction == "看涨鲨鱼鳍 (Bullish)" else 'S<sub>T</sub> > K'})，即期权处于价外区域（且未达到障碍价格B的另一侧）时，通常获得本金 {s0:.2f}。
            * 当到期标的价格处于执行价格K和障碍价格B之间 ({'K $\leq$ S<sub>T</sub> < B' if direction == "看涨鲨鱼鳍 (Bullish)" else 'B < S<sub>T</sub> $\leq$ K'})，投资者将按 {participation_rate_pct:.0f}% 的参与率分享标的价格的有利变动。
                * 看涨时，收益随价格上涨而增加。
                * 看跌时，收益随价格下跌而增加（相对于K）。
            * 当到期标的价格达到或越过障碍价格B ({'S<sub>T</sub> $\geq$ B' if direction == "看涨鲨鱼鳍 (Bullish)" else 'S<sub>T</sub> $\leq$ B'})，产品的“鳍型”收益部分被“削掉”，投资者获得一个固定的总价值，即 ${fixed_rebate_value:.2f}$ (对应于 {rebate_if_barrier_hit_pct:.2f}% 的名义收益率)。这代表了障碍价格对潜在高收益的限制作用。

        * **灰色/橙色虚线:** 分别标记执行价格 K 和障碍价格 B。
        * **黑色实线:** 标记名义本金水平。
        * **红色点划线 (如果可见):** 标记达到或越过障碍时的固定回报水平。

        虽然产品本身是美式期权（障碍在存续期内持续观察），此图的单一收益线更多地是展示一种“若到期时价格为X，则收益为Y”的对应关系，其中障碍价格B在X轴上扮演了一个关键的阈值角色，一旦到期价格越过此阈值，收益形态发生转变。实际美式期权若在期中已触碰障碍，可能已提前按固定回报处理。
        """)
        st.caption(f"注意: 此图表为示意性，基于名义本金 {s0:.0f} 进行计算，未考虑交易费用、税费等实际成本。“越过障碍固定收益率 R” ({rebate_if_barrier_hit_pct:.2f}%) 是产品在到期价格达到或越过障碍时提供的收益率。请以具体产品说明为准。")

    else:
        st.info("请在上方输入参数，然后点击“生成鲨鱼鳍收益分析图”。")

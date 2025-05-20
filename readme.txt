| 变量名                   | 含义                                                                        
| --------------------- | ------------------------------------------------------------------------- 
| `underlying_code`     | 挂钩标的代码（例如 `"000852.SH"`）                                                  
| `notional_principal`  | 名义本金（单位：万元）                                                               
| `knock_in_pct`        | 敲入障碍价格（百分比）                                                               
| `start_price`         | 产品期初价格（点位）                                                                
| `start_date`          | 产品开始日期                                                                    
| `obs_dates_input`     | 用户输入的敲出观察日字符串                                                             
| `obs_barriers_input`  | 用户输入的敲出障碍价格字符串                                                            
| `obs_coupons_input`   | 用户输入的敲出票息字符串                                                              
| `dividend_mode`       | 红利票息来源模式（“同敲出票息”/“自行输入”）                                                  
| `dividend_rate`       | 红利票息率（小数）                                                                 
| `margin_ratio`        | 保证金比例（小数）                                                                 
| `max_loss_ratio`      | 最大亏损比例（小数）                                                                
| `knock_in_strike_pct` | 敲入执行价格（小数形式；如 1.0 表示 100%）                                                
| `participation_rate`  | 敲入参与率（小数形式；如 1.0 表示 100%）                                                 
| `knock_in_style`      | 敲入观察方式（“每日观察”/“到期观察”）                                                     
| `sim_start_date`      | 历史模拟数据开始日期                                                                
| `obs_dates`           | 解析后的敲出观察日列表（`date` 类型）                                                    
| `obs_barriers`        | 解析后的敲出障碍价格列表（小数）                                                          
| `obs_coupons`         | 解析后的敲出票息列表（小数）                                                            
| `knock_in_level`      | 敲入障碍价对应的点位 = `start_price * knock_in_pct`                                 
| `obs_barrier_lvls`    | 每个观察日对应的敲出障碍点位列表 = `start_price * obs_barriers[i]`                        
| `obs_dict`            | 敲出观察日到障碍点位的映射字典                                                           
| `df`                  | 调用 `get_price_data` 返回的原始历史价格 DataFrame                                   
| `price_col`           | 从 `df` 中选用的价格列名称（`"close"` 或其他）                                           
| `rets`                | 历史日收益率数组 = `df["price"].pct_change()`                                     
| `sim_dates`           | 模拟期间的交易日索引（`DatetimeIndex`）                                               
| `sim_prices`          | 滚动生成的模拟价格序列                                                               
| `knock_ined`          | 是否触发过敲入事件的布尔标志                                                            
| `knock_out`           | 是否触发过敲出事件的布尔标志                                                            
| `knock_in_date`       | 触发敲入的日期                                                                   
| `knock_out_date`      | 触发敲出的日期                                                                   
| `sim_df`              | 用于绘制图2的模拟价格路径 DataFrame                                                   
| `active_days`         | 产品敲出时的存续交易日天数                                                             
| `coupon`              | 敲出票息率（小数）                                                                 
| `payoff`              | 敲出时的收益（万元）                                                                
| `final_price`         | 最后观察日的模拟价格                                                                
| `final_pct`           | 最后观察日价格相对期初价的比例                                                           
| `raw_loss_pct`        | 原始亏损率 = `(strike_pct - final_pct)`（不低于 0）                                 
| `capped_loss_pct`     | 应用最大亏损上限后的亏损率                                                             
| `loss_amt`            | 敲入未敲出时的亏损金额 = `capped_loss_pct * notional_principal * participation_rate` 

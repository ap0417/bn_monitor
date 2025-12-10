import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# 获取当前日期和100天前日期
today = datetime.now().strftime("%Y-%m-%d")
start_date_str = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
print(f"开始日期: {start_date_str}")
print(f"结束日期: {today}")
target_date_str = "2025-11-30"  # 设定的目标日期
print(f"目标日期: {target_date_str}")
exclude_symbols=[
                'usdt', 'usdc', 'fdusd', 'dai', 'busd','tusd',
                'usde', 'usd1','susds','pyusd','usds','usde','syrupusdt',
                'usdt0','usdtf','syrupusdc','usdtb','bfusd','rlusd','usdg','usyc','bsc-usd',
                'reth', 'steth', 'wsteth', 'wbeth','weth','weeth','rseth',
                'wbtc', 'cbbtc','fbtc',
                'jitosol','bnsol',
                'wbnb',
                    ]
exclude_names = ['Wrapped SOL']

def fetch_binance_drawdown_analysis():
    # 1. 读取第一步生成的 CSV (包含市值信息)
    input_file = 'data/top_250_coingecko.csv'
    try:
        df = pd.read_csv(input_file)
        print(f"成功读取 {input_file}，共 {len(df)} 条数据。")
    except FileNotFoundError:
        print(f"未找到 {input_file}，请先运行第一步获取列表的代码。")
        return

    # 2. 设定时间范围
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    
    start_ts = int(start_date.timestamp() * 1000) 
    end_ts = int(time.time() * 1000) 

    base_url = "https://api.binance.com/api/v3/klines"
    
    results = []

    print(f"开始分析回撤数据 (从最高点寻找后续最低点)...")
    print("-" * 70)

    valid_cnt = 0
    # 3. 遍历代币
    for index, row in df.iterrows():
        symbol_cg = row['symbol']
        name = row['name']
        market_cap = row['market_cap']
        
        if symbol_cg.lower() in exclude_symbols or name in exclude_names:
            continue

        symbol_binance = f"{symbol_cg.upper()}USDT"
        
        params = {
            'symbol': symbol_binance,
            'interval': '1d',
            'startTime': start_ts,
            'endTime': end_ts,
            'limit': 1000 
        }

        try:
            response = requests.get(base_url, params=params, timeout=5)
            if response.status_code != 200:
                continue 
            klines = response.json()
            if not klines:
                continue

            valid_cnt += 1
            # 限制只分析100个币种
            if valid_cnt == 101:
                break
            
            # 1. 基础数据
            close_price_start = float(klines[0][4]) # 使用开始日期的收盘价作为参考
            close_price_now = float(klines[-1][4])
            
            # 2. 寻找【最高点】及其位置 (Index)
            # max_high_candle: 整个周期内 High 最高的 K 线
            # enumerate 用于获取 index，以便后续切片
            max_high_idx = -1
            max_high_val = -1.0
            
            for i, k in enumerate(klines):
                h = float(k[2])
                if h > max_high_val:
                    max_high_val = h
                    max_high_idx = i
            
            # 获取最高点的日期
            max_high_ts = klines[max_high_idx][0]
            max_high_date = datetime.fromtimestamp(max_high_ts / 1000).strftime('%Y-%m-%d')

            # 3. 寻找【最高点之后的最低点】
            # 我们截取从 max_high_idx 开始到最后的数据
            # 包含 max_high_idx 是为了捕捉当天冲高后的回落
            subsequent_data = klines[max_high_idx:]
            
            min_low_after_peak = float('inf')
            min_low_ts = 0
            
            for k in subsequent_data:
                l = float(k[3])
                if l < min_low_after_peak:
                    min_low_after_peak = l
                    min_low_ts = k[0]
            
            min_low_date = datetime.fromtimestamp(min_low_ts / 1000).strftime('%Y-%m-%d')
            
            # 4. 计算指标
            # 累计涨跌幅
            pct_change_total = (close_price_now - close_price_start) / close_price_start
            
            # 计算到目标日期的涨跌幅
            target_price = None
            pct_change_target = None
            
            for k in klines:
                k_ts = k[0]
                k_date = datetime.fromtimestamp(k_ts / 1000).strftime('%Y-%m-%d')
                if k_date == target_date_str:
                    target_price = float(k[4])  # 收盘价
                    break
            
            if target_price is not None:
                pct_change_target = (target_price - close_price_start) / close_price_start
                price_change_target = (target_price - close_price_start) / close_price_start
            else:
                price_change_target = None
            
            # 新增逻辑：计算区间[开始日期, 目标日期]内的最高点，以及该最高点到目标日期收盘价的跌幅
            drawdown_from_high_to_target = None
            target_idx = -1
            
            # 重新定位 target_idx (虽然上面循环做过，但为了逻辑清晰再找一次，或者优化上面的循环)
            # 优化：上面的循环已经可以拿到 target_idx，我们修改上面的循环
            for i, k in enumerate(klines):
                k_ts = k[0]
                k_date = datetime.fromtimestamp(k_ts / 1000).strftime('%Y-%m-%d')
                if k_date == target_date_str:
                    target_idx = i
                    break
            
            if target_idx != -1 and target_price is not None:
                # 截取从开始到目标日期的K线
                klines_to_target = klines[:target_idx+1]
                max_high_to_target = -1.0
                max_high_to_target_date = ""
                for k in klines_to_target:
                    h = float(k[2])
                    if h > max_high_to_target:
                        max_high_to_target = h
                        max_high_to_target_ts = k[0]
                        max_high_to_target_date = datetime.fromtimestamp(max_high_to_target_ts / 1000).strftime('%Y-%m-%d')
                
                if max_high_to_target > 0:
                    drawdown_from_high_to_target = (target_price - max_high_to_target) / max_high_to_target
            
            # 回撤幅度 (Drawdown)
            # 公式：(后续最低 - 最高) / 最高
            drawdown_pct = (min_low_after_peak - max_high_val) / max_high_val

            # --- 存入结果 ---
            results.append({
                '名称': name,
                '符号': symbol_cg,
                '市值(USD)': market_cap,
                '{}价格'.format(start_date_str): close_price_start,
                '当前价格': close_price_now,
                '{}至今涨跌(%)'.format(start_date_str): round(pct_change_total * 100, 2),
                '{}价格'.format(target_date_str): target_price,
                '{}至{}涨跌(%)'.format(start_date_str, target_date_str): round(pct_change_target * 100, 2) if pct_change_target is not None else None,
                '{}至{}最高价'.format(start_date_str, target_date_str): max_high_to_target if max_high_to_target > 0 else None,
                '{}至{}最高价日期'.format(start_date_str, target_date_str): max_high_to_target_date,
                '{}至{}最高价到结束日期收盘价跌幅(%)'.format(start_date_str, target_date_str): round(drawdown_from_high_to_target * 100, 2) if drawdown_from_high_to_target is not None else None,                
                '全区间最高价': max_high_val,
                '全区间最高价日期': max_high_date,    
                '全区间最高点后最低价': min_low_after_peak,
                '全区间最高点后最低价日期': min_low_date,
                '全区间最高到最低回调幅度(%)': round(drawdown_pct * 100, 2)
            })
            
            print(f"[{symbol_binance}] 最高: {max_high_date} | 后续最低: {min_low_date} | 最大回撤: {round(drawdown_pct * 100, 2)}%")

        except Exception as e:
            print(f"[{symbol_binance}] 出错: {e}")
        
        time.sleep(0.15)

    # 4. 排序与保存
    if results:
        result_df = pd.DataFrame(results)
        
        # 依然按市值降序排列
        result_df = result_df.sort_values(by='市值(USD)', ascending=False)
        
        # 调整列顺序
        cols = [
            '名称', '符号', '市值(USD)', '当前价格', 
            '{}价格'.format(start_date_str),  
            '{}至今涨跌(%)'.format(start_date_str), 
            '{}价格'.format(target_date_str),
            '{}至{}涨跌(%)'.format(start_date_str, target_date_str),
            '{}至{}最高价'.format(start_date_str, target_date_str),
            '{}至{}最高价日期'.format(start_date_str, target_date_str),
            '{}至{}最高价到结束日期收盘价跌幅(%)'.format(start_date_str, target_date_str),
            '全区间最高价', 
            '全区间最高价日期', 
            '全区间最高点后最低价', 
            '全区间最高点后最低价日期', 
            '全区间最高到最低回调幅度(%)'
        ]
        result_df = result_df[cols]
        
        output_file = 'output/binance_drawdown_analysis_since_{}.csv'.format(start_date_str)
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("-" * 70)
        print(f"分析完成！结果已保存至: {output_file}")
        
        # --- 打印统计信息 ---
        target_pct_col = '{}日至{}涨跌(%)'.format(start_date_str, target_date_str)
        if target_pct_col in result_df.columns:
            print("\n" + "="*40)
            print(f"【{start_date_str} 至 {target_date_str} 统计数据】")
            
            # 过滤掉空值进行统计
            valid_changes = result_df[target_pct_col].dropna()
            
            if not valid_changes.empty:
                avg_change = valid_changes.mean()
                median_change = valid_changes.median()
                up_count = len(valid_changes[valid_changes > 0])
                down_count = len(valid_changes[valid_changes < 0])
                
                print(f"参与统计币种数: {len(valid_changes)}")
                print(f"平均涨跌幅: {avg_change:.2f}%")
                print(f"中位数涨跌幅: {median_change:.2f}%")
                print(f"上涨数量: {up_count}")
                print(f"下跌数量: {down_count}")
                
                # 最佳和最差表现
                best_perf = result_df.loc[valid_changes.idxmax()]
                worst_perf = result_df.loc[valid_changes.idxmin()]
                print(f"最佳表现: {best_perf['符号']} ({best_perf[target_pct_col]}%)")
                print(f"最差表现: {worst_perf['符号']} ({worst_perf[target_pct_col]}%)")
            else:
                print("无有效数据进行统计。")
            print("="*40 + "\n")

        print("注意：'最高到最低回调幅度' 反映了从期间高点买入后的最大亏损风险。")
    else:
        print("未获取到数据。")

if __name__ == "__main__":
    fetch_binance_drawdown_analysis()
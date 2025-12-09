import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# 获取当前日期和100天前日期
today = datetime.now().strftime("%Y-%m-%d")
start_date_set = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
print(f"开始日期: {start_date_set}")
print(f"结束日期: {today}")
exclude_symbols=[
                'usdt', 'usdc', 'fdusd', 'dai', 'busd', 
                'usde', 'usd1','susds','pyusd','usds','usde','syrupusdt'
                'usdt0','usdtf','syrupusdc','usdtb','bfusd','rlusd','usdg','usyc','bsc-usd',
                'reth', 'steth', 'wsteth', 'wbeth','weth','weeth','rseth'
                'wbtc', 'cbbtc','fbtc',
                'jitosol','bnsol'
                'wbnb',
                
                    ]

def fetch_binance_drawdown_analysis():
    # 1. 读取第一步生成的 CSV (包含市值信息)
    input_file = 'top_100_crypto.csv'
    try:
        df = pd.read_csv(input_file)
        print(f"成功读取 {input_file}，共 {len(df)} 条数据。")
    except FileNotFoundError:
        print(f"未找到 {input_file}，请先运行第一步获取列表的代码。")
        return

    # 2. 设定时间范围
    start_date_str = start_date_set
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    
    start_ts = int(start_date.timestamp() * 1000) 
    end_ts = int(time.time() * 1000) 

    base_url = "https://api.binance.com/api/v3/klines"
    
    results = []

    print(f"开始分析回撤数据 (从最高点寻找后续最低点)...")
    print("-" * 70)

    # 3. 遍历代币
    for index, row in df.iterrows():
        symbol_cg = row['符号']
        name = row['名称']
        market_cap = row['市值(USD)']
        
        if symbol_cg.lower() in exclude_symbols:
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

            # --- 核心逻辑修正 ---
            
            # 1. 基础数据
            open_price_start = float(klines[0][1])
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
            pct_change_total = (close_price_now - open_price_start) / open_price_start
            
            # 回撤幅度 (Drawdown)
            # 公式：(后续最低 - 最高) / 最高
            drawdown_pct = (min_low_after_peak - max_high_val) / max_high_val

            # --- 存入结果 ---
            results.append({
                '名称': name,
                '符号': symbol_cg,
                '市值(USD)': market_cap,
                '{}日价格'.format(start_date_set): open_price_start,
                '当前价格': close_price_now,
                '{}日至今涨跌(%)'.format(start_date_set): round(pct_change_total * 100, 2),
                
                '期间最高价': max_high_val,
                '最高点日期': max_high_date,
                
                '最高点后最低价': min_low_after_peak,
                '后最低点日期': min_low_date,
                
                '最高点回调幅度(%)': round(drawdown_pct * 100, 2)
            })
            
            print(f"[{symbol_binance}] 最高: {max_high_date} | 后续最低: {min_low_date} | 回撤: {round(drawdown_pct * 100, 2)}%")

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
            '名称', '符号', '市值(USD)', '当前价格', '{}日价格'.format(start_date_set), 
            '{}日至今涨跌(%)'.format(start_date_set), 
            '期间最高价', '最高点日期', 
            '最高点后最低价', '后最低点日期', 
            '最高点回调幅度(%)'
        ]
        result_df = result_df[cols]
        
        output_file = 'binance_drawdown_analysis_since_{}.csv'.format(start_date_set)
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("-" * 70)
        print(f"分析完成！结果已保存至: {output_file}")
        print("注意：'最高点回调幅度' 反映了从期间高点买入后的最大亏损风险。")
    else:
        print("未获取到数据。")

if __name__ == "__main__":
    fetch_binance_drawdown_analysis()
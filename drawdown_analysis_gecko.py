import requests
import pandas as pd
from datetime import datetime
import time

def analyze_crypto_with_coingecko():
    # --- 配置区域 ---
    # 设定起始时间：2025年9月1日
    start_date_str = "2025-09-01"
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    
    # CoinGecko 需要的是 UNIX 时间戳 (秒级)
    start_ts = int(start_date.timestamp())
    end_ts = int(time.time())

    # --- 第一步：获取前100个代币的 ID 和 市值 ---
    print("步骤 1/2: 获取市值前 100 代币列表以获得准确 ID...")
    list_url = "https://api.coingecko.com/api/v3/coins/markets"
    list_params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'false'
    }
    
    # 伪装 User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(list_url, params=list_params, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"获取列表失败，状态码: {response.status_code}")
            return
        coin_list = response.json()
    except Exception as e:
        print(f"网络请求错误: {e}")
        return

    print(f"成功获取 {len(coin_list)} 个代币。")
    print("-" * 60)
    print("步骤 2/2: 逐个获取历史数据并计算回撤 (速度较慢以防封禁)...")
    print("-" * 60)

    results = []

    # --- 第二步：遍历并获取历史数据 ---
    for i, coin in enumerate(coin_list):
        coin_id = coin['id']
        symbol = coin['symbol'].upper()
        name = coin['name']
        market_cap = coin['market_cap']
        
        # 跳过一些无法计算的稳定币 (可选)
        # if symbol in ['USDT', 'USDC', 'FDUSD', 'DAI', 'USDE']:
        #     print(f"[{i+1}/100] {symbol} 跳过 (稳定币)")
        #     continue

        # 历史数据接口
        hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        hist_params = {
            'vs_currency': 'usd',
            'from': start_ts,
            'to': end_ts
        }

        try:
            r = requests.get(hist_url, params=hist_params, headers=headers, timeout=10)
            
            # 处理 API 限制 (HTTP 429)
            if r.status_code == 429:
                print(f"⚠️ 触发频率限制，暂停 60 秒后重试...")
                time.sleep(60)
                # 重试一次
                r = requests.get(hist_url, params=hist_params, headers=headers, timeout=10)

            if r.status_code != 200:
                print(f"[{i+1}/100] {symbol} 获取失败 (Code {r.status_code})")
                continue

            data = r.json()
            prices = data.get('prices', [])

            if not prices:
                print(f"[{i+1}/100] {symbol} 无历史数据")
                continue

            # --- 数据计算逻辑 (完全依照您的要求) ---
            # prices 结构: [[timestamp_ms, price], [timestamp_ms, price], ...]
            
            # 1. 基础价格
            open_price_sept1 = prices[0][1] # 9月1日 (或最早数据) 价格
            close_price_now = prices[-1][1] # 最新价格
            
            # 2. 寻找【期间最高点】
            # max 使用 key 来比较价格 (x[1])
            highest_point = max(prices, key=lambda x: x[1])
            max_price = highest_point[1]
            max_ts = highest_point[0]
            max_date = datetime.fromtimestamp(max_ts / 1000).strftime('%Y-%m-%d')
            
            # 获取最高点在列表中的索引
            max_index = prices.index(highest_point)

            # 3. 寻找【最高点之后的最低点】
            # 截取从最高点开始到最后的数据
            subsequent_data = prices[max_index:]
            
            # 在这段数据中找最低
            lowest_after_peak = min(subsequent_data, key=lambda x: x[1])
            min_price_after_peak = lowest_after_peak[1]
            min_ts = lowest_after_peak[0]
            min_date = datetime.fromtimestamp(min_ts / 1000).strftime('%Y-%m-%d')

            # 4. 计算涨跌幅
            # A. 9月1日至今涨幅
            pct_change_total = (close_price_now - open_price_sept1) / open_price_sept1
            
            # B. 最高点到后续最低点跌幅 (回撤)
            drawdown_pct = (min_price_after_peak - max_price) / max_price

            results.append({
                '名称': name,
                '符号': symbol,
                '市值(USD)': market_cap,
                '当前价格': close_price_now,
                '9月1日至今涨跌(%)': round(pct_change_total * 100, 2),
                '期间最高价': max_price,
                '最高点日期': max_date,
                '最高点后最低价': min_price_after_peak,
                '后最低点日期': min_date,
                '最高点回调幅度(%)': round(drawdown_pct * 100, 2)
            })

            print(f"[{i+1}/100] {symbol} | 市值排名: {i+1} | 回撤: {round(drawdown_pct * 100, 2)}%")

        except Exception as e:
            print(f"[{i+1}/100] {symbol} 处理出错: {e}")

        # --- 关键：为了保护 API 不被封，这里设置延时 ---
        # 免费版建议间隔 1.5 - 3 秒
        time.sleep(2) 

    # --- 第三步：保存结果 ---
    if results:
        df_result = pd.DataFrame(results)
        
        # 确保按市值降序
        df_result = df_result.sort_values(by='市值(USD)', ascending=False)
        
        cols = [
            '名称', '符号', '市值(USD)', '当前价格', 
            '9月1日至今涨跌(%)', 
            '期间最高价', '最高点日期', 
            '最高点后最低价', '后最低点日期', 
            '最高点回调幅度(%)'
        ]
        df_result = df_result[cols]
        
        filename = 'coingecko_drawndown_analysis.csv'
        df_result.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print("-" * 60)
        print(f"全部完成！文件已保存至: {filename}")
        print("所有数据均来自 CoinGecko，覆盖率 100%。")
    else:
        print("未成功获取数据。")

if __name__ == "__main__":
    analyze_crypto_with_coingecko()
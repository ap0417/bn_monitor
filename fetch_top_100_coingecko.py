import requests
import pandas as pd
import time

def fetch_top_100_coins():
    # CoinGecko API 端点
    url = "https://api.coingecko.com/api/v3/coins/markets"
    
    # 请求参数
    params = {
        'vs_currency': 'usd',          # 计价货币：美元
        'order': 'market_cap_desc',    # 排序：按市值降序
        'per_page': 100,               # 每页数量：100
        'page': 1,                     # 页码：第1页
        'sparkline': 'false'           # 是否包含价格走势图数据：否
    }
    
    # 添加 User-Agent 伪装成浏览器，防止被 API 拦截 (403 Forbidden)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("正在从 CoinGecko 获取数据...")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # 检查响应状态码
        if response.status_code == 200:
            data = response.json()
            
            # 将 JSON 数据转换为 Pandas DataFrame
            df = pd.DataFrame(data)
            
            # 筛选想要保留的列 (可以根据需要修改)
            columns_to_keep = [
                'market_cap_rank', 
                'name', 
                'symbol', 
                'current_price', 
                'market_cap', 
                'total_volume', 
                'price_change_percentage_24h'
            ]
            
            # 确保列存在，防止 API 变动导致报错
            existing_columns = [col for col in columns_to_keep if col in df.columns]
            df = df[existing_columns]
            
            # 重命名列名，使其更易读
            df.columns = [
                '排名', '名称', '符号', '当前价格(USD)', 
                '市值(USD)', '24h交易量', '24h涨跌幅(%)'
            ]
            
            # 保存为 CSV 文件
            filename = 'top_100_crypto.csv'
            df.to_csv(filename, index=False, encoding='utf-8-sig') # utf-8-sig 防止中文乱码
            
            print(f"成功！数据已保存至 {filename}")
            print(f"共获取 {len(df)} 条数据。")
            
        elif response.status_code == 429:
            print("错误：请求过于频繁 (Rate Limit Exceeded)。请稍后再试。")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求发生错误: {e}")

if __name__ == "__main__":
    fetch_top_100_coins()
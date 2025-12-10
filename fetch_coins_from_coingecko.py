import requests
import pandas as pd
import time

mktcap_cutoff = 250


def fetch_coins_info():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    
    # CoinGecko allows up to 250 per page
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': mktcap_cutoff,
        'page': 1,
        'sparkline': 'false'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("Fetching top {} coins from CoinGecko...".format(mktcap_cutoff))
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 429:
            print("Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        
        if not data:
            print("No data received.")
            return

        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Select relevant columns (optional, but good for clean output)
        # Keeping most useful columns
        columns_to_keep = [
            'id', 'symbol', 'name', 'current_price', 'market_cap', 
            'market_cap_rank', 'fully_diluted_valuation', 'total_volume',
            'high_24h', 'low_24h', 'price_change_percentage_24h', 
            'circulating_supply', 'total_supply', 'max_supply', 'ath', 'ath_date'
        ]
        
        # Filter columns that exist in the dataframe
        existing_columns = [col for col in columns_to_keep if col in df.columns]
        df = df[existing_columns]

        # Save to CSV
        filename = 'data/top_{}_coingecko.csv'.format(mktcap_cutoff)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"Successfully saved {len(df)} coins to {filename}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fetch_coins_info()

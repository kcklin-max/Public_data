import os
import io
import time
import requests
import pandas as pd

# ==========================================
# 1. 取得台北市類流感就診人次 (疾管署 CDC)
# ==========================================
cdc_url = "https://od.cdc.gov.tw/eic/NHI_Influenza_like_illness.csv"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/csv,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

# 準備多條連線通道 (直接連線 + 各大公用代理伺服器)
connection_channels = [
    cdc_url,  # 1. 先嘗試直接連線
    f"https://api.codetabs.com/v1/proxy?quest={cdc_url}",  # 2. Codetabs 代理
    f"https://corsproxy.io/?{cdc_url}",                    # 3. CORSProxy 代理
    f"https://api.allorigins.win/raw?url={cdc_url}"        # 4. AllOrigins 代理
]

csv_text = None

print("開始獲取 CDC 類流感資料...")
for channel in connection_channels:
    print(f"嘗試連線通道: {channel[:50]}...")
    try:
        # 設定 30 秒 Timeout 避免卡死
        response = requests.get(channel, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 檢查抓到的內容是否真的是我們的 CSV (必須包含特定欄位名稱)
        if "類流感健保就診人次" in response.text and "縣市" in response.text:
            csv_text = response.text
            print("✅ 成功獲取 CDC 資料！")
            break
        else:
            print("⚠️ 抓取到無效內容，嘗試下一條通道...")
            
    except Exception as e:
        print(f"❌ 通道失敗: {e}")
        time.sleep(2) # 暫停 2 秒再試下一個通道

# 如果所有通道都失敗，則終止程式
if not csv_text:
    raise RuntimeError("所有代理伺服器與連線通道皆失敗，CDC 伺服器目前可能全面阻擋海外連線。")

# 讀取 CSV 內容至 Pandas DataFrame
df_cdc = pd.read_csv(io.StringIO(csv_text))

# 篩選台北市最新一週的資料並加總
df_taipei = df_cdc[df_cdc['縣市'] == '台北市']
latest_year = df_taipei['年'].max()
latest_week = df_taipei[df_taipei['年'] == latest_year]['週'].max()

latest_data = df_taipei[(df_taipei['年'] == latest_year) & (df_taipei['週'] == latest_week)]
total_flu = latest_data['類流感健保就診人次'].sum()

# 輸出成 CSV
df_out_cdc = pd.DataFrame({'急診就診人次': [total_flu]})
df_out_cdc.to_csv('taipei_latest.csv', index=False)
print("✅ CDC CSV 檔案更新完成！")


# ==========================================
# 2. 取得北投區氣象預報 (中央氣象署 CWA)
# ==========================================
print("\n開始獲取 CWA 氣象資料...")
cwa_api_key = os.environ.get('CWA_API_KEY')
if not cwa_api_key:
    raise ValueError("找不到 CWA_API_KEY 環境變數，請檢查 GitHub Secrets 設定。")

cwa_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063"
params = {
    'Authorization': cwa_api_key,
    'locationName': '北投區',
    'elementName': 'MaxT,PoP12h'
}

res_weather = requests.get(cwa_url, params=params, timeout=30)
res_weather.raise_for_status()
weather_data = res_weather.json()

# 解析氣象元素
weather_elements = weather_data['records']['locations'][0]['location'][0]['weatherElement']
pop_data = next(item for item in weather_elements if item["elementName"] == "PoP12h")['time']
maxt_data = next(item for item in weather_elements if item["elementName"] == "MaxT")['time']

# 萃取數值並加入防呆處理 (若無資料則補 0)
try:
    max_t_val = float(maxt_data[0]['elementValue'][0]['value'])
except (IndexError, ValueError, KeyError):
    max_t_val = 0.0

try:
    pop_0018_val = float(pop_data[0]['elementValue'][0]['value']) / 100.0
except (IndexError, ValueError, KeyError):
    pop_0018_val = 0.0

try:
    pop_1824_val = float(pop_data[1]['elementValue'][0]['value']) / 100.0
except (IndexError, ValueError, KeyError):
    pop_1824_val = 0.0

# 輸出成 CSV
df_out_weather = pd.DataFrame({
    '白天最高溫(00-18)': [max_t_val],
    '00-18降雨': [pop_0018_val],
    '18-24降雨': [pop_1824_val]
})
df_out_weather.to_csv('beitou_weather_forecast.csv', index=False)
print("✅ CWA CSV 檔案更新完成！")

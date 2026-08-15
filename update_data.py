import os
import io
import requests
import pandas as pd

# ==========================================
# 1. 取得台北市類流感就診人次 (疾管署 CDC)
# ==========================================
cdc_url = "https://od.cdc.gov.tw/eic/NHI_Influenza_like_illness.csv"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print("嘗試直接連線至 CDC 獲取資料...")
    response = requests.get(cdc_url, headers=headers, timeout=15)
    response.raise_for_status()
    csv_text = response.text
except requests.exceptions.RequestException as e:
    print(f"直接連線失敗 ({e})，啟動 AllOrigins 備用代理伺服器連線...")
    # 透過 allorigins.win 的 raw API 作為跳板，繞過 CDC 的區域封鎖
    proxy_url = f"https://api.allorigins.win/raw?url={cdc_url}"
    response = requests.get(proxy_url, headers=headers, timeout=60)
    response.raise_for_status()
    csv_text = response.text

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
print("✅ CDC 類流感資料更新成功！")


# ==========================================
# 2. 取得北投區氣象預報 (中央氣象署 CWA)
# ==========================================
cwa_api_key = os.environ.get('CWA-319B349C-4179-478B-860A-DEC589456C90')
if not cwa_api_key:
    raise ValueError("找不到 CWA_API_KEY 環境變數，請檢查 GitHub Secrets 設定。")

cwa_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063"
params = {
    'Authorization': cwa_api_key,
    'locationName': '北投區',
    'elementName': 'MaxT,PoP12h'
}

print("嘗試取得 CWA 氣象資料...")
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
print("✅ CWA 氣象資料更新成功！")

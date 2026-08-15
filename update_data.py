import os
import requests
import pandas as pd

# ==========================================
# 取得北投區氣象預報 (中央氣象署 CWA)
# ==========================================
print("開始獲取 CWA 氣象資料...")
cwa_api_key = os.environ.get('CWA_API_KEY')

if not cwa_api_key:
    raise ValueError("❌ 找不到 CWA_API_KEY 環境變數，請檢查 GitHub Secrets 設定。")

cwa_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063"
params = {
    'Authorization': cwa_api_key,
    'locationName': '北投區',
    'elementName': 'MaxT,PoP12h'
}

try:
    # 嘗試連線氣象署 API
    res_weather = requests.get(cwa_url, params=params, timeout=30)
    res_weather.raise_for_status()
    weather_data = res_weather.json()
    print("✅ 成功連線中央氣象署 API！")
except Exception as e:
    raise RuntimeError(f"❌ 連線氣象署失敗: {e}")

# 解析 JSON 樹狀結構
try:
    weather_elements = weather_data['records']['locations'][0]['location'][0]['weatherElement']
    pop_data = next(item for item in weather_elements if item["elementName"] == "PoP12h")['time']
    maxt_data = next(item for item in weather_elements if item["elementName"] == "MaxT")['time']
except Exception as e:
    raise RuntimeError(f"❌ 解析氣象資料結構失敗，可能是氣象署回傳格式有變: {e}")

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

# 建立 DataFrame 並輸出成 CSV
df_out_weather = pd.DataFrame({
    '白天最高溫(00-18)': [max_t_val],
    '00-18降雨': [pop_0018_val],
    '18-24降雨': [pop_1824_val]
})

df_out_weather.to_csv('beitou_weather_forecast.csv', index=False)
print("✅ CWA 氣象資料更新完成，已成功輸出 beitou_weather_forecast.csv！")

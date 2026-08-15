import os
import json
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
    res_weather = requests.get(cwa_url, params=params, timeout=30)
    res_weather.raise_for_status()
    weather_data = res_weather.json()
    print("✅ 成功連線中央氣象署 API！")
except Exception as e:
    raise RuntimeError(f"❌ 連線氣象署失敗: {e}")

# 解析 JSON 樹狀結構 (加入防呆與自動偵測機制)
try:
    records = weather_data.get('records', {})
    
    # 氣象署的 JSON 結構有時是 locations，有時是 location
    if 'locations' in records:
        weather_elements = records['locations'][0]['location'][0]['weatherElement']
    elif 'location' in records:
        weather_elements = records['location'][0]['weatherElement']
    else:
        # 如果都不是，就把氣象署實際傳來的內容完整印出來，讓我們知道發生什麼事！
        print("❌ 未知的資料格式！氣象署實際回傳的內容為：")
        print(json.dumps(weather_data, ensure_ascii=False, indent=2))
        raise KeyError("找不到 locations 或 location 欄位")

    pop_data = next(item for item in weather_elements if item["elementName"] == "PoP12h")['time']
    maxt_data = next(item for item in weather_elements if item["elementName"] == "MaxT")['time']
except Exception as e:
    print("❌ 解析氣象資料結構失敗，請查看上方的 JSON 內容。")
    raise e

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

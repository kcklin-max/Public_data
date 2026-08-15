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
    res_weather = requests.get(cwa_url, params=params, timeout=30)
    res_weather.raise_for_status()
    weather_data = res_weather.json()
    print("✅ 成功連線中央氣象署 API！")
except Exception as e:
    raise RuntimeError(f"❌ 連線氣象署失敗: {e}")

# 解析 JSON 樹狀結構 (修正大小寫與區域名稱對位)
try:
    records = weather_data.get('records', {})
    
    # 找尋 Locations 陣列
    locations_list = records.get('Locations') or records.get('locations') or []
    if not locations_list:
        raise KeyError("找不到 Locations 陣列")
        
    # 從 Locations 中找到包含 Location 陣列的那一層
    location_array = locations_list[0].get('Location') or locations_list[0].get('location')
    if not location_array:
        raise KeyError("找不到 Location 陣列")

    # 尋找 "北投區" 的資料
    target_location = None
    for loc in location_array:
        if loc.get('LocationName') == '北投區' or loc.get('locationName') == '北投區':
            target_location = loc
            break
            
    if not target_location:
         raise KeyError("在回傳資料中找不到『北投區』的資料，可能是 API 參數失效傳回全部或不包含該區")

    # 取得氣象元素列表
    weather_elements = target_location.get('WeatherElement') or target_location.get('weatherElement')

    # 尋找最高溫 (MaxT) 和 降雨機率 (PoP12h)
    pop_data = next(item for item in weather_elements if item["ElementName"] == "PoP12h" or item["elementName"] == "PoP12h")['Time']
    maxt_data = next(item for item in weather_elements if item["ElementName"] == "MaxT" or item["elementName"] == "MaxT")['Time']

except Exception as e:
    raise RuntimeError(f"❌ 解析氣象資料結構失敗，請檢查欄位大小寫: {e}")

# 萃取數值並加入防呆處理 (若無資料則補 0)
try:
    # 這裡的 JSON 結構也是大寫開頭 ElementValue, MaxTemperature, ProbabilityOfPrecipitation
    max_t_val = float(maxt_data[0]['ElementValue'][0].get('MaxTemperature') or maxt_data[0]['ElementValue'][0].get('value') or 0.0)
except (IndexError, ValueError, KeyError, TypeError):
    max_t_val = 0.0

try:
    pop_0018_val = float(pop_data[0]['ElementValue'][0].get('ProbabilityOfPrecipitation') or pop_data[0]['ElementValue'][0].get('value') or 0.0) / 100.0
except (IndexError, ValueError, KeyError, TypeError):
    pop_0018_val = 0.0

try:
    pop_1824_val = float(pop_data[1]['ElementValue'][0].get('ProbabilityOfPrecipitation') or pop_data[1]['ElementValue'][0].get('value') or 0.0) / 100.0
except (IndexError, ValueError, KeyError, TypeError):
    pop_1824_val = 0.0

# 建立 DataFrame 並輸出成 CSV
df_out_weather = pd.DataFrame({
    '白天最高溫(00-18)': [max_t_val],
    '00-18降雨': [pop_0018_val],
    '18-24降雨': [pop_1824_val]
})

df_out_weather.to_csv('beitou_weather_forecast.csv', index=False)
print("✅ CWA 氣象資料更新完成，已成功輸出 beitou_weather_forecast.csv！")

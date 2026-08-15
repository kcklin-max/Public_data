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
    # 參數同時加上中英文，盡量讓 API 吐出我們要的資料
    'elementName': '最高溫度,12小時降雨機率,MaxT,PoP12h' 
}

try:
    res_weather = requests.get(cwa_url, params=params, timeout=30)
    res_weather.raise_for_status()
    weather_data = res_weather.json()
    print("✅ 成功連線中央氣象署 API！")
except Exception as e:
    raise RuntimeError(f"❌ 連線氣象署失敗: {e}")

# 解析 JSON 樹狀結構 (使用 .get() 確保找不到 key 時不會當機)
try:
    records = weather_data.get('records', {})
    
    locations_list = records.get('Locations') or records.get('locations') or []
    if not locations_list:
        raise KeyError("找不到 Locations 陣列")
        
    location_array = locations_list[0].get('Location') or locations_list[0].get('location')
    if not location_array:
        raise KeyError("找不到 Location 陣列")

    # 尋找 "北投區"
    target_location = None
    for loc in location_array:
        loc_name = loc.get('LocationName') or loc.get('locationName')
        if loc_name == '北投區':
            target_location = loc
            break
            
    if not target_location:
         raise KeyError("在回傳資料中找不到『北投區』的資料")

    weather_elements = target_location.get('WeatherElement') or target_location.get('weatherElement') or []

    # 尋找降雨與溫度資料
    pop_data = None
    maxt_data = None
    
    for item in weather_elements:
        name = item.get("ElementName") or item.get("elementName") or ""
        # 同時比對英文與中文名稱
        if name in ["PoP12h", "12小時降雨機率", "降雨機率"]:
            pop_data = item.get('Time') or item.get('time')
        elif name in ["MaxT", "最高溫度"]:
            maxt_data = item.get('Time') or item.get('time')

    if pop_data is None or maxt_data is None:
        raise KeyError("找不到『降雨機率』或『最高溫度』的欄位")

except Exception as e:
    raise RuntimeError(f"❌ 解析氣象資料結構失敗: {e}")

# 設計一個安全抓取數值的輔助函數
def get_val(time_list, index):
    try:
        val_list = time_list[index].get('ElementValue') or time_list[index].get('elementValue')
        val_dict = val_list[0]
        # 直接抓取字典裡面的第一個值 (不管它的 key 叫 MaxTemperature 還是 value)
        raw_val = list(val_dict.values())[0]
        # 去除空白，若為空字串或有問題則給 0
        if str(raw_val).strip() == "":
            return 0.0
        return float(raw_val)
    except Exception:
        return 0.0

# 萃取數值
max_t_val = get_val(maxt_data, 0)
pop_0018_val = get_val(pop_data, 0) / 100.0
pop_1824_val = get_val(pop_data, 1) / 100.0

# 建立 DataFrame 並輸出成 CSV
df_out_weather = pd.DataFrame({
    '白天最高溫(00-18)': [max_t_val],
    '00-18降雨': [pop_0018_val],
    '18-24降雨': [pop_1824_val]
})

df_out_weather.to_csv('beitou_weather_forecast.csv', index=False)
print(f"✅ 成功抓取數值：最高溫={max_t_val}, 白天降雨={pop_0018_val}, 晚間降雨={pop_1824_val}")
print("✅ CWA 氣象資料更新完成，已成功輸出 beitou_weather_forecast.csv！")

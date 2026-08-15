library(httr)
library(jsonlite)
library(dplyr)
library(readr)

# ==========================================
# 0. 全域設定
# ==========================================
options(timeout = 120)

# ==========================================
# 1. 取得台北市類流感就診人次 (疾管署 CDC)
# ==========================================
# 【關鍵修正】：在原本的 CDC 網址前面，加上 corsproxy.io 這個免費代理服務作為跳板
# 這樣 CDC 防火牆就不會直接看到是 GitHub 發出的請求而封鎖我們
cdc_url <- "https://corsproxy.io/?https://od.cdc.gov.tw/eic/NHI_Influenza_like_illness.csv"

# 透過代理伺服器直接讀取即可
cdc_data <- read_csv(cdc_url, show_col_types = FALSE)

# 找出資料庫中「最新的一年」以及「該年的最新一週」
latest_year <- max(cdc_data$年, na.rm = TRUE)
latest_week <- max(cdc_data$週[cdc_data$年 == latest_year], na.rm = TRUE)

# 篩選台北市最新一週的資料並加總 (門診+急診總人次，供預測模組使用)
taipei_latest <- cdc_data %>%
  filter(縣市 == "台北市", 年 == latest_year, 週 == latest_week) %>%
  summarise(`急診就診人次` = sum(類流感健保就診人次, na.rm = TRUE))

# 輸出 CSV 覆寫舊檔
write_csv(taipei_latest, "taipei_latest.csv")


# ==========================================
# 2. 取得北投區氣象預報 (中央氣象署 CWA)
# (氣象署的 API 允許海外連線，因此維持不變)
# ==========================================
# 從 GitHub Secrets 讀取環境變數 (保護 API Key 不外流)
cwa_api_key <- Sys.getenv("CWA_API_KEY") 
url_weather <- paste0("https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063?",
                      "Authorization=", cwa_api_key, 
                      "&locationName=北投區",
                      "&elementName=MaxT,PoP12h")

response <- GET(url_weather)
weather_json <- fromJSON(content(response, "text", encoding = "UTF-8"))

# 解析氣象元素 (對應氣象署 JSON 樹狀結構)
weather_elements <- weather_json$records$locations$location[[1]]$weatherElement[[1]]

# 擷取降雨機率 (PoP12h) 與 最高溫 (MaxT) 列表
pop_data <- weather_elements %>% filter(elementName == "PoP12h") %>% pull(time) %>% .[[1]]
maxt_data <- weather_elements %>% filter(elementName == "MaxT") %>% pull(time) %>% .[[1]]

# 萃取數值並加入 NA 防呆處理 (若無資料則補 0)
max_t_val <- as.numeric(maxt_data$elementValue[[1]]$value[1])
pop_0018_val <- as.numeric(pop_data$elementValue[[1]]$value[1])
pop_1824_val <- as.numeric(pop_data$elementValue[[2]]$value[1])

# 建立 Shiny 需要的氣象資料格式 (降雨機率除以 100 轉為小數)
beitou_weather <- data.frame(
  `白天最高溫(00-18)` = ifelse(is.na(max_t_val), 0, max_t_val),
  `00-18降雨` = ifelse(is.na(pop_0018_val), 0, pop_0018_val) / 100, 
  `18-24降雨` = ifelse(is.na(pop_1824_val), 0, pop_1824_val) / 100,
  check.names = FALSE
)

# 輸出 CSV 覆寫舊檔
write_csv(beitou_weather, "beitou_weather_forecast.csv")

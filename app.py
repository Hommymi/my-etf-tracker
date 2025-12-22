import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(
    page_title="00929 持股監控小幫手",
    page_icon="📈",
    layout="wide"
)

st.title("📊 00929 復華台灣科技優息 - 持股即時監控")

# 2. 定義資料抓取函式 (加入更強的模擬機制)
@st.cache_data(ttl=3600)  # 每小時自動更新一次
def get_etf_data():
    url = "https://www.fhtrust.com.tw/api/Etf/GetEtfStock"
    payload = {"fundId": "ETF23", "lang": "CH"}
    
    # 這裡是最關鍵的 Headers，模擬真人瀏覽器行為
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.fhtrust.com.tw/ETF/etf_detail/ETF23",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.fhtrust.com.tw"
    }
    
    try:
        # 發送 POST 請求
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        # 檢查伺服器狀態
        if response.status_code != 200:
            st.error(f"❌ 伺服器連線失敗，錯誤代碼：{response.status_code}")
            return None
        
        # 嘗試解析 JSON
        json_data = response.json()
        
        if 'data' not in json_data:
            st.error("❌ 抓取成功但資料格式不符")
            return None
            
        # 轉換為 DataFrame
        df = pd.DataFrame(json_data['data'])
        
        # 篩選欄位並重新命名
        df = df[['STOCK_ID', 'STOCK_NAME', 'HOLD_QTY', 'RATIO']]
        df.columns = ['代碼', '名稱', '持股數', '權重%']
        
        # 轉換數值型態
        df['持股數'] = pd.to_numeric(df['持股數'], errors='coerce')
        df['權重%'] = pd.to_numeric(df['權重%'], errors='coerce')
        
        return df

    except Exception as e:
        st.error(f"⚠️ 發生錯誤: {str(e)}")
        return None

#

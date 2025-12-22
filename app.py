import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3

# 禁用 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 網頁基本設定
st.set_page_config(page_title="2317 鴻海股價監控", page_icon="🍎", layout="wide")

st.title("📈 2317 鴻海 - 本月每日成交報表")

@st.cache_data(ttl=3600)
def get_stock_history(stock_id="2317"):
    # 取得當前年月 (格式: 20240501)
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={stock_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # verify=False 解決 SSLCertVerificationError
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        data = response.json()
        
        if data.get('stat') == 'OK':
            # 建立 DataFrame
            df = pd.DataFrame(data['data'], columns=data['fields'])
            
            # 資料清理：移除逗號並轉為數值
            for col in ['收盤價', '開盤價', '最高價', '最低價',

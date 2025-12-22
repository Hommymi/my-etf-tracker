import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告 (避免連線證交所時噴出警告訊息)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 設定頁面語系與標題 ---
st.set_page_config(page_title="光電三傑監控中心", layout="wide")
st.title("📊 3714 富采 | 6854 錼創 | 3593 力銘 整合監控")
st.caption(f"數據更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (每日僅向證交所請求一次)")

# --- 定義股票對照表 ---
# STOCK_MAP 用於 PDF (純英文避開編碼報錯)
STOCK_MAP = {
    "3714": "Ennostar", 
    "6854": "PlayNitride", 
    "3593": "Leading"
}
# DISPLAY_NAMES 用於網頁顯示 (支援中文)
DISPLAY_NAMES = {
    "3714": "富采", 
    "6854": "錼創科技-KY", 
    "3593": "力銘"
}

# --- 核心抓取函式 (設定 ttl=86400 即 24 小時才抓一次新資料) ---
@st.cache_data(ttl=86400)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # verify=False 增加連線成功率
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        data = res.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 資料清理：移除逗號與符號，轉換

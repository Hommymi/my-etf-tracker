import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF
import os

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="面板/光電股監控中心", layout="wide")
st.title("📊 3714 富采 | 6854 錼創 | 3593 力銘")

# --- 抓取資料 (10分鐘更新一次) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK' and 'data' in data:
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 統一欄位名稱，確保 PDF 讀得到
            df.rename(columns={'成交金額': '成交值', '成交股數': '成交量'}, inplace=True)
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}
all_data = {sid: fetch_twse_data(sid) for sid in DISPLAY_NAMES.keys()}

tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

# --- PDF 產生器 (核心修正版) ---
def create_advanced_pdf(data_dict):
    pdf = FPDF()
    font_path = "chinese.ttf"
    
    # 檢查字體
    use_chinese = False
    if os.path.exists(font_path):
        try:
            pdf.add_font('ChineseFont', '', font_path, uni=True)
            use_chinese = True
        except: pass

    for sid, df in data_dict.items():
        if df is not None and not df.empty:
            pdf.add_page()
            
            # 設定字體與標題
            if use_chinese:
                pdf.set_font('ChineseFont', '', 16)
                title = f"股票詳細報表 - {sid} {DISPLAY_NAMES.get(sid, '')}"
                header = ["日期", "最高價", "最低價", "收盤價", "漲跌"]
            else:
                pdf.set_font('Arial', 'B', 16)
                title = f"Stock Detail Report - {sid}"
                header = ["Date", "High", "Low", "Close", "Diff"]
            
            pdf.cell(1

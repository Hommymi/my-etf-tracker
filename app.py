import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股雙強監控整合版", layout="wide")
st.title("📊 2317 鴻海 & 2330 台積電 整合監控中心")

# --- 抓取資料函式 ---
@st.cache_data(ttl=3600)
def fetch_data(sid):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m%d')}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        data = res.json()
        if data.get('stat') == 'OK':
            temp_df = pd.DataFrame(data['data'], columns=data['fields'])
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                temp_df[col] = temp_df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            return temp_df
        return None
    except: return None

# --- 產生聯合 PDF 函式 ---
def create_combined_pdf(data_dict):
    pdf = FPDF()
    for stock_id, df in data_dict.items():
        if df is not None:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt=f"Stock Analysis Report: {stock_id}", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(190, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
            pdf.ln(5)
            # 表格標頭
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(45, 10, "Date", 1, 0, 'C', True)
            pdf.cell(45, 10, "Close", 1, 0, 'C', True)
            pdf.cell(45, 10, "Change", 1, 0, 'C', True)
            pdf.cell(45, 10, "High/Low", 1, 1, 'C', True)
            # 表格內容
            pdf.set_font("Arial", size=10)
            display_df = df.sort_index(ascending=False).head(15)
            for i in range(len(display_df)):
                row = display_df.iloc[i]
                pdf.cell(45, 10, str(row['日期']), 1)
                pdf.cell(45, 10, str(row['收盤價']), 1)
                pdf.cell(45, 10, str(row['漲跌價差']), 1)
                pdf.cell(45, 10, f"{row['最高價']}/{row['最低價']}", 1)
                pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- 讀取兩份資料 ---
df_2317 = fetch_data("2317")
df_2330 = fetch_data("2330")

# --- 介面佈局：分頁標籤 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載中心"])

with tab1:

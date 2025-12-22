import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF
import io

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股監控報表", layout="wide")

# --- PDF 產生邏輯 (採用英文標籤以確保不亂碼) ---
def create_pdf_report(df, stock_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # 標題
    pdf.cell(190, 10, txt=f"Stock Report: {stock_id}", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # 表格標頭
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(45, 10, "Date", 1, 0, 'C', True)
    pdf.cell(45, 10, "Close Price", 1, 0, 'C', True)
    pdf.cell(45, 10, "Change", 1, 0, 'C', True)
    pdf.cell(45, 10, "High/Low", 1, 1, 'C', True)
    
    # 表格內容 (取最近 15 筆)
    pdf.set_font("Arial", size=10)
    for i in range(min(len(df), 15)):
        row = df.iloc[i]
        pdf.cell(45, 10, str(row['日期']), 1)
        pdf.cell(45, 10, str(row['收盤價']), 1)
        pdf.cell(45, 10, str(row['漲跌價差']), 1)
        pdf.cell(45, 10, f"{row['最高價']}/{row['最低價']}", 1)
        pdf.ln()
    
    # 輸出為 Bytes
    return pdf.output(dest='S').encode('latin-1')

# --- 側邊欄 ---
st.sidebar.title("🔍 選股設定")
stock_option = st.sidebar.selectbox("選擇股票：", ("2317 鴻海", "2330 台積電", "自定義"))
stock_id = stock_option.split(" ")[0] if stock_option != "自定義" else st.sidebar.text_input("輸入代碼", "2454")

# --- 抓取資料 ---
@st.cache_data(ttl=3600)
def fetch_data(sid):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m%d')}&stockNo={sid}"
    try:
        res = requests.get(url, verify=False, timeout=15)
        data = res.json()
        if data.get('stat') == 'OK':
            temp_df = pd.DataFrame(data['data'], columns=data['fields'])
            for col in ['收盤價', '開盤價', '最高價', '最低價', '漲跌價差']:
                temp_df[col] = temp_df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            return temp_df
        return None
    except: return None

df = fetch_data(stock_id)

if df is not None:
    st.title(f"📊 {stock_id} 數據儀表板")
    
    # 下載按鈕區
    col_dl1, col_dl2 = st.columns(2)
    
    # 1. CSV 下載
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    col_dl1.download_button(f"📥 下載 {stock_id} CSV", csv_data, f"{stock_id}.csv", "text/csv")
    
    # 2. PDF 下載
    try:
        pdf_bytes = create_pdf_report(df.sort_index(ascending=False), stock_id)
        col_dl2.download_button(f"📄 產生 {stock_id} PDF 報表", pdf_bytes, f"{stock_id}_report.pdf", "application/pdf")
    except Exception as e:
        col_dl2.error("PDF 產生失敗")

    # 走勢圖
    fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color='#FF4B4B')))
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.error("連線失敗，請稍後再試。")

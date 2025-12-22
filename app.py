import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股雙強監控", layout="wide")
st.title("📈 2317 鴻海 & 2330 台積電 聯合報表")

# --- 抓取資料函式 ---
@st.cache_data(ttl=3600)
def fetch_data(sid):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m%d')}&stockNo={sid}"
    try:
        res = requests.get(url, verify=False, timeout=15)
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
            pdf.cell(190, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
            pdf.ln(5)
            
            # 表格標頭
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(45, 10, "Date", 1, 0, 'C', True)
            pdf.cell(45, 10, "Close", 1, 0, 'C', True)
            pdf.cell(45, 10, "Change", 1, 0, 'C', True)
            pdf.cell(45, 10, "High/Low", 1, 1, 'C', True)
            
            # 表格內容 (前 15 筆)
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

# --- 介面佈局 ---
col_2317, col_2330 = st.columns(2)

with col_2317:
    st.subheader("🍎 2317 鴻海")
    if df_2317 is not None:
        st.metric("收盤價", f"{df_2317.iloc[-1]['收盤價']}")
        fig1 = go.Figure(go.Scatter(x=df_2317['日期'], y=df_2317['收盤價'], name="2317", line=dict(color='red')))
        st.plotly_chart(fig1, use_container_width=True)

with col_2330:
    st.subheader("💎 2330 台積電")
    if df_2330 is not None:
        st.metric("收盤價", f"{df_2330.iloc[-1]['收盤價']}")
        fig2 = go.Figure(go.Scatter(x=df_2330['日期'], y=df_2330['收盤價'], name="2330", line=dict(color='blue')))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- 下載區 ---
st.subheader("📥 聯合報表下載")
if df_2317 is not None and df_2330 is not None:
    combined_pdf = create_combined_pdf({"2317": df_2317, "2330": df_2330})
    st.download_button(
        label="📄 下載 2317+2330 聯合 PDF 報表",
        data=combined_pdf,
        file_name="Combined_Stock_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.error("部分資料抓取失敗，無法產生聯合報表。")

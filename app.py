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
            
            pdf.cell(190, 10, txt=title, ln=True, align='C')
            pdf.ln(5)
            
            # 表格標頭繪製
            pdf.set_fill_color(220, 230, 241)
            pdf.set_font('Arial' if not use_chinese else 'ChineseFont', '', 10)
            widths = [40, 35, 35, 40, 40]
            for i, h in enumerate(header):
                pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
            pdf.ln()
            
            # 填入數據 (使用安全取值方式避免 Index Error)
            pdf.set_font('Arial', '', 9)
            recent_df = df.tail(15).iloc[::-1]
            
            for _, row in recent_df.iterrows():
                # 使用 row.get() 確保欄位不存在時不會崩潰
                pdf.cell(40, 7, str(row.get('日期', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最高價', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最低價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('收盤價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('漲跌價差', '--')), 1, 1, 'C')
                
    return pdf.output(dest='S')

with tab1:
    cols = st.columns(3)
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(width=3)))
                fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {sid} {name}")
        if all_data.get(sid) is not None:
            st.dataframe(all_data[sid].sort_index(ascending=False), use_container_width=True)

with tab3:
    st.subheader("📦 下載 PDF 報表")
    if any(df is not None for df in all_data.values()):
        try:
            raw_pdf = create_advanced_pdf(all_data)
            pdf_bytes = raw_pdf if isinstance(raw_pdf, (bytes, bytearray)) else raw_pdf.encode('latin-1')
            st.download_button(
                label="📄 點此下載完整 PDF 報表",
                data=pdf_bytes,
                file_name=f"Stock_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF 產製錯誤: {e}")

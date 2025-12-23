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

# --- 頁面基本設定 ---
st.set_page_config(page_title="Liteon 有價證券監控", layout="wide")
st.title("📊 Liteon 有價證券 (3714 | 6854 | 3593)")
st.caption(f"自動更新頻率：每 10 分鐘 | 最後檢查時間：{datetime.now().strftime('%H:%M:%S')}")

# --- 核心抓取函式 (TTL 600秒 = 10分鐘) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK' and 'data' in data:
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 資料清理與轉換
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except Exception as e:
        return None

# 定義股票對照
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}
all_data = {sid: fetch_twse_data(sid) for sid in DISPLAY_NAMES.keys()}

# --- PDF 產生邏輯 (支援分頁與中文) ---
def create_advanced_pdf(data_dict):
    pdf = FPDF()
    font_path = "chinese.ttf"  # 確保此檔案存在於 GitHub 根目錄
    
    # 檢查字體並嘗試載入
    if os.path.exists(font_path):
        try:
            pdf.add_font('ChineseFont', '', font_path, uni=True)
            font_name = 'ChineseFont'
            use_chinese = True
        except:
            font_name = 'Arial'
            use_chinese = False
    else:
        font_name = 'Arial'
        use_chinese = False

    for sid, df in data_dict.items():
        if df is not None and not df.empty:
            pdf.add_page()
            
            # 頁面標題
            pdf.set_font(font_name, 'B' if not use_chinese else '', 16)
            title = f"個股詳細數據報表 - {sid} {DISPLAY_NAMES.get(sid, '')}" if use_chinese else f"Stock Report - {sid}"
            pdf.cell(190, 10, txt=title, ln=True, align='C')
            pdf.ln(5)
            
            # 表格標頭
            pdf.set_font(font_name, '', 10)
            pdf.set_fill_color(220, 230, 241)
            header = ["日期", "最高價", "最低價", "收盤價", "漲跌價差"] if use_chinese else ["Date", "High", "Low", "Close", "Change"]
            widths = [40, 35, 35, 40, 40]
            for i, h in enumerate(header):
                pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
            pdf.ln()
            
            # 填入數據 (最新 20 筆)
            pdf.set_font(font_name, '', 9)
            recent_df = df.tail(20).iloc[::-1]
            for _, row in recent_df.iterrows():
                pdf.cell(40, 7, str(row.get('日期', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最高價', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最低價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('收盤價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('漲跌價差', '--')), 1, 1, 'C')
                
    return pdf.output(dest='S')

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"{name} ({sid}) 數據讀取中...")

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {sid} {name} 詳細數據明細")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 產出 Liteon 有價證券 PDF 報表")
    st.info("系統將產出分頁報表：第一頁為富采、第二頁為錼創、第三頁為力銘。")
    
    if any(df is not None for df in all_data.values()):
        try:
            raw_pdf = create_advanced_pdf(all_data)
            # 轉換為位元組流
            pdf_bytes = raw_pdf if isinstance(raw_pdf, (bytes, bytearray)) else raw_pdf.encode('latin-1')
            
            st.download_button(
                label="📄 下載中文分頁報表 (PDF)",
                data=pdf_bytes,
                file_name=f"Liteon_Stock_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF 製作錯誤: {e}")
    else:
        st.warning("目前暫無數據，請確認連線。")

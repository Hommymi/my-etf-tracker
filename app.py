import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="面板/光電股監控中心", layout="wide")
st.title("📊 3714 富采 | 6854 錼創 | 3593 力銘")
st.caption(f"自動更新頻率：每 10 分鐘一次 | 最後檢查時間：{datetime.now().strftime('%H:%M:%S')}")

# --- 抓取資料 (設定 10 分鐘請求一次) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 轉換數值並清理符號
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

# 定義股票對照 (PDF 用英文避開編碼報錯)
STOCK_MAP = {"3714": "Ennostar", "6854": "PlayNitride", "3593": "Leading"}
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}

# 執行抓取
all_data = {sid: fetch_twse_data(sid) for sid in STOCK_MAP.keys()}

tab1, tab2, tab3 = st.tabs(["📈 即時走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} 讀取中...")

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 報表匯出系統")
    
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, txt="Daily Stock Report", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        
        for sid, df in data_dict.items():
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                en_name = STOCK_MAP[sid]
                # 確保內容完全沒有中文，避免 latin-1 編碼錯誤
                line = f"Ticker: {sid} ({en_name}) | Price: {latest['收盤價']} | Change: {latest['漲跌價差']}"
                pdf.cell(190, 10, txt=line, ln=True)
        
        # 使用 bytearray 處理輸出
        return pdf.output(dest='S')

    if any(df is not None for df in all_data.values()):
        try:
            raw_pdf = create_pdf(all_data)
            # 確保輸出為 bytes 格式供 Streamlit 下載
            pdf_bytes = raw_pdf if isinstance(raw_pdf, bytes) else raw_pdf.encode('latin-1')
            
            st.download_button(
                label="📄 下載 PDF 報表 (英文版)",
                data=pdf_bytes,
                file_name=f"Stock_Report_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"報表製作錯誤: {e}")

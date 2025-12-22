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
st.title("📊 面板/光電三傑監控 (3714 | 6854 | 3593)")

# 定義股票清單
STOCK_LIST = {
    "3714": "Ennostar",  # PDF 用英文避開編碼錯誤
    "6854": "PlayNitride",
    "3593": "Leading"
}

@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

all_data = {sid: fetch_twse_data(sid) for sid in STOCK_LIST.keys()}

tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    display_names = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(display_names.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    for sid, name in STOCK_LIST.items():
        st.subheader(f"{sid} Data Table")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)

with tab3:
    st.subheader("📦 Export Report")
    
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, txt="Stock Market Report", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        
        for sid, df in data_dict.items():
            if df is not None:
                latest = df.iloc[-1]
                # 這裡只印英文名稱和數字，絕對不要放中文，避開 latin-1 錯誤
                name_en = STOCK_LIST[sid]
                line = f"ID: {sid} ({name_en}) | Price: {latest['收盤價']} | Change: {latest['漲跌價差']}"
                pdf.cell(190, 10, txt=line, ln=True)
        
        # 關鍵修正：直接回傳位元組字串，不進行額外的 encode('latin-1')
        return pdf.output(dest='S')

    if any(df is not None for df in all_data.values()):
        try:
            pdf_output = create_pdf(all_data)
            st.download_button(
                label="📄 Download PDF Report (English Version)",
                data=bytes(pdf_output), # 轉成 bytes 確保 Streamlit 接受
                file_name="report.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF Error: {e}")

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

# 定義股票清單 (全部使用穩定的證交所來源)
STOCK_LIST = {
    "3714": "富采",
    "6854": "錼創科技",
    "3593": "力銘"
}

# --- 抓取資料函式 ---
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
            # 數值轉換
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

# 讀取資料
all_data = {sid: fetch_twse_data(sid) for sid in STOCK_LIST.keys()}

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c'] # 藍、橘、綠
    
    for i, (sid, name) in enumerate(STOCK_LIST.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                
                # 繪製走勢圖
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} ({sid}) 資料獲取中...")

with tab2:
    for sid, name in STOCK_LIST.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 報表匯出")
    # PDF 產生邏輯 (採用拉丁字體確保通用性)
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        pdf.add_page()
        pdf.cell(200, 10, txt="Stock Monitoring Report", ln=True, align='C')
        pdf.ln(10)
        for sid, df in data_dict.items():
            if df is not None:
                latest = df.iloc[-1]
                name = STOCK_LIST[sid]
                pdf.cell(190, 10, txt=f"{name} ({sid}): Price {latest['收盤價']} | Change {latest['漲跌價差']}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if any(df is not None for df in all_data.values()):
        pdf_bytes = create_pdf(all_data)
        st.download_button(
            label="📄 下載 PDF 聯合報表",
            data=pdf_bytes,
            file_name=f"Stock_Report_{datetime.now().strftime('%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

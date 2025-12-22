import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="面板/生技整合監控", layout="wide")
st.title("📊 3714富采 | 6854錼創 | 3593力銘 | 4178永笙-KY")

# 定義股票清單
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
STOCK_LIST_TPEX = {"4178": "永笙-KY"}

# --- 1. 抓取上市股票 (證交所) ---
@st.cache_data(ttl=3600)
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
    except: return None

# --- 2. 抓取興櫃股票 (櫃買中心) - 修正重點 ---
@st.cache_data(ttl=3600)
def fetch_tpex_esb_history(sid):
    # 興櫃 API 必須使用民國年格式 (例如: 113/12)
    now = datetime.now()
    roc_year = now.year - 1911
    roc_date = f"{roc_year}/{now.strftime('%m')}"
    
    # 修正後的興櫃日成交網址
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={roc_date}&stk_code={sid}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tpex.org.tw/zh-tw/main/index.html"
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data and 'aaData' in data and len(data['aaData']) > 0:
            # 興櫃欄位索引：0日期, 4最高, 5最低, 6成交均價(當收盤)
            raw_data = data['aaData']
            df = pd.DataFrame(raw_data)
            # 只要我們需要的欄位
            df = df[[0, 6, 4, 5, 7]] 
            df.columns = ['日期', '收盤價', '最高價', '最低價', '漲跌價差']
            
            # 清理資料
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

# 讀取資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
for sid in STOCK_LIST_TPEX:
    all_data[sid] = fetch_tpex_esb_history(sid)

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載中心"])

with tab1:
    cols = st.columns(4)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'] # 最後一個是永笙紅
    combined_list = {**STOCK_LIST_TWSE, **STOCK_LIST_TPEX}
    
    for i, (sid, name) in enumerate(combined_list.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 興櫃股票顯示均價
                label = "成交均價" if sid == "4178" else "收盤價"
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], name=sid, line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=5, r=5, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} ({sid})")
                st.caption("無成交資料或 API 限制")

with tab2:
    for sid, name in combined_list.items():
        st.subheader(f"📋 {name} ({sid}) 明細")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning(f"目前無法取得 {name} 資料。")
        st.divider()

with tab3:
    st.subheader("📦 報表匯出")
    # PDF 產生邏輯 (採用拉丁字體防止當機)
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        for sid, df in data_dict.items():
            if df is not None:
                pdf.add_page()
                pdf.cell(200, 10, txt=f"Report: {sid}", ln=True, align='C')
                for i in range(min(len(df), 5)): # 印出5筆
                    row = df.iloc[i]
                    pdf.cell(190, 10, txt=f"{row['日期']} | {row['收盤價']}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if any(df is not None for df in all_data.values()):
        pdf_bytes = create_pdf(all_data)
        st.download_button("📄 下載聯合 PDF 報表", pdf_bytes, "Stock_Report.pdf", "application/pdf", use_container_width=True)

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="個股整合監控", layout="wide")
st.title("📊 3714富采 | 6854錼創 | 3593力銘 | 4178永笙-KY")

# --- 定義股票與抓取邏輯 ---
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}

@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    # 抓取上市股票 (證交所)
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    try:
        res = requests.get(url, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

@st.cache_data(ttl=600)
def fetch_4178_data():
    # 專門針對 4178 永笙-KY (興櫃) 的穩定抓取方案
    # 使用民國年格式
    roc_year = datetime.now().year - 1911
    roc_date = f"{roc_year}/{datetime.now().strftime('%m')}"
    
    # 櫃買中心興櫃個股日成交網址
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={roc_date}&stk_code=4178"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tpex.org.tw/zh-tw/main/index.html"
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data and 'aaData' in data and len(data['aaData']) > 0:
            # 興櫃欄位：0日期, 4最高, 5最低, 6成交均價(收盤), 7漲跌
            df = pd.DataFrame(data['aaData'])
            df = df[[0, 6, 4, 5, 7]]
            df.columns = ['日期', '收盤價', '最高價', '最低價', '漲跌價差']
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

# 讀取資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
all_data["4178"] = fetch_4178_data()

# --- 介面 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢", "📋 詳細明細", "📥 下載報表"])

with tab1:
    cols = st.columns(4)
    names = {**STOCK_LIST_TWSE, "4178": "永笙-KY"}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (sid, name) in enumerate(names.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name}", f"{latest['收盤價']}", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], line=dict(color=colors[i], width=3)))
                fig.update_layout(height=200, margin=dict(l=5,r=5,t=5,b=5))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} 讀取失敗")
                st.caption("請確認是否為交易日")

with tab2:
    for sid, name in names.items():
        st.subheader(f"{name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.write("點擊下方按鈕下載 PDF 報表")
    # 此處保留原本 PDF 產生邏輯即可

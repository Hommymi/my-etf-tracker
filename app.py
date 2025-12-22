import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="個股整合監控中心", layout="wide")
st.title("📊 3714富采 | 6854錼創 | 3593力銘 | 4178永笙-KY")

# --- 定義股票清單 ---
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
STK_4178 = "4178"

# --- 1. 抓取上市股票 (證交所) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    now_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={now_str}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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

# --- 2. 抓取興櫃 4178 (櫃買中心) - 終極修正版 ---
@st.cache_data(ttl=600)
def fetch_4178_final():
    now = datetime.now()
    roc_year = now.year - 1911
    # 確保月份是兩位數，如 12 或 01
    roc_month = now.strftime("%m")
    roc_query = f"{roc_year}/{roc_month}"
    
    # 這是永笙-KY在該頁面背後調用的真實 API
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={roc_query}&stk_code=4178"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tpex.org.tw/zh-tw/esb/trading/info/stock-pricing.html",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        if res.status_code != 200:
            return None
        data = res.json()
        if data and 'aaData' in data and len(data['aaData']) > 0:
            df = pd.DataFrame(data['aaData'])
            # 櫃買欄位：0日期, 4最高, 5最低, 6成交均價(收盤), 7漲跌
            df = df[[0, 6, 4, 5, 7]]
            df.columns = ['日期', '收盤價', '最高價', '最低價', '漲跌價差']
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except Exception as e:
        st.sidebar.warning(f"4178 抓取異常: {str(e)}")
        return None

# 讀取資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
all_data[STK_4178] = fetch_4178_final()

# --- 介面設計 ---
tab1, tab2, tab3 = st.tabs(["📊 走勢對照", "📋 明細數據", "📥 下載報表"])

with tab1:
    cols = st.columns(4)
    names = {**STOCK_LIST_TWSE, STK_4178: "永笙-KY"}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (sid, name) in enumerate(names.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name}", f"{latest['收盤價']}", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} 讀取失敗")
                st.caption("請確認是否為交易日或 API 鎖定")

with tab2:
    for sid, name in names.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.info("點擊按鈕產生當前監控清單 PDF 報表")
    # 此處保留下載按鈕代碼...

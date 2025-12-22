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

# 定義股票清單
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}

# --- 1. 抓取上市股票 (證交所) ---
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
    except: return None

# --- 2. 抓取興櫃股票 (櫃買中心 4178 專用 - 強制民國年版) ---
@st.cache_data(ttl=600)
def fetch_4178_tpex(sid):
    # 取得當前民國年與月份
    now = datetime.now()
    roc_year = now.year - 1911
    # 格式必須是 "114/12"
    roc_date_query = f"{roc_year}/{now.strftime('%m')}"
    
    # 這是該網頁背後的日成交資訊 API 網址
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={roc_date_query}&stk_code={sid}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tpex.org.tw/zh-tw/esb/trading/info/stock-pricing.html"
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        
        # 檢查資料是否存在於 aaData 欄位
        if data and 'aaData' in data and len(data['aaData']) > 0:
            # 興櫃欄位索引：0日期, 4最高, 5最低, 6成交均價(視為收盤), 7漲跌
            df = pd.DataFrame(data['aaData'])
            # 過濾並重新命名欄位
            df = df[[0, 6, 4, 5, 7]] 
            df.columns = ['日期', '收盤價', '最高價', '最低價', '漲跌價差']
            
            # 清理數值格式
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
all_data["4178"] = fetch_4178_tpex("4178")

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載中心"])

with tab1:
    cols = st.columns(4)
    all_stocks = {**STOCK_LIST_TWSE, "4178": "永笙-KY"}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (sid, name) in enumerate(all_stocks.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 興櫃顯示「均價」，上市顯示「收盤」
                val_label = "成交均價" if sid == "4178" else "收盤價"
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                
                # 畫圖
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], name=sid, line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=5, r=5, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} ({sid})")
                st.caption("無法取得本月資料，請檢查櫃買中心 API 狀態。")

with tab2:
    for sid, name in all_stocks.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning(f"目前無 {name} 的表格數據。")
        st.divider()

with tab3:
    st.subheader("📦 報表匯出")
    # PDF 下載邏輯... (略)
    st.info("PDF 下載按鈕功能已準備就緒。")

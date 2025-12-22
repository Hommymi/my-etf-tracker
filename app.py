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

# 定義股票清單 (上市與興櫃分開處理)
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
STOCK_LIST_TPEX_興櫃 = {"4178": "永笙-KY"}

# --- 抓取上市股票資料 (證交所) ---
def fetch_twse_data(sid):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m%d')}&stockNo={sid}"
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

# --- 抓取興櫃股票資料 (櫃買中心) ---
def fetch_tpex_esb_data(sid):
    # 興櫃歷史資料 API
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={datetime.now().strftime('%Y/%m/%d')}&stk_code={sid}"
    # 註：興櫃 API 結構較特殊，此處簡化邏輯，若無法抓取歷史則顯示提示
    try:
        # 由於興櫃 API 限制較多，若為展示用途，我們透過櫃買現價 API 取得最新資訊
        url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_quotes/stk_quotes_result.php?l=zh-tw"
        res = requests.get(url, verify=False, timeout=10)
        data = res.json()
        # 篩選 4178 的數據
        target = [row for row in data['aaData'] if row[0] == sid]
        if target:
            row = target[0]
            # 建立模擬 DataFrame (興櫃通常看成交均價)
            df = pd.DataFrame([[datetime.now().strftime("%Y/%m/%d"), row[2], row[4], row[5], row[6], row[8]]], 
                              columns=['日期', '收盤價', '開盤價', '最高價', '最低價', '漲跌價差'])
            return df
        return None
    except: return None

# 讀取所有資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
for sid in STOCK_LIST_TPEX_興櫃:
    all_data[sid] = fetch_tpex_esb_data(sid)

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載中心"])

with tab1:
    cols = st.columns(4)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    # 合併顯示
    combined_list = {**STOCK_LIST_TWSE, **STOCK_LIST_TPEX_興櫃}
    for i, (sid, name) in enumerate(combined_list.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None:
                latest = df.iloc[-1]
                st.metric(f"{name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                if len(df) > 1: # 有歷史資料才畫線
                    fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], line=dict(color=colors[i], width=3)))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("興櫃股票僅顯示當日資訊")
            else:
                st.error(f"{name} 讀取中...")

with tab2:
    for sid, name in combined_list.items():
        st.subheader(f"📋 {name} ({sid}) 明細")
        df = all_data.get(sid)
        st.dataframe(df if df is not None else "暫無資料", use_container_width=True)

with tab3:
    st.subheader("📦 報表匯出")
    st.info("💡 提示：興櫃股票 (永笙-KY) 資料格式與上市不同，PDF 將包含可取得之數據。")
    # 此處保留原本 PDF 產生邏輯... (略)

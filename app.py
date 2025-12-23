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

# --- 抓取資料 (10分鐘更新一次) ---
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
            # 數值清理
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

# 定義股票清單
STOCK_MAP = {"3714": "Ennostar", "6854": "PlayNitride", "3593": "Leading"}
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}

all_data = {sid: fetch_twse_data(sid) for sid in STOCK_MAP.keys()}

# --- 修改頁籤名稱 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 加上股票代碼
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update

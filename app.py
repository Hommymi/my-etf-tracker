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

# --- 抓取上市股票 (證交所) ---
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
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

# --- 抓取興櫃股票 (櫃買中心即時行情 - 繞過歷史 API 阻擋) ---
@st.cache_data(ttl=600)
def fetch_tpex_esb_realtime(sid):
    # 這個 API 是櫃買中心「興櫃個股行情」最基礎的來源
    url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_quotes/stk_quotes_result.php?l=zh-tw"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tpex.org.tw/zh-tw/esb/trading/info/stock-pricing.html"
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        data = res.json()
        if data and 'aaData' in data:
            # 在所有興櫃股票中找出 4178
            target = [row for row in data['aaData'] if str(row[0]).strip() == str(sid)]
            if target:
                row = target[0]
                # 0代號, 2成交均價, 4開盤, 5最高, 6最低, 8漲跌
                df = pd.DataFrame([{
                    '日期': datetime.now().strftime("%Y/%m/%d"),
                    '收盤價': float(row[2]) if row[2] != '--' else 0.0,
                    '最高價': float(row[5]) if row[5] != '--' else 0.0,
                    '最低價': float(row[6]) if row[6] != '--' else 0.0,
                    '漲跌價差': row[8] if row[8] != '--' else "0"
                }])
                return df
        return None
    except Exception as e:
        # 在開發時可以看到錯誤原因
        st.sidebar.error(f"永笙連線異常: {e}")
        return None

# 讀取資料
all_data = {}
for sid in ["3714", "6854", "3593"]:
    all_data[sid] = fetch_twse_data(sid)
all_data["4178"] = fetch_tpex_esb_realtime("4178")

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載"])

with tab1:
    cols = st.columns(4)
    names = {"3714": "富采", "6854": "錼創科技", "3593": "力銘", "4178": "永笙-KY"}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (sid, name) in enumerate(names.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(name, f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                
                # 畫圖：上市股票畫線，興櫃(若只有今日)畫點
                fig = go.Figure()
                mode = 'markers' if len(df) == 1 else 'lines+markers'
                fig.add_trace(go.Scatter(x=df['日期'], y=df['收盤價'], mode=mode, line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=5, r=5, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} 讀取失敗")

with tab2:
    for sid, name in names.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df, use_container_width=True)
        st.divider()

with tab3:
    st.write("PDF 報表下載已準備")

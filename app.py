import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 頁面基本設定 ---
st.set_page_config(page_title="Liteon 有價證券監控", layout="wide")
st.title("📊 Liteon 有價證券 (6805 永笙-KY)")
st.caption(f"數據更新頻率：每 10 分鐘 | 最後檢查時間：{datetime.now().strftime('%H:%M:%S')}")

# --- 櫃買中心 (TPEX) 興櫃抓取函式 ---
@st.cache_data(ttl=600)
def fetch_tpex_6805():
    # 永笙-KY 是興櫃股票，使用興櫃成交行情 API
    # 這裡抓取最近的交易數據
    url = "https://www.tpex.org.tw/web/emergingstock/historical/daily_quotes/EMDailyQuo_result.php?l=zh-tw&stk_code=6805"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tpex.org.tw/"
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        
        # 檢查資料是否存在
        if 'aaData' in data and len(data['aaData']) > 0:
            # 櫃買中心興櫃欄位：0日期, 1成交股數, 2成交金額, 3開盤, 4最高, 5最低, 6收盤(均價), 7漲跌...
            raw_df = pd.DataFrame(data['aaData'])
            
            # 挑選關鍵欄位並重新命名
            df = raw_df[[0, 4, 5, 6, 3, 7]].copy()
            df.columns = ['日期', '最高價', '最低價', '收盤價', '開盤價', '漲跌價差']
            
            # 清理數值符號
            for col in ['最高價', '最低價', '收盤價', '開盤價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            return None
    except Exception as e:
        st.error(f"連線櫃買中心失敗: {e}")
        return None

# 定義股票清單 (針對單一股票優化)
sid = "6805"
name = "永笙-KY"
en_name = "StemCyte"

# 抓取資料
df_6805 = fetch_tpex_6805()

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    if df_6805 is not None and not df_6805.empty:
        latest = df_6805.iloc[-1]
        # 興櫃股票通常看「加權平均價」作為收盤
        st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
        
        fig = go.Figure(go.Scatter(
            x=df_6805['日期'], 
            y=df_6805['收盤價'], 
            mode='lines+markers',
            line=dict(color='#00CC96', width=3),
            name="均價"
        ))
        fig.update_layout(title=f"{name} 歷史均價走勢", height=400, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ 無法取得 6805 永笙-KY 的數據，可能是非交易時間或 API 限制。")

with tab2:
    st.subheader(f"📋 {sid} {name} 興櫃交易明細")

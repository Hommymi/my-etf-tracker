import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3

# 禁用安全警告（因為我們跳過了 SSL 驗證）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="2301 股價監控", layout="wide")
st.title("📈 2301 光寶科 - 本月每日成交報表")

@st.cache_data(ttl=3600)
def get_stock_history(stock_id="2301"):
    # 取得當前年月
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={stock_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # 重點修正：加入 verify=False 跳過 SSL 驗證
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        data = response.json()
        
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 清理數值中的逗號，否則無法轉成數字
            for col in ['收盤價', '開盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].str.replace(',', '')
            return df
        else:
            st.error(f"證交所回傳訊息: {data.get('stat')}")
            return None
    except Exception as e:
        st.error(f"抓取失敗: {e}")
        return None

# 執行抓取
df = get_stock_history("2301")

if df is not None:
    # 數據轉換
    df['收盤價'] = df['收盤價'].astype(float)
    
    # 指標顯示
    latest = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新收盤價", f"{latest['收盤價']} 元")
    col2.metric("漲跌價差", latest['漲跌價差'])
    col3.metric("最高價", latest['最高價'])
    col4.metric("最低價", latest['最低價'])

    # 畫圖
    st.subheader("📊 本月股價走勢圖")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', name='收盤價'))
    st.plotly_chart(fig, use_container_width=True)

    # 表格
    st.subheader("📋 每日成交明細")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("⚠️ 目前連線受阻或非交易時段，請稍後再試。")

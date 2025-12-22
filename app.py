import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="2301 股價監控", layout="wide")

st.title("📈 2301 光寶科 - 本月每日成交報表")

@st.cache_data(ttl=3600)
def get_stock_history(stock_id="2301"):
    # 取得當前年月 (格式: 20240501)
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={stock_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data['stat'] == 'OK':
            # 建立 DataFrame
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 整理欄位：日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
            return df
        else:
            st.error(f"證交所回傳錯誤: {data['stat']}")
            return None
    except Exception as e:
        st.error(f"抓取失敗: {e}")
        return None

# 執行抓取
df = get_stock_history("2301")

if df is not None:
    # 數據清理：將收盤價轉為數字以利畫圖
    df['收盤價'] = df['收盤價'].astype(float)
    
    # 1. 顯示今日最新股價資訊
    latest = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新收盤價", f"{latest['收盤價']} 元")
    col2.metric("漲跌價差", latest['漲跌價差'])
    col3.metric("最高價", latest['最高價'])
    col4.metric("最低價", latest['最低價'])

    # 2. 畫出走勢圖
    st.subheader("📊 本月收盤走勢")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', name='收盤價', line=dict(color='#1f77b4')))
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # 3. 顯示原始報表
    st.subheader("📋 每日成交明細")
    st.dataframe(df, use_container_width=True)

    # 4. 下載功能
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載本月報表 (CSV)", csv, "2301_history.csv", "text/csv")

else:
    st.warning("目前無法取得證交所資料，請稍後再試。")


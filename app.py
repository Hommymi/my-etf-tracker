import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3

# 禁用 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 網頁基本設定
st.set_page_config(page_title="2317 鴻海股價監控", page_icon="🍎", layout="wide")

st.title("📈 2317 鴻海 - 本月每日成交報表")

@st.cache_data(ttl=3600)
def get_stock_history(stock_id="2317"):
    # 取得當前年月 (格式: 20240501)
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={stock_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # verify=False 解決 SSLCertVerificationError
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        data = response.json()
        
        if data.get('stat') == 'OK':
            # 建立 DataFrame
            df = pd.DataFrame(data['data'], columns=data['fields'])
            
            # 資料清理：移除逗號並轉為數值
            for col in ['收盤價', '開盤價', '最高價', '最低價', '漲跌價差', '成交股數']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                # 如果是空值或特殊符號轉為 0
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            st.error(f"證交所訊息: {data.get('stat')}")
            return None
    except Exception as e:
        st.error(f"抓取失敗: {e}")
        return None

# 執行抓取
df = get_stock_history("2317")

if df is not None:
    # 取得最新一筆資料
    latest = df.iloc[-1]
    
    # 1. 頂部儀表板
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新收盤價", f"{latest['收盤價']} 元")
    
    # 處理漲跌符號顯示
    change = latest['漲跌價差']
    col2.metric("今日漲跌", f"{change} 元")
    
    col3.metric("本月最高", f"{df['最高價'].max()} 元")
    col4.metric("本月最低", f"{df['最低價'].min()} 元")

    # 2. 畫出股價走勢圖
    st.subheader("📊 本月收盤走勢圖")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['日期'], 
        y=df['收盤價'], 
        mode='lines+markers', 
        name='收盤價',
        line=dict(color='#E61615', width=3), # 鴻海紅
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        hovermode="x unified",
        xaxis_title="日期",
        yaxis_title="股價 (元)",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. 顯示詳細報表
    st.subheader("📋 每日成交明細")
    # 格式化表格，讓閱讀更清楚
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

    # 4. 下載功能
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載 2317 本月成交資料",
        data=csv,
        file_name=f"2317_HoneHai_{datetime.now().strftime('%Y%m')}.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ 暫時無法取得 2317 股價資料，請檢查網路或稍後再試。")

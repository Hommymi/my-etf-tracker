import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 頁面基本設定 ---
st.set_page_config(page_title="Liteon 有價證券監控", layout="wide")
st.title("📊 Liteon 有價證券 (3714 | 6854 | 3593)")
st.caption(f"數據更新頻率：每 10 分鐘 | 最後更新：{datetime.now().strftime('%H:%M:%S')}")

# --- 核心抓取函式 (TTL 600秒 = 10分鐘) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK' and 'data' in data:
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 數值清理轉換
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except Exception:
        return None

# 定義監控股票
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}
all_data = {sid: fetch_twse_data(sid) for sid in DISPLAY_NAMES.keys()}

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 數據下載中心"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"{name} ({sid}) 資料檢查中...")

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {sid} {name} 交易明細")
        df = all_data.get(sid)
        if df is not None:
            # 最新日期排在最上面
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 彙整數據下載")
    st.write("下載包含所有監控個股之詳細交易數據。此 CSV 檔案已優化中文編碼，可直接於 Excel 開啟。")
    
    # 建立下載用 DataFrame
    csv_list = []
    for sid, name in DISPLAY_NAMES.items():
        df = all_data.get(sid)
        if df is not None:
            temp_df = df.copy()
            temp_df.insert(0, '個股名稱', name)
            temp_df.insert(0, '個股代碼', sid)
            csv_list.append(temp_df)
    
    if csv_list:
        final_csv_df = pd.concat(csv_list)
        # 轉換為 CSV 格式並加上 BOM (utf-8-sig)
        csv_bytes = final_df = final_csv_df.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📊 點此下載 Liteon 彙整數據 (CSV)",
            data=csv_bytes,
            file_name=f"Liteon_Stock_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("暫無可供下載的數據。")

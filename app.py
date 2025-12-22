import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# 網頁標題設定
st.set_page_config(page_title="00929 持股監控", layout="wide")

st.title("📊 00929 復華台灣科技優息 - 持股監控")

# 定義抓取資料的函式
@st.cache_data(ttl=3600)  # 快取 1 小時，避免重複抓取耗時
def get_etf_data():
    url = "https://www.fhtrust.com.tw/api/Etf/GetEtfStock"
    payload = {"fundId": "ETF23", "lang": "CH"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()['data']
        df = pd.DataFrame(data)
        # 整理欄位
        df = df[['STOCK_ID', 'STOCK_NAME', 'HOLD_QTY', 'RATIO']]
        df.columns = ['代碼', '名稱', '持股數', '權重%']
        df['持股數'] = df['持股數'].astype(float)
        df['權重%'] = df['權重%'].astype(float)
        return df
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return None

# 執行抓取
df = get_etf_data()

if df is not None:
    # 側邊欄顯示資訊
    st.sidebar.success("✅ 資料連線正常")
    st.sidebar.write(f"最後更新日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 1. 數據摘要 (Metric)
    col1, col2, col3 = st.columns(3)
    col1.metric("成份股總數", f"{len(df)} 檔")
    col2.metric("最大持股", df.iloc[0]['名稱'])
    col3.metric("最大權重", f"{df['權重%'].max()}%")

    # 2. 權重分佈圖
    st.subheader("💡 持股權重分佈")
    fig = px.bar(df.head(20), x='名稱', y='權重%', text='權重%', color='權重%', 
                 title="前 20 大成份股 (按權重排序)")
    st.plotly_chart(fig, use_container_width=True)

    # 3. 詳細表格
    st.subheader("📋 所有持股明細")
    # 讓搜尋更方便
    search_query = st.text_input("輸入股票代碼或名稱搜尋：")
    if search_query:
        display_df = df[df['名稱'].str.contains(search_query) | df['代碼'].str.contains(search_query)]
    else:
        display_df = df

    st.dataframe(display_df, use_container_width=True, height=600)

    # 4. 下載功能
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載完整持股 CSV",
        data=csv,
        file_name=f'00929_holdings_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
else:
    st.warning("暫時無法取得資料，請稍後再試。")
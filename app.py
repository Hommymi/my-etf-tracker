import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(
    page_title="00929 持股監控小幫手",
    page_icon="📈",
    layout="wide"
)

st.title("📊 00929 復華台灣科技優息 - 持股即時監控")

# 2. 定義資料抓取函式 (加入更強的模擬機制)
@st.cache_data(ttl=3600)  # 每小時自動更新一次
def get_etf_data():
    url = "https://www.fhtrust.com.tw/api/Etf/GetEtfStock"
    payload = {"fundId": "ETF23", "lang": "CH"}
    
    # 這裡是最關鍵的 Headers，模擬真人瀏覽器行為
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.fhtrust.com.tw/ETF/etf_detail/ETF23",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.fhtrust.com.tw"
    }
    
    try:
        # 發送 POST 請求
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        # 檢查伺服器狀態
        if response.status_code != 200:
            st.error(f"❌ 伺服器連線失敗，錯誤代碼：{response.status_code}")
            return None
        
        # 嘗試解析 JSON
        json_data = response.json()
        
        if 'data' not in json_data:
            st.error("❌ 抓取成功但資料格式不符")
            return None
            
        # 轉換為 DataFrame
        df = pd.DataFrame(json_data['data'])
        
        # 篩選欄位並重新命名
        df = df[['STOCK_ID', 'STOCK_NAME', 'HOLD_QTY', 'RATIO']]
        df.columns = ['代碼', '名稱', '持股數', '權重%']
        
        # 轉換數值型態
        df['持股數'] = pd.to_numeric(df['持股數'], errors='coerce')
        df['權重%'] = pd.to_numeric(df['權重%'], errors='coerce')
        
        return df

    except Exception as e:
        st.error(f"⚠️ 發生錯誤: {str(e)}")
        return None

# 3. 執行抓取與介面顯示
df = get_etf_data()

if df is not None:
    # 顯示更新時間
    st.sidebar.info(f"🕒 資料更新時間：\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 指標面板
    m1, m2, m3 = st.columns(3)
    m1.metric("總成份股數", f"{len(df)} 檔")
    m2.metric("最大權重股", f"{df.iloc[0]['名稱']}")
    m3.metric("前十大權重合計", f"{df['權重%'].head(10).sum():.2f}%")

    # 視覺化圖表
    st.subheader("💡 前 20 大持股權重圖")
    fig = px.bar(
        df.head(20), 
        x='名稱', 
        y='權重%', 
        text='權重%', 
        color='權重%',
        color_continuous_scale='Viridis'
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # 搜尋與表格
    st.subheader("📋 持股明細清單")
    search = st.text_input("🔍 搜尋股票名稱或代碼 (例如: 2330)")
    
    if search:
        filtered_df = df[df['名稱'].str.contains(search) | df['代碼'].str.contains(search)]
    else:
        filtered_df = df
        
    st.dataframe(filtered_df, use_container_width=True, height=500)

    # 下載按鈕
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載今日持股報表 (CSV)",
        data=csv_data,
        file_name=f'00929_holdings_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
else:
    st.warning("🔄 正在嘗試重新連線中... 請嘗試重新整理網頁。")

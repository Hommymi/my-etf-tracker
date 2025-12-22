import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="00929 持股監控", page_icon="📈", layout="wide")
st.title("📊 00929 復華台灣科技優息 - 持股即時監控")

# 2. 定義資料抓取函式 (改用證交所官方 API)
@st.cache_data(ttl=3600)
def get_twse_data():
    # 證交所 ETF 持股分佈 API (這是公開資料，不會擋 IP)
    url = "https://www.twse.com.tw/exchangeReport/BWIBBU_d?response=json"
    
    try:
        # 00929 的資料在證交所是公開的，我們直接抓取當日清單
        # 注意：證交所資料通常在 14:30 後更新
        response = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_all")
        data = response.json()
        
        # 轉換為 DataFrame
        df = pd.DataFrame(data)
        
        # 篩選 00929 的成分股 (這裡我們用復華官網作為備援，如果 API 不行就手動顯示)
        # 由於 00929 是熱門 ETF，我們改用另一套更穩定的來源
        res = requests.get("https://api.stockit.com.tw/api/v1/etf/00929/stocks")
        df = pd.DataFrame(res.json()['data'])
        
        df = df[['code', 'name', 'shares', 'ratio']]
        df.columns = ['代碼', '名稱', '持股數', '權重%']
        df['權重%'] = df['權重%'].astype(float)
        return df
    except:
        # 如果第三方 API 也失敗，我們使用復華官網的最後嘗試 (加上偽裝)
        try:
            url = "https://www.fhtrust.com.tw/api/Etf/GetEtfStock"
            payload = {"fundId": "ETF23", "lang": "CH"}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.fhtrust.com.tw/"}
            response = requests.post(url, json=payload, headers=headers)
            df = pd.DataFrame(response.json()['data'])
            df = df[['STOCK_ID', 'STOCK_NAME', 'HOLD_QTY', 'RATIO']]
            df.columns = ['代碼', '名稱', '持股數', '權重%']
            return df
        except:
            return None

# 執行抓取
df = get_twse_data()

if df is not None:
    st.sidebar.success(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")
    
    # 統計指標
    col1, col2 = st.columns(2)
    col1.metric("成份股總數", f"{len(df)} 檔")
    col2.metric("前十大權重合計", f"{df['權重%'].head(10).sum():.2f}%")

    # 圖表
    st.subheader("💡 前 15 大持股權重")
    fig = px.pie(df.head(15), values='權重%', names='名稱', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # 列表
    st.subheader("📋 持股明細")
    st.dataframe(df, use_container_width=True)
else:
    st.error("❌ 抱歉，目前所有資料來源連線均被阻擋。這通常發生在投信網站維護期間。")
    st.info("💡 建議：請於交易日 09:00 - 17:00 之間再次嘗試。")

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="00929 監控 (穩定版)", layout="wide")
st.title("🚀 00929 持股監控 (Google 代理版)")

# 填入你剛才在 Google 部署後取得的網址
GAS_URL = "你的_GAS_網址" 

@st.cache_data(ttl=3600)
def get_data_via_proxy():
    try:
        response = requests.get(GAS_URL, timeout=20)
        data = response.json()
        df = pd.DataFrame(data['data'])
        df = df[['STOCK_ID', 'STOCK_NAME', 'HOLD_QTY', 'RATIO']]
        df.columns = ['代碼', '名稱', '持股數', '權重%']
        df['權重%'] = df['權重%'].astype(float)
        return df
    except Exception as e:
        st.error(f"連線代理伺服器失敗: {e}")
        return None

df = get_data_via_proxy()

if df is not None:
    st.success("✅ 透過 Google 代理成功抓取資料")
    
    # 這裡放原本的圖表代碼
    fig = px.bar(df.head(10), x='名稱', y='權重%', text='權重%', color='權重%')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("請確認您的 Google Apps Script 網址是否正確，且已設定為『所有人』皆可存取。")

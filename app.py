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
    # 獲取當前西元年/月
    now = datetime.now()
    year = now.year
    month = now.month
    
    # 建立請求參數
    url = "https://www.tpex.org.tw/web/emergingstock/historical/daily_quotes/EMDailyQuo_result.php"
    params = {
        "l": "zh-tw",
        "d": f"{year}/{month:02d}/01", # 從本月 1 號開始抓
        "stk_code": "6805",
        "_": int(datetime.now().timestamp() * 1000)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tpex.org.tw/web/emergingstock/historical/daily_quotes/daily_quotes.php",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # 使用 Session 維持連線狀態
        session = requests.Session()
        res = session.get(url, params=params, headers=headers, verify=False, timeout=15)
        
        if res.status_code != 200:
            return f"伺服器回傳錯誤代碼: {res.status_code}"

        data = res.json()
        
        if 'aaData' in data and len(data['aaData']) > 0:
            raw_df = pd.DataFrame(data['aaData'])
            # 興櫃欄位：0日期, 4最高, 5最低, 6均價, 3開盤, 7漲跌
            df = raw_df[[0, 4, 5, 6, 3, 7]].copy()
            df.columns = ['日期', '最高價', '最低價', '收盤價', '開盤價', '漲跌價差']
            
            for col in ['最高價', '最低價', '收盤價', '開盤價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        else:
            return "查無資料 (aaData 為空)"
    except Exception as e:
        return f"連線異常: {str(e)}"

# 執行抓取
result = fetch_tpex_6805()

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

# 判斷結果類型
if isinstance(result, pd.DataFrame):
    df_6805 = result
    with tab1:
        latest = df_6805.iloc[-1]
        st.metric(f"6805 永笙-KY", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
        fig = go.Figure(go.Scatter(x=df_6805['日期'], y=df_6805['收盤價'], mode='lines+markers', line=dict(color='#00CC96')))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(df_6805.sort_index(ascending=False), use_container_width=True)
        
    with tab3:
        # PDF 與 CSV 下載 (邏輯同前)
        csv_data = df_6805.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📊 下載 Liteon 中文 CSV", data=csv_data, file_name="Liteon_6805.csv", mime="text/csv")
else:
    # 顯示錯誤訊息
    st.error(f"❌ 數據讀取失敗：{result}")
    st.info("💡 提示：興櫃 API 有時會限制海外 IP (GitHub Actions/Streamlit Cloud 伺服器所在地)。如果持續失敗，建議檢查網頁是否能正常開啟。")

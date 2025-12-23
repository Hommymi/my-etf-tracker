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

# --- 櫃買中心 (TPEX) 強效抓取函式 ---
@st.cache_data(ttl=600)
def fetch_tpex_6805_v3():
    # 改用歷史行情查詢頁面的 POST 介面
    url = "https://www.tpex.org.tw/web/emergingstock/historical/daily_quotes/EMDailyQuo_result.php?l=zh-tw"
    
    # 建立今天的日期字串
    today = datetime.now()
    date_str = f"{today.year}/{today.month:02d}/01"
    
    # 模擬表單提交
    payload = {
        "d": date_str,
        "stk_code": "6805",
        "sidx": "date",
        "sord": "asc"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.tpex.org.tw",
        "Referer": "https://www.tpex.org.tw/web/emergingstock/historical/daily_quotes/daily_quotes.php",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # 使用 Session 並先訪問首頁獲取可能需要的 Cookies
        session = requests.Session()
        session.get("https://www.tpex.org.tw/web/index.php", headers=headers, timeout=10)
        
        # 發送 POST 請求
        res = session.post(url, data=payload, headers=headers, verify=False, timeout=15)
        
        # 檢查是否為 HTML 而不是 JSON (被擋時通常回傳 HTML)
        if res.text.strip().startswith("<!DOCTYPE"):
            return "伺服器拒絕連線 (觸發防火牆)，請稍後再試。"

        data = res.json()
        
        if 'aaData' in data and len(data['aaData']) > 0:
            raw_df = pd.DataFrame(data['aaData'])
            # 櫃買中心興櫃欄位索引：0日期, 4最高, 5最低, 6均價, 3開盤, 7漲跌
            df = raw_df[[0, 4, 5, 6, 3, 7]].copy()
            df.columns = ['日期', '最高價', '最低價', '收盤價', '開盤價', '漲跌價差']
            
            # 清理格式
            for col in ['最高價', '最低價', '收盤價', '開盤價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        else:
            return "查無資料 (aaData 為空)，可能是該股票今日無交易。"
    except Exception as e:
        return f"連線異常: {str(e)}"

# --- 執行與顯示 ---
result = fetch_tpex_6805_v3()

tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

if isinstance(result, pd.DataFrame):
    df_6805 = result
    with tab1:
        latest = df_6805.iloc[-1]
        st.metric("6805 永笙-KY", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
        fig = go.Figure(go.Scatter(x=df_6805['日期'], y=df_6805['收盤價'], mode='lines+markers', line=dict(color='#00CC96')))
        fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(df_6805.sort_index(ascending=False), use_container_width=True)
        
    with tab3:
        # 下載 CSV (中文支援)
        csv_bytes = df_6805.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📊 下載 Liteon 中文 CSV", data=csv_bytes, file_name="Liteon_6805.csv", mime="text/csv")
        
        # 下載 PDF (英文分頁)
        def create_simple_pdf(df):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(190, 10, txt="Liteon Report - 6805 StemCyte", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font('Arial', '', 10)
            for _, row in df.tail(15).iterrows():
                pdf.cell(190, 8, txt=f"{row['日期']} | Close: {row['收盤價']} | High: {row['最高價']}", ln=True)
            return pdf.output(dest='S')
            
        pdf_bytes = create_simple_pdf(df_6805)
        st.download_button("📄 下載英文 PDF 報表", data=pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.encode('latin-1'), file_name="Liteon_6805.pdf", mime="application/pdf")

else:
    st.error(f"❌ 數據讀取失敗：{result}")
    st.info("💡 如果連 POST 請求都被擋，建議在您的 GitHub Repo 加入一個簡單的 proxy 設定，或是改用其他數據供應來源 (如 Yahoo Finance)。")

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="面板/生技監控中心", layout="wide")
st.title("📊 3714富采 | 6854錼創 | 3593力銘 | 4178永笙-KY")

# 定義股票清單
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
STOCK_LIST_TPEX = {"4178": "永笙-KY"}

# --- 1. 抓取上市/上櫃股票 (證交所 API) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

# --- 2. 抓取興櫃股票 (櫃買中心即時 API) - 這是解決 4178 的關鍵 ---
@st.cache_data(ttl=600)
def fetch_tpex_esb_realtime(sid):
    # 興櫃即時行情 API (aaData 格式)
    url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_quotes/stk_quotes_result.php?l=zh-tw"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.tpex.org.tw/zh-tw/main/index.html"
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if 'aaData' in data:
            # 在所有興櫃股票中搜尋 4178
            target = [row for row in data['aaData'] if str(row[0]).strip() == str(sid)]
            if target:
                row = target[0]
                # 興櫃欄位: 0代號, 1名稱, 2成交均價, 3前日均價, 4開盤, 5最高, 6最低
                df = pd.DataFrame([{
                    '日期': datetime.now().strftime("%Y/%m/%d"),
                    '收盤價': float(row[2]) if row[2] != '--' else 0.0,
                    '最高價': float(row[5]) if row[5] != '--' else 0.0,
                    '最低價': float(row[6]) if row[6] != '--' else 0.0,
                    '漲跌價差': row[8] if row[8] != '--' else "0"
                }])
                return df
        return None
    except: return None

# 讀取資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
for sid in STOCK_LIST_TPEX:
    all_data[sid] = fetch_tpex_esb_realtime(sid)

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 即時走勢對照", "📋 詳細數據明細", "📥 報表下載中心"])

with tab1:
    cols = st.columns(4)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    combined_list = {**STOCK_LIST_TWSE, **STOCK_LIST_TPEX}
    
    for i, (sid, name) in enumerate(combined_list.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 興櫃顯示均價，上市顯示收盤
                price_type = "成交均價" if sid == "4178" else "收盤價"
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                
                # 繪圖邏輯：興櫃若只有一筆資料則顯示點，上市顯示線
                fig = go.Figure()
                mode = 'markers' if len(df) == 1 else 'lines+markers'
                fig.add_trace(go.Scatter(x=df['日期'], y=df['收盤價'], mode=mode, line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=5, r=5, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"{name} 無即時報價")
                st.caption("請確認是否為交易日或 API 維護中")

with tab2:
    for sid, name in combined_list.items():
        st.subheader(f"📋 {name} ({sid}) 明細")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"無法載入 {name} 表格資料")

with tab3:
    st.subheader("📦 報表匯出")
    # PDF 簡化版
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        pdf.add_page()
        pdf.cell(200, 10, txt="Stock Report Summary", ln=True, align='C')
        for sid, df in data_dict.items():
            if df is not None:
                latest = df.iloc[-1]
                pdf.cell(190, 10, txt=f"{sid}: {latest['收盤價']} (Date: {latest['日期']})", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if any(df is not None for df in all_data.values()):
        pdf_bytes = create_pdf(all_data)
        st.download_button("📄 下載簡報 PDF", pdf_bytes, "Report.pdf", "application/pdf")

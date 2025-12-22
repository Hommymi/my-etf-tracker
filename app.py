import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="個股整合監控中心", layout="wide")
st.title("📊 3714富采 | 6854錼創 | 3593力銘 | 4178永笙-KY")

# 定義股票清單
STOCK_LIST_TWSE = {"3714": "富采", "6854": "錼創科技", "3593": "力銘"}
STOCK_LIST_TPEX = {"4178": "永笙-KY"}

# --- 抓取上市股票資料 (證交所 API) ---
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

# --- 抓取興櫃股票歷史資料 (櫃買中心 API) ---
def fetch_tpex_esb_history(sid):
    # 興櫃個股日成交資訊 (抓取本月)
    datestr = datetime.now().strftime("%Y/%m")
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_quot_no1430_result.php?l=zh-tw&d={datestr}&stk_code={sid}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.tpex.org.tw/"
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data and 'aaData' in data and len(data['aaData']) > 0:
            # 興櫃欄位: 0日期, 1成交股數, 2成交金額, 3成交筆數, 4最高, 5最低, 6成交均價(當收盤看), 7漲跌
            df = pd.DataFrame(data['aaData'], columns=['日期', '成交股數', '成交金額', '成交筆數', '最高價', '最低價', '收盤價', '漲跌價差'])
            # 興櫃資料通常是均價代表成交行情
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except: return None

# 讀取資料
all_data = {}
for sid in STOCK_LIST_TWSE:
    all_data[sid] = fetch_twse_data(sid)
for sid in STOCK_LIST_TPEX:
    all_data[sid] = fetch_tpex_esb_history(sid)

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
                st.metric(f"{name} ({sid})", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], name=sid, line=dict(color=colors[i], width=3)))
                fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{name} 讀取失敗")
                st.caption("興櫃資料可能於盤後更新")

with tab2:
    for sid, name in combined_list.items():
        st.subheader(f"📋 {name} ({sid}) 明細")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning(f"目前無法取得 {name} 的表格資料。")
        st.divider()

with tab3:
    st.subheader("📦 報表匯出")
    # PDF 產生邏輯 (簡化顯示)
    def create_pdf(data_dict):
        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        for sid, df in data_dict.items():
            if df is not None:
                pdf.add_page()
                pdf.cell(200, 10, txt=f"Stock Report: {sid}", ln=True, align='C')
                pdf.ln(10)
                # 簡單印出最後 10 筆數據
                for i in range(min(len(df), 10)):
                    row = df.iloc[i]
                    pdf.cell(190, 10, txt=f"{row['日期']} | Close: {row['收盤價']} | Change: {row['漲跌價差']}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if any(df is not None for df in all_data.values()):
        pdf_bytes = create_pdf(all_data)
        st.download_button("📄 下載 4 檔股票聯合 PDF 報表", pdf_bytes, "Stock_Report.pdf", "application/pdf", use_container_width=True)
    else:
        st.error("暫無資料可供下載")

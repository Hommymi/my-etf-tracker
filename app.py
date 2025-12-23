import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="面板/光電股監控中心", layout="wide")
st.title("📊 3714 富采 | 6854 錼創 | 3593 力銘")
st.caption(f"自動更新頻率：每 10 分鐘一次 | 目前系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 抓取資料 (設定 10 分鐘請求一次) ---
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
    except:
        return None

# 股票清單
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}
all_data = {sid: fetch_twse_data(sid) for sid in DISPLAY_NAMES.keys()}

tab1, tab2, tab3 = st.tabs(["📈 即時走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {name} ({sid})")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)

with tab3:
    st.subheader("📦 報表匯出中心")
    
    def create_pdf(data_dict):
        # 初始化 PDF
        pdf = FPDF()
        pdf.add_page()
        
        # --- 重要：處理中文 ---
        # 如果你沒有上傳字型，這裡會崩潰。
        # 為了保險，我們改用 CSV 下載或是將 PDF 標題改為日期
        report_date = datetime.now().strftime("%Y-%m-%d")
        
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, txt=f"Stock Report - {report_date}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=12)
        for sid, df in data_dict.items():
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 這裡目前只能印出 ID，因為中文需要額外字型檔
                line = f"Ticker: {sid} | Price: {latest['收盤價']} | Change: {latest['漲跌價差']} | Date: {report_date}"
                pdf.cell(190, 10, txt=line, ln=True)
        
        return pdf.output(dest='S')

    if any(df is not None for df in all_data.values()):
        # 1. 正常的 PDF 下載 (含日期)
        pdf_out = create_pdf(all_data)
        st.download_button(
            label=f"📄 下載 PDF 報表 ({datetime.now().strftime('%Y-%m-%d')})",
            data=bytes(pdf_out) if isinstance(pdf_out, bytes) else pdf_out.encode('latin-1'),
            file_name=f"Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # 2. 額外提供 CSV 下載 (這可以完美支援中文)
        st.write("---")
        st.write("💡 若需完整中文字內容，建議下載 Excel/CSV 版本：")
        csv_list = []
        for sid, df in all_data.items():
            if df is not None:
                temp_df = df.tail(1).copy()
                temp_df['股票'] = DISPLAY_NAMES[sid]
                csv_list.append(temp_df)
        
        if csv_list:
            final_csv_df = pd.concat(csv_list)
            st.download_button(
                label="📊 下載中文完整數據 (Excel/CSV)",
                data=final_csv_df.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"個股報表_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

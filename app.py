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
st.title("📊 面板/光電三傑監控 (3714 | 6854 | 3593)")

# --- 抓取資料 (10分鐘更新一次) ---
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
            # 數值清理
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

# 定義股票清單
STOCK_MAP = {"3714": "Ennostar", "6854": "PlayNitride", "3593": "Leading"}
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}

all_data = {sid: fetch_twse_data(sid) for sid in STOCK_MAP.keys()}

# --- 修改頁籤名稱 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                # 加上股票代碼
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {sid} {name} (詳細數據)")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 專業 PDF 報表產出")
    st.write("點擊按鈕下載包含歷史詳細數據的 PDF (每支股票獨立一頁)。")
    
    def create_advanced_pdf(data_dict):
        pdf = FPDF()
        report_date = datetime.now().strftime("%Y-%m-%d")
        
        for sid, df in data_dict.items():
            if df is not None and not df.empty:
                # 每一支股票開新頁
                pdf.add_page()
                
                # 標題區
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, txt=f"Stock Detail Report - {sid}", ln=True, align='C')
                pdf.set_font("Arial", '', 10)
                pdf.cell(190, 10, txt=f"Report Date: {report_date} | Company: {STOCK_MAP[sid]}", ln=True, align='C')
                pdf.ln(10)
                
                # 繪製表格表頭 (PDF 表格)
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(40, 8, "Date", 1, 0, 'C', True)
                pdf.cell(35, 8, "High", 1, 0, 'C', True)
                pdf.cell(35, 8, "Low", 1, 0, 'C', True)
                pdf.cell(40, 8, "Close", 1, 0, 'C', True)
                pdf.cell(40, 8, "Change", 1, 1, 'C', True)
                
                # 填入數據內容 (只取最新 15 筆，避免單頁過長)
                pdf.set_font("Arial", '', 9)
                recent_df = df.tail(15).iloc[::-1] # 取最新15筆並反轉
                for index, row in recent_df.iterrows():
                    pdf.cell(40, 7, str(row['日期']), 1, 0, 'C')
                    pdf.cell(35, 7, str(row['最高價']), 1, 0, 'C')
                    pdf.cell(35, 7, str(row['最低價']), 1, 0, 'C')
                    pdf.cell(40, 7, str(row['收盤價']), 1, 0, 'C')
                    pdf.cell(40, 7, str(row['漲跌價差']), 1, 1, 'C')
                
                pdf.ln(10)
                pdf.set_font("Arial", 'I', 8)
                pdf.cell(190, 10, txt="* This report is for informational purposes only.", ln=True, align='L')
                
        return pdf.output(dest='S')

    if any(df is not None for df in all_data.values()):
        try:
            raw_pdf = create_advanced_pdf(all_data)
            pdf_bytes = raw_pdf if isinstance(raw_pdf, bytes) else raw_pdf.encode('latin-1')
            
            st.download_button(
                label="📄 下載詳細數據 PDF (分頁版)",
                data=pdf_bytes,
                file_name=f"Stock_Detailed_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF 產製錯誤: {e}")

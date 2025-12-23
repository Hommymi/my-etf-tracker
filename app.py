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
st.caption(f"數據更新頻率：每 10 分鐘 | 最後更新：{datetime.now().strftime('%H:%M:%S')}")

# --- 櫃買中心 (TPEX) 抓取函式 ---
@st.cache_data(ttl=600)
def fetch_tpex_data(sid):
    # 櫃買中心興櫃/戰略新板歷史成交 API
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/otc_quotes_no1430_result.php?l=zh-tw&stk_code={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('aaData'):
            # 欄位對照：日期, 成交股數, 成交金額, 開盤, 最高, 最低, 收盤, 漲跌, 成交筆數
            df = pd.DataFrame(data['aaData'])
            # 根據櫃買中心格式選取主要欄位
            df = df[[0, 4, 5, 6, 3, 7]] 
            df.columns = ['日期', '最高價', '最低價', '收盤價', '開盤價', '漲跌價差']
            
            # 數值清理
            for col in ['最高價', '最低價', '收盤價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except:
        return None

# 定義監控股票 (改為永笙-KY)
ENGLISH_NAMES = {"6805": "StemCyte"}
DISPLAY_NAMES = {"6805": "永笙-KY"}

all_data = {sid: fetch_tpex_data(sid) for sid in DISPLAY_NAMES.keys()}

# --- PDF 產生邏輯 (純英文避免編碼錯誤) ---
def create_pdf_report(data_dict):
    pdf = FPDF()
    report_date = datetime.now().strftime("%Y-%m-%d")

    for sid, df in data_dict.items():
        if df is not None and not df.empty:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            en_name = ENGLISH_NAMES.get(sid, "Stock")
            pdf.cell(190, 10, txt=f"Stock Report - {sid} ({en_name})", ln=True, align='C')
            pdf.set_font('Arial', '', 10)
            pdf.cell(190, 10, txt=f"Date: {report_date}", ln=True, align='C')
            pdf.ln(5)
            
            # 表格標頭
            pdf.set_fill_color(220, 230, 241)
            header = ["Date", "High", "Low", "Close", "Diff"]
            widths = [40, 35, 35, 40, 40]
            pdf.set_font('Arial', 'B', 10)
            for i, h in enumerate(header):
                pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
            pdf.ln()
            
            # 數據
            pdf.set_font('Arial', '', 9)
            recent_df = df.tail(15).iloc[::-1]
            for _, row in recent_df.iterrows():
                pdf.cell(40, 7, str(row.get('日期', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最高價', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最低價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('收盤價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('漲跌價差', '--')), 1, 1, 'C')
    return pdf.output(dest='S')

# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載"])

with tab1:
    for sid, name in DISPLAY_NAMES.items():
        df = all_data.get(sid)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
            fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color='#1f77b4', width=3)))
            fig.update_layout(title=f"{name} 走勢圖", height=350)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"{sid} {name}")
        if all_data.get(sid) is not None:
            st.dataframe(all_data[sid].sort_index(ascending=False), use_container_width=True)

with tab3:
    st.subheader("📦 報表下載")
    if any(df is not None for df in all_data.values()):
        # PDF 下載
        pdf_out = create_pdf_report(all_data)
        st.download_button(
            label="📄 下載英文 PDF (永笙-KY 分頁報表)",
            data=pdf_out if isinstance(pdf_out, bytes) else pdf_out.encode('latin-1'),
            file_name=f"Liteon_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.divider()
        # CSV 下載
        csv_list = []
        for sid, name in DISPLAY_NAMES.items():
            df = all_data.get(sid)
            if df is not None:
                temp = df.copy(); temp.insert(0, '名稱', name); temp.insert(0, '代碼', sid)
                csv_list.append(temp)
        if csv_list:
            csv_bytes = pd.concat(csv_list).to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📊 下載中文 CSV (支援 Excel)", data=csv_bytes, 
                               file_name=f"Liteon_Data_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

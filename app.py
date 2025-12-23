import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib3
from fpdf import FPDF # 重新引入 FPDF

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 頁面基本設定 ---
st.set_page_config(page_title="Liteon 有價證券監控", layout="wide")
st.title("📊 Liteon 有價證券 (3714 | 6854 | 3593)")
st.caption(f"數據更新頻率：每 10 分鐘 | 最後更新：{datetime.now().strftime('%H:%M:%S')}")

# --- 核心抓取函式 (TTL 600秒 = 10分鐘) ---
@st.cache_data(ttl=600)
def fetch_twse_data(sid):
    datestr = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datestr}&stockNo={sid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK' and 'data' in data:
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 數值清理轉換
            for col in ['收盤價', '最高價', '最低價', '漲跌價差']:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('+', '').str.replace('X', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return None
    except Exception:
        return None

# 定義監控股票
DISPLAY_NAMES = {"3714": "富采", "6854": "錼創科技-KY", "3593": "力銘"}
all_data = {sid: fetch_twse_data(sid) for sid in DISPLAY_NAMES.keys()}

# --- PDF 產生邏輯 (純英文版，穩定輸出) ---
def create_pdf_report(data_dict):
    pdf = FPDF()
    report_date = datetime.now().strftime("%Y-%m-%d")

    for sid, df in data_dict.items():
        if df is not None and not df.empty:
            pdf.add_page()
            
            # 頁面標題 (英文)
            pdf.set_font('Arial', 'B', 16)
            title = f"Stock Report - {sid} ({DISPLAY_NAMES.get(sid, '')})"
            pdf.cell(190, 10, txt=title, ln=True, align='C')
            
            pdf.set_font('Arial', '', 10)
            pdf.cell(190, 10, txt=f"Report Date: {report_date}", ln=True, align='C')
            pdf.ln(5)
            
            # 表格標頭 (英文)
            pdf.set_fill_color(220, 230, 241)
            header = ["Date", "High", "Low", "Close", "Change"]
            widths = [40, 35, 35, 40, 40]
            pdf.set_font('Arial', 'B', 10)
            for i, h in enumerate(header):
                pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
            pdf.ln()
            
            # 填入數據 (英文)
            pdf.set_font('Arial', '', 9)
            recent_df = df.tail(20).iloc[::-1] # 最新 20 筆
            for _, row in recent_df.iterrows():
                pdf.cell(40, 7, str(row.get('日期', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最高價', '--')), 1, 0, 'C')
                pdf.cell(35, 7, str(row.get('最低價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('收盤價', '--')), 1, 0, 'C')
                pdf.cell(40, 7, str(row.get('漲跌價差', '--')), 1, 1, 'C')
                
    return pdf.output(dest='S')


# --- 介面佈局 ---
tab1, tab2, tab3 = st.tabs(["📈 當日走勢", "📋 詳細數據", "📥 報表下載中心"])

with tab1:
    cols = st.columns(3)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, (sid, name) in enumerate(DISPLAY_NAMES.items()):
        with cols[i]:
            df = all_data.get(sid)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                st.metric(f"{sid} {name}", f"{latest['收盤價']} 元", f"{latest['漲跌價差']}")
                fig = go.Figure(go.Scatter(x=df['日期'], y=df['收盤價'], mode='lines+markers', line=dict(color=colors[i], width=3)))
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"{name} ({sid}) 資料檢查中...")

with tab2:
    for sid, name in DISPLAY_NAMES.items():
        st.subheader(f"📋 {sid} {name} 交易明細")
        df = all_data.get(sid)
        if df is not None:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        st.divider()

with tab3:
    st.subheader("📦 下載 Liteon 股票數據")
    st.write("您可以選擇下載分頁的 **PDF 報告 (英文版)** 或支援中文的 **CSV 數據 (Excel 開啟)**。")
    
    # --- PDF 下載按鈕 ---
    if any(df is not None for df in all_data.values()):
        try:
            pdf_output = create_pdf_report(all_data)
            pdf_bytes = pdf_output if isinstance(pdf_output, (bytes, bytearray)) else pdf_output.encode('latin-1')
            
            st.download_button(
                label="📄 下載詳細 PDF 報表 (英文版)",
                data=pdf_bytes,
                file_name=f"Liteon_Stock_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF 製作錯誤: {e}")
    else:
        st.warning("目前無數據可產製 PDF。")

    st.markdown("---") # 分隔線
    
    # --- CSV 下載按鈕 ---
    csv_list = []
    for sid, name in DISPLAY_NAMES.items():
        df = all_data.get(sid)
        if df is not None:
            temp_df = df.copy()
            temp_df.insert(0, '個股名稱', name)
            temp_df.insert(0, '個股代碼', sid)
            csv_list.append(temp_df)
    
    if csv_list:
        final_csv_df = pd.concat(csv_list)
        csv_bytes = final_csv_df.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📊 下載 Liteon 彙整數據 (CSV, 支援中文)",
            data=csv_bytes,
            file_name=f"Liteon_Stock_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("目前無數據可下載 CSV。")

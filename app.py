import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import twstock
from datetime import datetime
import base64
from io import BytesIO

st.set_page_config(page_title="台股即時分析工具", layout="centered")
st.title("台股即時分析工具")

st.markdown(
    "輸入台股代碼（例如：**2330** 為台積電），系統將抓取技術指標並評估是否為值得投資的時機。"
)

# RSI 簡介區塊
with st.expander("📘 RSI 是什麼？（點我查看）"):
    st.markdown(
        """
**RSI（相對強弱指數）簡介：**  
RSI 是用來判斷股票是否處於「超買」或「超賣」狀態的技術指標。  

- **RSI < 30**：可能過度賣出，有機會反彈（可觀察是否進場）  
- **RSI > 70**：可能過度買入，有下跌風險（適合考慮賣出）  
- **30 ≤ RSI ≤ 70**：屬於正常波動範圍，建議觀望  
"""
    )

# 我的最愛功能
st.sidebar.header("⭐ 我的最愛")
fav_input = st.sidebar.text_input("輸入股票代碼（如 2330）")
if "fav_list" not in st.session_state:
    st.session_state.fav_list = []

if st.sidebar.button("加入最愛"):
    if fav_input and fav_input not in st.session_state.fav_list:
        st.session_state.fav_list.append(fav_input)

if st.session_state.fav_list:
    st.sidebar.markdown("### 快速查詢")
    for fav_code in st.session_state.fav_list:
        if st.sidebar.button(fav_code):
            st.session_state["selected_fav"] = fav_code

# 日期範圍選擇
st.sidebar.header("📅 選擇資料區間")
period_option = st.sidebar.selectbox(
    "請選擇查詢區間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2
)

# 股票輸入（優先讀取最愛選擇）
ticker_input = st.session_state.get("selected_fav", "") or st.text_input(
    "請輸入台股代碼（例如 2330）"
)

if ticker_input:
    try:
        code = ticker_input.strip()
        ticker_symbol = f"{code}.TW"
        data = yf.download(ticker_symbol, period=period_option, interval="1d")

        if data.empty:
            st.error("查無此代碼，請重新輸入。")
        else:
            stock_info = twstock.codes.get(code)
            stock_name = stock_info.name if stock_info else code
            stock_group = getattr(stock_info, "group", "－不詳－")
            stock_start = getattr(stock_info, "start", "－不詳－")

            st.success(f"{code} - {stock_name}")
            st.caption(f"產業別：{stock_group} | 上市日期：{stock_start}")

            close_prices = data["Close"].astype(float).squeeze()

            # 計算 RSI
            rsi_calc = RSIIndicator(close=close_prices)
            rsi = rsi_calc.rsi()

            # 股價圖表
            st.subheader("📈 股價走勢圖")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=close_prices,
                    mode="lines+markers",
                    name="收盤價",
                    hovertemplate="日期：%{x}<br>股價：%{y}<extra></extra>",
                )
            )
            fig.update_layout(title="股價走勢", xaxis_title="日期", yaxis_title="股價")
            st.plotly_chart(fig, use_container_width=True)

            # 匯出功能
            st.subheader("💾 匯出")
            excel_buffer = BytesIO()
            data.to_excel(excel_buffer, index=True, engine="xlsxwriter")
            st.download_button(
                "匯出 Excel",
                excel_buffer.getvalue(),
                f"{code}_stock_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # 複製分析結果按鈕
            st.subheader("🖱️ 分享分析結果")
            analysis_summary = (
                f"股票代碼：{code}\n股票名稱：{stock_name}\n產業別：{stock_group}\nRSI：{rsi.iloc[-1]:.2f}"
                if not rsi.empty
                else "無法計算 RSI"
            )
            st.code(analysis_summary, language="markdown")
            st.caption("可自行複製貼上分享")

            # 投資評估
            st.subheader("📊 投資評估")
            if not rsi.empty:
                latest_rsi = rsi.iloc[-1]
                if latest_rsi < 30:
                    st.success("RSI 低於 30：可能是超賣區，考慮進場")
                elif latest_rsi > 70:
                    st.warning("RSI 高於 70：可能是超買區，謹慎投資")
                else:
                    st.info("RSI 在正常區間：觀望中")
            else:
                st.error("無法計算有效的 RSI，請檢查資料來源。")

        # 重置選擇狀態，避免連續點擊
        if "selected_fav" in st.session_state:
            del st.session_state["selected_fav"]

    except Exception as e:
        st.error(f"發生錯誤：{str(e)}")

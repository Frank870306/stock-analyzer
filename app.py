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

st.markdown("輸入台股代碼（例如：**2330** 為台積電），系統將抓取技術指標並評估是否為值得投資的時機。")

ticker_input = st.text_input("請輸入台股代碼（例如 2330）")

if ticker_input:
    try:
        code = ticker_input.strip()
        ticker_symbol = f"{code}.TW"
        data = yf.download(ticker_symbol, period="6mo", interval="1d")

        if data.empty:
            st.error("查無此代碼，請重新輸入。")
        else:
            stock_info = twstock.codes.get(code)
            stock_name = stock_info.name if stock_info else code
            stock_group = getattr(stock_info, 'group', '－不詳－')
            stock_start = getattr(stock_info, 'start', '－不詳－')

            st.success(f"{code} - {stock_name}")
            st.caption(f"產業別：{stock_group} | 上市日期：{stock_start}")

            close_prices = data['Close'].astype(float).squeeze()

            # 計算 RSI
            rsi_calc = RSIIndicator(close=close_prices)
            rsi = rsi_calc.rsi()

            # RSI 介紹 - 使用 expander
            with st.expander("📘 點擊查看 RSI 介紹"):
                st.markdown("""
                **RSI（相對強弱指標）** 是一個常用的技術指標，用來評估股票是否過度買進或賣出。其值範圍從 0 到 100，當 RSI 低於 30 時，通常表示股票可能處於過度賣出的區域，反之當 RSI 高於 70 時，則可能表示過度買進。

                - **RSI < 30**：可能是過度賣出，建議進場觀察。
                - **RSI > 70**：可能是過度買進，建議謹慎投資。
                - **30 < RSI < 70**：一般為正常區間，觀望中。

                RSI 幫助投資人識別潛在的買入或賣出時機。
                """)

            # 股價圖表
            st.subheader("📈 股價走勢圖")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=close_prices, mode='lines+markers', name='收盤價', hovertemplate='日期：%{x}<br>股價：%{y}<extra></extra>'))
            fig.update_layout(title='股價走勢', xaxis_title='日期', yaxis_title='股價')
            st.plotly_chart(fig, use_container_width=True)

            # 匯出功能
            st.subheader("💾 匯出")
            excel_buffer = BytesIO()
            data.to_excel(excel_buffer, index=True, engine='xlsxwriter')
            st.download_button("匯出 Excel", excel_buffer.getvalue(), f"{code}_stock_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # 複製分析結果按鈕
            st.subheader("🖱️ 分享分析結果")
            analysis_summary = f"股票代碼：{code}\n股票名稱：{stock_name}\n產業別：{stock_group}\nRSI：{rsi.iloc[-1]:.2f}" if not rsi.empty else "無法計算 RSI"
            st.code(analysis_summary, language='markdown')
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

            # 推薦熱門股票（範例：以成交量排序前 3 大）
            st.subheader("🔍 熱門推薦股票")
            try:
                hot_df = yf.download(["2330.TW", "2303.TW", "2412.TW"], period="1d")["Volume"].iloc[-1].sort_values(ascending=False)
                for symbol, volume in hot_df.items():
                    s_code = symbol.split('.')[0]
                    s_name = twstock.codes[s_code].name if s_code in twstock.codes else ''
                    st.write(f"{s_code} - {s_name}（成交量：{volume}）")
            except:
                st.warning("熱門股票資料讀取失敗")

    except Exception as e:
        st.error(f"發生錯誤：{str(e)}")

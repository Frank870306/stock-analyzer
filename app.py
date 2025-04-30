import streamlit as st
import yfinance as yf
import time
import json
import os
from ta.momentum import RSIIndicator
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime

# 儲存檔案路徑
FAVORITES_FILE = "favorites.json"
NOTES_FILE = "notes.json"
FONT_PATH = "C:\\Windows\\Fonts\\msjh.ttc"  # 微軟正黑體

# 儲存股價的字典
stock_data_cache = {}

# 設置自動更新時間間隔（每隔 5 分鐘刷新一次）
UPDATE_INTERVAL = 300  # 秒（5分鐘）

# 儲存股價快取時間
STOCK_CACHE_DURATION = 3600  # 1 小時內不重新請求股價資料


# 載入最愛與備註資料
def load_data():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r") as f:
            st.session_state.fav_list = json.load(f)
    else:
        st.session_state.fav_list = []

    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            st.session_state.notes = json.load(f)
    else:
        st.session_state.notes = {}


# 儲存最愛與備註資料
def save_data():
    with open(FAVORITES_FILE, "w") as f:
        json.dump(st.session_state.fav_list, f)
    with open(NOTES_FILE, "w") as f:
        json.dump(st.session_state.notes, f)


# 獲取股價資料並快取
def get_stock_price(stock_code):
    global stock_data_cache

    current_time = time.time()

    # 若該股票資料已快取，且快取時間在有效期內，直接返回快取資料
    if (
        stock_code in stock_data_cache
        and current_time - stock_data_cache[stock_code]["time"] < STOCK_CACHE_DURATION
    ):
        return stock_data_cache[stock_code]["price"]

    # 否則重新請求股價資料
    try:
        ticker_symbol = f"{stock_code}.TW"
        stock_data = yf.Ticker(ticker_symbol)
        latest_price = stock_data.history(period="1d")["Close"].iloc[-1]

        # 儲存股價資料到快取
        stock_data_cache[stock_code] = {"price": latest_price, "time": current_time}
        return latest_price
    except Exception as e:
        raise ValueError(f"無法取得股價資料: {str(e)}")


# 初始化 session state
if "fav_list" not in st.session_state:
    st.session_state.fav_list = []
if "notes" not in st.session_state:
    st.session_state.notes = {}
if "selected_code" not in st.session_state:
    st.session_state.selected_code = ""

# 載入資料
load_data()

st.set_page_config(page_title="台股即時分析工具", layout="centered")
st.title("台股即時分析工具")

st.markdown(
    "輸入台股代碼（例如：**2330** 為台積電），系統將抓取技術指標並評估是否為值得投資的時機。"
)

# 我的最愛功能
st.sidebar.header("⭐ 我的最愛")
fav_input = st.sidebar.text_input("輸入股票代碼（如 2330）", key="fav_input")

if st.sidebar.button("加入最愛", key="add_fav"):
    if fav_input and fav_input not in st.session_state.fav_list:
        st.session_state.fav_list.append(fav_input.strip())
        save_data()
        st.success(f"✅ {fav_input.strip()} 已加入最愛！")

if st.session_state.fav_list:
    st.sidebar.markdown("### 快速查詢")
    fav_cols = st.sidebar.columns(3)
    for i, fav_code in enumerate(st.session_state.fav_list):
        col = fav_cols[i % 3]
        if col.button(fav_code, key=f"select_{fav_code}"):
            st.session_state.selected_code = fav_code

        try:
            latest_price = get_stock_price(fav_code)
            col.markdown(f"**最新股價：** {latest_price:.2f} TWD")
        except Exception as e:
            col.markdown(f"**無法取得股價** ({str(e)})")

        if col.button("🗑️", key=f"delete_{fav_code}"):
            st.session_state.fav_list.remove(fav_code)
            save_data()
            st.success(f"✅ {fav_code} 已從最愛中移除！")

# 股票輸入（優先讀取 selected_code）
ticker_input = st.text_input(
    "請輸入台股代碼（例如 2330）",
    value=st.session_state.selected_code,
    key="ticker_input",
)
st.session_state.selected_code = st.session_state.get("ticker_input", "").strip()

# 自動更新機制
if "last_updated" not in st.session_state:
    st.session_state.last_updated = time.time()

# 如果距離上次更新超過 UPDATE_INTERVAL，則重新載入頁面
if (time.time() - st.session_state.last_updated) >= UPDATE_INTERVAL:
    st.session_state.last_updated = time.time()
    st.rerun()  # 重新載入頁面，實現自動更新功能

if ticker_input:
    try:
        code = ticker_input.strip()
        ticker_symbol = f"{code}.TW"
        data = yf.download(ticker_symbol, period="1y", interval="1d")

        if data.empty:
            st.error(f"查無此代碼 {code}，請重新輸入。")
        else:
            stock_info = {
                "name": code,
                "group": "－不詳－",
                "start": "－不詳－",
            }  # 假設沒有資料時
            st.sidebar.markdown("### 🏢 公司資訊")
            st.sidebar.markdown(f"**股票代碼：** {code}")
            st.sidebar.markdown(f"**股票名稱：** {stock_info['name']}")
            st.sidebar.markdown(f"**產業別：** {stock_info['group']}")
            st.sidebar.markdown(f"**上市日期：** {stock_info['start']}")

            close_prices = data["Close"].astype(float).squeeze()
            rsi_calc = RSIIndicator(close=close_prices)
            rsi = rsi_calc.rsi()

            st.subheader("📈 股價走勢圖")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data.index, y=close_prices, mode="lines+markers", name="收盤價"
                )
            )
            fig.update_layout(title="股價走勢", xaxis_title="日期", yaxis_title="股價")
            st.plotly_chart(fig, use_container_width=True)

            if st.button("📄 生成 PDF 報告"):
                st.write("正在生成 PDF...")

                # 創建 PDF 報告
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("msjh", fname=FONT_PATH, uni=True)
                pdf.set_font("msjh", size=12)

                pdf.cell(
                    200,
                    10,
                    txt=f"📊 台股分析報告 - {stock_info['name']} ({code})",
                    ln=True,
                )
                pdf.cell(
                    200,
                    10,
                    txt=f"產業別：{stock_info['group']} / 上市日期：{stock_info['start']}",
                    ln=True,
                )
                pdf.cell(
                    200,
                    10,
                    txt=f"分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    ln=True,
                )
                pdf.cell(200, 10, txt=f"資料區間：1年", ln=True)
                pdf.cell(200, 10, txt=f"最新 RSI 指標：{rsi.iloc[-1]:.2f}", ln=True)
                pdf.cell(200, 10, txt="---", ln=True)

                pdf_output_path = f"{code}_stock_report.pdf"
                pdf.output(pdf_output_path)

                # 檢查 PDF 是否生成成功
                if os.path.exists(pdf_output_path):
                    st.success("PDF 報告已成功生成！")
                    with open(pdf_output_path, "rb") as f:
                        st.download_button(
                            label="📥 下載 PDF 報告",
                            data=f,
                            file_name=pdf_output_path,
                            mime="application/pdf",
                        )
                else:
                    st.error(f"PDF 生成失敗，檢查路徑：{pdf_output_path}")

    except Exception as e:
        st.error(f"錯誤: {str(e)}")

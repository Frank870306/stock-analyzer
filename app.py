import streamlit as st
import yfinance as yf
import twstock
from ta.momentum import RSIIndicator
import plotly.graph_objects as go
import json
import os

# 儲存檔案路徑
FAVORITES_FILE = "favorites.json"
NOTES_FILE = "notes.json"


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

# 顯示加入最愛按鈕
if st.sidebar.button("加入最愛", key="add_fav"):
    if fav_input and fav_input not in st.session_state.fav_list:
        st.session_state.fav_list.append(fav_input.strip())
        save_data()  # 儲存資料
        st.success(f"✅ {fav_input.strip()} 已加入最愛！")

# 顯示我的最愛
if st.session_state.fav_list:
    st.sidebar.markdown("### 快速查詢")
    fav_cols = st.sidebar.columns(3)
    for i, fav_code in enumerate(st.session_state.fav_list):
        col = fav_cols[i % 3]
        if col.button(fav_code, key=f"select_{fav_code}"):
            st.session_state.selected_code = fav_code

        # 顯示即時股價
        try:
            ticker_symbol = f"{fav_code}.TW"
            stock_data = yf.Ticker(ticker_symbol)
            latest_price = stock_data.history(period="1d")["Close"].iloc[-1]
            col.markdown(f"**最新股價：** {latest_price:.2f} TWD")
        except Exception as e:
            col.markdown(f"**無法取得股價** ({str(e)})")

        if col.button("🗑️", key=f"delete_{fav_code}"):
            st.session_state.fav_list.remove(fav_code)
            save_data()  # 儲存資料
            st.success(f"✅ {fav_code} 已從最愛中移除！")
            st.rerun()  # 強制刷新頁面，立即反映最愛列表更新

# 股票輸入（優先讀取 selected_code）
ticker_input = st.text_input(
    "請輸入台股代碼（例如 2330）",
    value=st.session_state.selected_code,
    key="ticker_input",
)

# 每次輸入時同步更新 selected_code
st.session_state.selected_code = st.session_state.get("ticker_input", "").strip()

# 中文版的查詢區間對照
period_mapping = {
    "最近1個月": "1mo",
    "最近3個月": "3mo",
    "最近6個月": "6mo",
    "最近1年": "1y",
    "最近2年": "2y",
    "最近5年": "5y",
}

# 選擇查詢區間（中文）
st.sidebar.header("🗓️ 選擇資料區間")
period_label = st.sidebar.selectbox(
    "請選擇查詢區間", list(period_mapping.keys()), index=2
)
period_option = period_mapping[period_label]

if ticker_input:
    try:
        code = ticker_input.strip()
        ticker_symbol = f"{code}.TW"
        data = yf.download(ticker_symbol, period=period_option, interval="1d")

        # 檢查資料是否抓取成功
        if data.empty:
            st.error(f"查無此代碼 {code}，請重新輸入。")
        else:
            stock_info = twstock.codes.get(code)
            if stock_info and hasattr(stock_info, "name"):
                stock_name = stock_info.name
                stock_group = getattr(stock_info, "group", "－不詳－")
                stock_start = getattr(stock_info, "start", "－不詳－")
            else:
                stock_name = code
                stock_group = "－不詳－"
                stock_start = "－不詳－"

            st.sidebar.markdown("### 🏢 公司資訊")
            st.sidebar.markdown(f"**股票代碼：** {code}")
            st.sidebar.markdown(f"**股票名稱：** {stock_name}")
            st.sidebar.markdown(f"**產業別：** {stock_group}")
            st.sidebar.markdown(f"**上市日期：** {stock_start}")

            close_prices = data["Close"].astype(float).squeeze()

            # 計算 RSI
            rsi_calc = RSIIndicator(close=close_prices)
            rsi = rsi_calc.rsi()

            # 顯示股價走勢圖
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

            # 顯示備註表單
            note_key = f"note_input_{code}"
            current_note = st.session_state.notes.get(code, "")

            st.subheader("📝 個股備註")
            with st.form(f"note_form_{code}"):

                note_input = st.text_area("輸入備註", value=current_note, key=note_key)
                submitted = st.form_submit_button("💾 儲存備註")
                if submitted:
                    st.session_state.notes[code] = st.session_state[note_key]
                    save_data()  # 儲存資料
                    st.success("✅ 備註已儲存！")

            if code in st.session_state.notes and st.session_state.notes[code]:
                st.info(st.session_state.notes[code])

                # 顯示單一備註清除按鈕
                if st.button("🗑️ 清除此備註", key=f"clear_note_{code}"):
                    del st.session_state.notes[code]
                    save_data()  # 儲存資料
                    st.success(f"✅ {code} 的備註已刪除！")
                    st.rerun()  # 強制刷新頁面，立即反映備註刪除
            else:
                st.warning("尚無備註")

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

            st.subheader("🖱️ 分享分析結果")
            analysis_summary = (
                f"股票代碼：{code}\n股票名稱：{stock_name}\n產業別：{stock_group}\nRSI：{rsi.iloc[-1]:.2f}"
                if not rsi.empty
                else "無法計算 RSI"
            )
            st.code(analysis_summary, language="markdown")
    except Exception as e:
        st.error(f"發生錯誤：{str(e)}")

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
for key in ["fav_list", "notes", "selected_code"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key != "selected_code" else ""

# 載入資料
load_data()

# 頁面設定
st.set_page_config(page_title="台股即時分析工具", layout="centered")
st.title("📈 台股即時分析工具")

st.markdown(
    "輸入台股代碼（例如：**2330** 為台積電），系統將抓取技術指標並評估是否為值得投資的時機。"
)
st.divider()

# -- Sidebar 我的最愛 --
st.sidebar.header("⭐ 我的最愛")

fav_input = st.sidebar.text_input("輸入股票代碼（如 2330）", key="fav_input")

add_col, del_col = st.sidebar.columns([2, 1])
if add_col.button("➕ 加入", key="add_fav"):
    if fav_input:
        fav_code = fav_input.strip()
        if fav_code not in st.session_state.fav_list:
            st.session_state.fav_list.append(fav_code)
            save_data()
            st.sidebar.success(f"✅ {fav_code} 已加入最愛！")
        else:
            st.sidebar.info(f"⚡ {fav_code} 已在最愛中")
    else:
        st.sidebar.warning("請輸入股票代碼！")

if st.session_state.fav_list:
    st.sidebar.markdown("### 🔍 快速查詢")
    fav_cols = st.sidebar.columns(3)
    for i, fav_code in enumerate(st.session_state.fav_list):
        col = fav_cols[i % 3]
        if col.button(fav_code, key=f"select_{fav_code}"):
            st.session_state.selected_code = fav_code

    st.sidebar.divider()

# -- 主體 股票查詢 --
ticker_input = st.text_input(
    "請輸入台股代碼（例如 2330）",
    value=st.session_state.selected_code,
    key="ticker_input",
)
st.session_state.selected_code = ticker_input.strip()

# 查詢區間
st.sidebar.header("📅 查詢區間")
period_mapping = {
    "最近1個月": "1mo",
    "最近3個月": "3mo",
    "最近6個月": "6mo",
    "最近1年": "1y",
    "最近2年": "2y",
    "最近5年": "5y",
}
period_label = st.sidebar.selectbox(
    "選擇資料期間", list(period_mapping.keys()), index=2
)
period_option = period_mapping[period_label]

if ticker_input:
    try:
        code = ticker_input.strip()
        ticker_symbol = f"{code}.TW"
        data = yf.download(ticker_symbol, period=period_option, interval="1d")

        if data.empty:
            st.error(f"❌ 查無代碼 {code}，請確認股票代碼。")
        else:
            stock_info = twstock.codes.get(code)
            stock_name = stock_info.name if stock_info else code
            stock_group = getattr(stock_info, "group", "－不詳－")
            stock_start = getattr(stock_info, "start", "－不詳－")

            # 公司資訊
            st.subheader("🏢 公司基本資料")
            with st.container():
                st.markdown(f"- **股票代碼：** {code}")
                st.markdown(f"- **股票名稱：** {stock_name}")
                st.markdown(f"- **產業別：** {stock_group}")
                st.markdown(f"- **上市日期：** {stock_start}")

            st.divider()

            # 股價走勢
            st.subheader("📈 股價走勢圖")
            close_prices = data["Close"].astype(float)
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data.index, y=close_prices, mode="lines+markers", name="收盤價"
                )
            )
            fig.update_layout(
                title="股價走勢",
                xaxis_title="日期",
                yaxis_title="股價 (TWD)",
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # 備註
            st.subheader("📝 個股備註")
            note_key = f"note_input_{code}"
            current_note = st.session_state.notes.get(code, "")

            with st.form(f"note_form_{code}"):
                note_input = st.text_area(
                    "輸入或更新備註", value=current_note, key=note_key
                )
                submitted = st.form_submit_button("💾 儲存備註")
                if submitted:
                    st.session_state.notes[code] = st.session_state[note_key]
                    save_data()
                    st.success("✅ 備註已更新！")

            if current_note:
                st.info(f"備註內容：{current_note}")

                if st.button("🗑️ 清除備註", key=f"clear_note_{code}"):
                    del st.session_state.notes[code]
                    save_data()
                    st.success(f"✅ {code} 備註已刪除")
                    st.rerun()
            else:
                st.warning("目前尚無備註")

            st.divider()

            # 投資評估
            st.subheader("📊 投資評估 (RSI指標)")
            rsi_calc = RSIIndicator(close=close_prices)
            rsi = rsi_calc.rsi()
            if not rsi.empty:
                latest_rsi = rsi.iloc[-1]
                if latest_rsi < 30:
                    st.success(f"RSI {latest_rsi:.2f} ➔ 超賣區，考慮進場！")
                elif latest_rsi > 70:
                    st.warning(f"RSI {latest_rsi:.2f} ➔ 超買區，謹慎操作！")
                else:
                    st.info(f"RSI {latest_rsi:.2f} ➔ 觀望中。")
            else:
                st.error("⚠️ 無法計算 RSI 指標")

            st.divider()

            # 分享結果
            st.subheader("🖱️ 分析結果分享")
            st.code(
                (
                    f"""股票代碼：{code}
股票名稱：{stock_name}
產業別：{stock_group}
RSI：{rsi.iloc[-1]:.2f}"""
                    if not rsi.empty
                    else "無法計算 RSI"
                ),
                language="markdown",
            )
    except Exception as e:
        st.error(f"❗ 發生錯誤：{str(e)}")
else:
    st.info("請輸入股票代碼開始分析～")

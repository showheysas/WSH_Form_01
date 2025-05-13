import streamlit as st
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
import re
import json
from google.oauth2.service_account import Credentials

# 日本語フォント指定
def get_japanese_font():
    font_paths = [
        "/usr/share/fonts/truetype/ipafont-gothic/ipagp.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return fm.FontProperties(fname=path)
    return None

jp_font = get_japanese_font()

# スタイル調整
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
    background-color: #fffdf7;
    color: #3e3221;
}
.stButton>button {
    background-color: #d8bfa0;
    color: black;
    border-radius: 10px;
    padding: 0.5em 1.2em;
    font-size: 1.1em;
}
.stTextInput input, .stTextArea textarea {
    color: #3e3221;
    background-color: #fffef8;
    border-radius: 6px;
    font-size: 1rem;
}
@media (prefers-color-scheme: dark) {
    html, body, [class*="css"] {
        background-color: #121212 !important;
        color: #ffffff !important;
    }
    .stTextInput input, .stTextArea textarea {
        color: #ffffff !important;
        background-color: #2a2a2a !important;
        border: 1px solid #444 !important;
        font-size: 1rem;
        border-radius: 6px;
    }
    .stButton>button {
        background-color: #e1cbb0 !important;
        color: #000 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Google Sheets API認証
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("202505-WSH-Form").sheet1
else:
    st.error("Google認証情報が見つかりません。Secretsを設定してください。")
    sheet = None

st.title("週末共有会アンケート！")

st.markdown("""
Tech0・9期の週末共有会の開催時間を決めるアンケートです。  
参加しやすい時間帯をチェックボックスで選んで「送信」してください！
名前・ご意見は任意です。無記名でも回答できます。
みなさんの回答でヒートマップも進化します！
ぜひ回答ください！
""")

days = ["土", "日", "月", "金"]
hours = [f"{h}:00" for h in range(6, 24)]
column_ratios = [1] + [1] * len(days)

selected_slots = []
with st.form("time_form"):
    st.write("### 参加しやすい時間帯を選んでください")

    # ヘッダー行（曜日：絵文字で代替強調）
    header_cols = st.columns(column_ratios)
    header_cols[0].write(" ")
    for i, day in enumerate(days):
        label = "🟦 土" if day == "土" else "🟥 日" if day == "日" else day
        header_cols[i + 1].write(f"**{label}**")

    # チェックボックスマトリクス
    for hour in hours:
        label = f"{hour}～"
        row = st.columns(column_ratios)
        row[0].write(f"**{label}**")
        for i, day in enumerate(days):
            key = f"{day}-{hour}"
            if row[i + 1].checkbox(" ", key=key):
                selected_slots.append(key)

    name = st.text_input("お名前（任意）")
    feedback = st.text_area("ご意見・ご感想（任意）")
    submitted = st.form_submit_button("送信")

    if submitted:
        if selected_slots:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = [timestamp, name, feedback, ", ".join(selected_slots)]
            if sheet:
                next_row = len(sheet.get_all_values()) + 1
                sheet.insert_row(record, next_row, value_input_option="USER_ENTERED")
                st.success("ご回答ありがとうございました！")
        else:
            st.warning("少なくとも1つの時間帯を選択してください。")

# ヒートマップ表示
if sheet:
    try:
        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=["日時", "名前", "ご意見・ご感想", "選択"])

        all_selected = df["選択"].dropna().apply(lambda x: re.split(r"\s*,\s*", x)).explode().str.replace("～", "").str.strip()
        counts = all_selected.value_counts()

        heatmap_df = pd.DataFrame(0, index=hours, columns=days)
        for item, count in counts.items():
            if "-" in item:
                day, hour = item.split("-")
                if day in days and hour in hours:
                    heatmap_df.loc[hour, day] = count

        st.markdown("### 集計ヒートマップ")
        fig, ax = plt.subplots(figsize=(8, 10))
        cmap = sns.light_palette("#d3bfa4", as_cmap=True)
        sns.heatmap(
            heatmap_df,
            annot=True,
            fmt="d",
            cmap=cmap,
            ax=ax,
            cbar_kws={"shrink": 0.6},
            annot_kws={"fontproperties": jp_font} if jp_font else None
        )
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10, fontproperties=jp_font)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontsize=10, fontproperties=jp_font)
        ax.set_xlabel("曜日", fontproperties=jp_font)
        ax.set_ylabel("時間帯", fontproperties=jp_font)
        st.pyplot(fig)

        st.write(f"回答人数：{df.shape[0]}名")

        st.markdown("### 人気の時間帯トップ3")
        top3 = counts.head(3)
        for i, (label, count) in enumerate(top3.items(), 1):
            st.write(f"{i}. {label}：{count}票")

    except Exception as e:
        st.error(f"ヒートマップの生成中にエラーが発生しました：{e}")

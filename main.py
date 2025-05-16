import streamlit as st
import datetime
import gspread
import pandas as pd
import random
import os
import json
from google.oauth2.service_account import Credentials
import re
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.stylable_container import stylable_container

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

# ページ分岐用クエリ
query = st.query_params.get("page", "home")

# トップページ
if query == "home":
    st.title("週末共有会アンケート！")

    if sheet:
        try:
            data = sheet.get_all_values()
            df = pd.DataFrame(data[1:], columns=["Datetime", "Name", "Feedback", "Selection"])
            comments = df["Feedback"].dropna().tolist()
            if comments:
                comment = st.session_state.get("random_comment", random.choice(comments))
                st.markdown("### みんなのコメント")
                st.info(f"💬 {comment}")

                if st.button("次を見る"):
                    st.session_state["random_comment"] = random.choice(comments)
                    st.experimental_rerun()
        except Exception as e:
            st.error("コメントの読み込みに失敗しました")

    st.markdown("### アンケートはこちら！")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📱 スマホ"):
            st.experimental_set_query_params(page="mobile")
            st.experimental_rerun()
    with col2:
        if st.button("💻 PC"):
            st.experimental_set_query_params(page="pc")
            st.experimental_rerun()

# PC用フォーム（既存のマトリクス式UI）
elif query == "pc":
    st.title("週末共有会アンケート！")

    st.markdown("""
    Tech0・9期の週末共有会の開催時間を決めるアンケートです。  
    参加しやすい時間帯をチェックボックスで選んで「送信」してください！  
    名前・ご意見は任意です。無記名でも回答できます。  
    """)

    days = ["Sat", "Sun", "Mon", "Fri"]
    hours = [f"{h}:00" for h in range(6, 24)]
    column_ratios = [1] + [1] * len(days)

    selected_slots = []
    with st.form("time_form_pc"):
        st.write("### 参加しやすい時間帯を選んでください")

        header_cols = st.columns(column_ratios)
        header_cols[0].write(" ")
        for i, day in enumerate(days):
            label = "🟦 Sat" if day == "Sat" else "🟥 Sun" if day == "Sun" else day
            header_cols[i + 1].write(f"**{label}**")

        for hour in hours:
            row = st.columns(column_ratios)
            row[0].write(f"**{hour}～**")
            for i, day in enumerate(days):
                key = f"{day}-{hour}"
                if row[i + 1].checkbox(" ", key=key):
                    selected_slots.append(key)

        name = st.text_input("お名前（任意）", key="name_pc")
        feedback = st.text_area("ご意見・ご感想（任意）", key="fb_pc")
        submitted = st.form_submit_button("送信")

        if submitted:
            if selected_slots:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = [timestamp, name, feedback, ", ".join(selected_slots)]
                sheet.insert_row(record, len(sheet.get_all_values()) + 1)
                st.success("ご回答ありがとうございました！")
            else:
                st.warning("少なくとも1つの時間帯を選択してください。")

# スマホ向けフォーム（縦スクロールしやすく単純なリスト形式）
elif query == "mobile":
    st.title("週末共有会アンケート！（スマホ版）")

    st.markdown("選びやすいように、時間帯を1列にしました。チェックして送信してください。")

    days = ["Sat", "Sun", "Mon", "Fri"]
    hours = [f"{h}:00" for h in range(6, 24)]

    selected_slots = []
    with st.form("time_form_mobile"):
        for day in days:
            st.write(f"### {'🟦' if day == 'Sat' else '🟥' if day == 'Sun' else ''} {day}")
            for hour in hours:
                key = f"{day}-{hour}"
                if st.checkbox(f"{hour}～", key=key):
                    selected_slots.append(key)

        name = st.text_input("お名前（任意）", key="name_mobile")
        feedback = st.text_area("ご意見・ご感想（任意）", key="fb_mobile")
        submitted = st.form_submit_button("送信")

        if submitted:
            if selected_slots:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = [timestamp, name, feedback, ", ".join(selected_slots)]
                sheet.insert_row(record, len(sheet.get_all_values()) + 1)
                st.success("ご回答ありがとうございました！")
            else:
                st.warning("少なくとも1つの時間帯を選択してください。")

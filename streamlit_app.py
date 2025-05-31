import streamlit as st
import pandas as pd
from openai import OpenAI
import os

# OpenAI APIキー（Secretsから取得）
client = OpenAI()

# Excel読み込み関数
@st.cache_data
def load_job_data():
    return pd.read_excel("data/zentai_anken.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# 条件抽出関数
def extract_conditions(user_input):
    conditions = {
        "年齢": "",
        "性別": "",
        "地域": [],
        "免許": [],
        "寮": "",
    }
    # 年齢
    if "20代" in user_input:
        conditions["年齢"] = "20代"
    elif "30代" in user_input:
        conditions["年齢"] = "30代"
    elif "40代" in user_input:
        conditions["年齢"] = "40代"
    elif "50代" in user_input:
        conditions["年齢"] = "50代"

    # 性別
    if "男性" in user_input:
        conditions["性別"] = "男性"
    elif "女性" in user_input:
        conditions["性別"] = "女性"

    # 地域
    for pref in ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
                 "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
                 "新潟", "富山", "石川", "福井", "山梨", "長野",
                 "岐阜", "静岡", "愛知", "三重",
                 "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山",
                 "鳥取", "島根", "岡山", "広島", "山口",
                 "徳島", "香川", "愛媛", "高知",
                 "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]:
        if pref in user_input:
            conditions["地域"].append(pref)

    # 寮
    if "寮" in user_input:
        conditions["寮"] = "あり"
    elif "通勤" in user_input:
        conditions["寮"] = "なし"

    # 免許
    for keyword in ["リフト", "フォークリフト", "玉掛け", "クレーン", "溶接", "電気工事", "危険物"]:
        if keyword in user_input:
            conditions["免許"].append(keyword)

    return conditions

# マッチング関数
def match_jobs(df, conditions):
    df_match = df.copy()
    if conditions["年齢"]:
        df_match = df_match[df_match["年齢"] == conditions["年齢"]]
    if conditions["性別"]:
        df_match = df_match[df_match["性別"] == conditions["性別"]]
    if conditions["地域"]:
        df_match = df_match[df_match["勤務地"].str.contains('|'.join(conditions["地域"]))]
    if conditions["寮"]:
        df_match = df_match[df_match["寮"] == conditions["寮"]]
    for menkyo in conditions["免許"]:
        df_match = df_match[df_match["資格"].str.contains(menkyo, na=False)]
    return df_match

# 表示関数
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# Streamlit UI
st.title("📋 MatchingChat | 求人マッチングAIチャット")

user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        conditions = extract_conditions(user_input)
        matched = match_jobs(df_jobs, conditions)
        matched_count = len(matched)

        if matched_count == 0:
            reply = "申し訳ありません、条件に一致する求人が見つかりませんでした。条件を変更してもう一度お試しください。"
        elif matched_count > 5:
            reply = f"{matched_count}件の求人が見つかりました。さらに詳細な条件を追加いただくか、Excelで抽出してください。"
            st.download_button("📥 Excelで抽出する", matched.to_excel(index=False), file_name="matching_jobs.xlsx")
        else:
            summaries = summarize_jobs(matched.head(5))
            prompt = f"以下の求人情報を元に、求職者に自然な文章で5件のおすすめを紹介してください。\n\n{chr(10).join(summaries)}"
            res = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "あなたは親切な求人紹介アシスタントです。"},
                          {"role": "user", "content": prompt}]
            )
            reply = res.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"エラーが発生しました：{str(e)}")

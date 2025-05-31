import streamlit as st
import pandas as pd
import openai
import os
import json

# OpenAI APIキー
openai.api_key = os.getenv("OPENAI_API_KEY")

# モデル切替
model_option = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"])

# Excel読み込み関数
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# GPTで条件を抽出
@st.cache_data(show_spinner=False)
def extract_conditions_gpt(user_input):
    prompt = f"""
    以下のテキストから、求人マッチングに必要な情報を抽出してください。
    出力は JSON形式で、以下のキーを含めてください：
    - 年齢（例：30代、40代前半、50歳まで など）
    - 性別（例：男性、女性、男女）
    - 地域（都道府県名やエリア名）
    - 寮（あり・なし）
    - 免許（フォークリフト、クレーンなどあれば）

    テキスト：{user_input}
    """
    response = openai.ChatCompletion.create(
        model=model_option,
        messages=[
            {"role": "system", "content": "あなたは求人条件の抽出を行うアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
    )
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {}

# マッチング関数（あいまい検索対応）
def match_jobs(df, conditions):
    df_match = df.copy()
    
    if "年齢" in conditions and conditions["年齢"]:
        df_match = df_match[df_match["年齢"].astype(str).str.contains(conditions["年齢"], na=False)]

    if "性別" in conditions and conditions["性別"]:
        df_match = df_match[df_match["性別"].astype(str).str.contains(conditions["性別"], na=False)]

    if "地域" in conditions and conditions["地域"]:
        if isinstance(conditions["地域"], list):
            df_match = df_match[df_match["勤務地"].astype(str).str.contains('|'.join(conditions["地域"]), na=False)]
        else:
            df_match = df_match[df_match["勤務地"].astype(str).str.contains(conditions["地域"], na=False)]

    if "寮" in conditions and conditions["寮"]:
        if conditions["寮"] == "あり":
            df_match = df_match[df_match["寮"].astype(str).str.contains("寮", na=False)]
        elif conditions["寮"] == "なし":
            df_match = df_match[~df_match["寮"].astype(str).str.contains("寮", na=False)]

    if "免許" in conditions and conditions["免許"]:
        for menkyo in conditions["免許"]:
            df_match = df_match[df_match["資格"].astype(str).str.contains(menkyo, na=False)]

    return df_match

# 表示関数
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# Streamlit UI
st.title("📋 MatchingChat（GPTモデル切替対応）")

user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        conditions = extract_conditions_gpt(user_input)
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
            res = openai.ChatCompletion.create(
                model=model_option,
                messages=[
                    {"role": "system", "content": "あなたは親切な求人紹介アシスタントです。"},
                    {"role": "user", "content": prompt}
                ]
            )
            reply = res.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"エラーが発生しました：{str(e)}")

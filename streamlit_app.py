import streamlit as st
import pandas as pd
import os
from openai import OpenAI

# OpenAI APIキー（Secretsから取得）
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# モデル選択
model = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"])

# タイトル
st.title("📋 MatchingChat（GPTモデル切替対応）")

# Excel読み込み関数
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# ChatGPTで条件を抽出する関数
def extract_conditions_with_gpt(user_input, model="gpt-3.5-turbo"):
    prompt = f"""
次の文章から、年齢・性別・地域・寮希望・免許（資格）を以下のJSON形式で抽出してください。

# 出力形式
{{
    "年齢": "",     # 例: "40代", "43歳", "50代後半"
    "性別": "",     # "男性" または "女性"
    "地域": [],     # ["福岡", "佐賀"]
    "寮": "",       # "あり" or "なし"
    "免許": []      # ["フォークリフト", "玉掛け", "溶接"]
}}

# 入力文:
「{user_input}」
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "あなたは求人条件をJSONで抽出するアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
    )
    try:
        conditions = eval(response.choices[0].message.content)
        return conditions
    except Exception:
        raise ValueError("条件抽出に失敗しました")

# 求人マッチング関数
def match_jobs(df, conditions):
    df_match = df.copy()
    if conditions["年齢"]:
        df_match = df_match[df_match["年齢"].astype(str).str.contains(conditions["年齢"], na=False)]
    if conditions["性別"]:
        df_match = df_match[df_match["性別"].astype(str).str.contains(conditions["性別"], na=False)]
    if conditions["地域"]:
        df_match = df_match[df_match["勤務地"].astype(str).str.contains('|'.join(conditions["地域"]), na=False)]
    if conditions["寮"]:
        df_match = df_match[df_match["寮"].astype(str).str.contains(conditions["寮"], na=False)]
    for menkyo in conditions["免許"]:
        df_match = df_match[df_match["資格"].astype(str).str.contains(menkyo, na=False)]
    return df_match

# 要約関数
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# ユーザー入力受付
user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        with st.spinner("条件を抽出しています..."):
            conditions = extract_conditions_with_gpt(user_input, model=model)

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
                model=model,
                messages=[
                    {"role": "system", "content": "あなたは親切な求人紹介アシスタントです。"},
                    {"role": "user", "content": prompt}
                ]
            )
            reply = res.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        st.error(f"エラーが発生しました：{str(e)}")

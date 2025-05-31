import streamlit as st
import pandas as pd
import openai
import os

# OpenAI APIキーの設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Excel読み込み関数
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# 条件抽出をGPTに依頼
def extract_conditions_with_gpt(user_input, model):
    prompt = f"""
以下は求人マッチングのための求職者の希望条件です。
この条件から、以下の5つの項目を抽出してください。

- 年齢（20代、30代、40代、50代など）
- 性別（男性、女性など）
- 地域（都道府県名）※複数可
- 寮（あり／なし）
- 免許（リフト、玉掛け、クレーンなど）※複数可

出力形式は以下のJSON形式にしてください：
{{
  "年齢": "",
  "性別": "",
  "地域": [],
  "寮": "",
  "免許": []
}}

---

入力文：{user_input}
"""
    try:
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは求人条件を正確に抽出するAIです。"},
                {"role": "user", "content": prompt}
            ]
        )
        content = res.choices[0].message.content
        return eval(content)  # JSON形式として評価（信頼できる入力前提）
    except Exception as e:
        st.error("条件抽出に失敗しました")
        return None

# マッチング関数
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

# 表示関数
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# Streamlit UI
st.title("📋 MatchingChat（GPTモデル切替対応）")

model = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"])
user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        conditions = extract_conditions_with_gpt(user_input, model)
        if not conditions:
            raise ValueError("条件抽出失敗")

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
        with st.chat_message("assistant"):
            st.error(f"エラーが発生しました：{str(e)}")

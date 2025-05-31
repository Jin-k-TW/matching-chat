import streamlit as st
import pandas as pd
import openai
import os
from dotenv import load_dotenv

# .envからAPIキーを読み込む
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

@st.cache_data
def load_job_data():
    return pd.read_excel("data/全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

st.title("📋 MatchingChat | 求人マッチングAIチャット")

if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉・神奈川、寮希望、リフト・玉掛けあり など）")

def extract_conditions(user_message):
    system_prompt = """
あなたは人材紹介エージェントです。
以下のユーザーの文章から、次の5項目を抽出してください：
- 年齢（例：「40代」）
- 性別（例：「男性」）
- 希望勤務地（複数都道府県も可。リスト形式で）
- 資格（保有する免許・資格をすべてリスト形式で抽出。例：「リフト免許」「玉掛け」「溶接」など）
- 入寮希望の有無（true/false）

次のようなJSONで返してください：
{
  "年齢": "40代",
  "性別": "男性",
  "勤務地": ["東京都", "神奈川県"],
  "資格": ["リフト免許", "玉掛け"],
  "入寮": true
}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2
    )
    return eval(response.choices[0].message.content)

def match_jobs(df, conds):
    df_filtered = df.copy()

    if "勤務地" in conds and isinstance(conds["勤務地"], list):
        condition = df_filtered["都道府県"].astype(str).apply(
            lambda x: any(loc in x for loc in conds["勤務地"])
        )
        df_filtered = df_filtered[condition]

    if "資格" in conds and isinstance(conds["資格"], list):
        for qual in conds["資格"]:
            df_filtered = df_filtered[df_filtered["案件備考"].astype(str).str.contains(qual, na=False, case=False)]

    if "入寮" in conds and conds["入寮"]:
        df_filtered = df_filtered[df_filtered["案件備考"].astype(str).str.contains("寮|入寮", na=False)]

    return df_filtered

def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        prompt = f"""
以下の求人情報を求職者向けに魅力的に紹介してください：
勤務地: {row['都道府県']}
案件備考: {row['案件備考']}
        """
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        summaries.append(response.choices[0].message.content.strip())
    return summaries

MAX_VISIBLE = 5
LARGE_MATCH_THRESHOLD = 30

if user_input:
    st.session_state.history.append(("user", user_input))
    with st.spinner("マッチング中..."):
        conditions = extract_conditions(user_input)
        matched = match_jobs(df_jobs, conditions)
        matched_count = len(matched)

        if matched_count == 0:
            st.session_state.history.append(("bot", "申し訳ありません。条件に合致する求人が見つかりませんでした。"))

        elif matched_count > LARGE_MATCH_THRESHOLD:
            st.session_state.history.append(("bot", f"{matched_count}件の求人が見つかりました。"))
            action = st.radio("このあとの対応をお選びください：", ("さらに条件を絞り込む", "このままExcelで出力する"))

            if action == "さらに条件を絞り込む":
                st.session_state.history.append(("bot", "もう少し詳しい希望条件を教えてください（例：交替制、休日、日勤希望など）"))

            else:
                st.download_button(
                    label="📁 求人をExcelでダウンロード",
                    data=matched.to_excel(index=False),
                    file_name="matching_jobs.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        else:
            summaries = summarize_jobs(matched.head(MAX_VISIBLE))
            for summary in summaries:
                st.session_state.history.append(("bot", summary))

            st.download_button(
                label="📁 Excelでダウンロード（上位のみ）",
                data=matched.head(MAX_VISIBLE).to_excel(index=False),
                file_name="matching_jobs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

for role, msg in st.session_state.history:
    with st.chat_message("🧑‍💼" if role == "user" else "🤖"):
        st.markdown(msg)
import streamlit as st
import pandas as pd
import openai
import os

# OpenAI APIキー
openai.api_key = os.getenv("OPENAI_API_KEY")

# Excel読み込み関数
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# モデル選択
st.title("📋 MatchingChat（GPTモデル切替対応）")
model = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"])

# 条件抽出用プロンプトテンプレート
PROMPT_TEMPLATE = """
以下の入力文から、以下の形式で辞書として条件を抽出してください：
- 年齢（例："40代"、"20~30"）
- 性別（例："男性"、"女性"、"男女"など）
- 地域（例："東京"、"埼玉" など複数可）
- 寮希望（例："寮あり" or "通勤"）
- 免許（例："リフト"、"玉掛け"など）

出力は以下のようにJSONフォーマットで返してください：
{{
  "年齢": "",
  "性別": "",
  "地域": [],
  "寮": "",
  "免許": []
}}

---
入力文:
{user_input}
"""

# GPTを使って条件抽出
def extract_conditions_with_gpt(user_input):
    prompt = PROMPT_TEMPLATE.format(user_input=user_input)
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは人材紹介アシスタントです。"},
                {"role": "user", "content": prompt},
            ]
        )
        text = response.choices[0].message.content.strip()
        conditions = eval(text)  # JSON風文字列を辞書に変換
        return conditions
    except Exception as e:
        st.error(f"条件抽出エラー: {e}")
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

# 表示文要約
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# UI入力
user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        conditions = extract_conditions_with_gpt(user_input)
        if not conditions:
            st.error("条件抽出に失敗しました")
        else:
            matched = match_jobs(df_jobs, conditions)
            matched_count = len(matched)

            if matched_count == 0:
                st.chat_message("assistant").markdown("申し訳ありません、条件に一致する求人が見つかりませんでした。条件を変更してもう一度お試しください。")
            elif matched_count > 5:
                st.chat_message("assistant").markdown(f"{matched_count}件の求人が見つかりました。さらに条件を追加いただくか、以下からExcelでダウンロードできます。")
                st.download_button("📥 Excelで抽出する", matched.to_excel(index=False), file_name="matching_jobs.xlsx")
            else:
                summaries = summarize_jobs(matched.head(5))
                prompt = f"以下の求人情報を元に、求職者に自然な文章で5件のおすすめを紹介してください。\n\n{chr(10).join(summaries)}"
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "あなたは親切な求人紹介アシスタントです。"},
                        {"role": "user", "content": prompt},
                    ]
                )
                reply = response.choices[0].message.content
                st.chat_message("assistant").markdown(reply)

    except Exception as e:
        st.chat_message("assistant").error(f"エラーが発生しました：{str(e)}")

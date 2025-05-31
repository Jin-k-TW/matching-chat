import streamlit as st
import pandas as pd
import os
import openai

# APIキーはSecretsから取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# モデル選択UI
model = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"], index=1)

st.title("📋 MatchingChat（GPTモデル切替対応）")

# データ読み込み（キャッシュ）
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# 条件抽出をGPTに任せる
@st.cache_data(show_spinner=False)
def extract_conditions_with_gpt(user_input):
    prompt = f"""
    以下の文章から、求人マッチングに必要な条件を抽出してください：
    ・年齢（例：20代, 30代, 40代, 50代などの表記）
    ・性別（男性 / 女性）
    ・地域（都道府県）
    ・寮の希望（寮希望 or 通勤）
    ・保有資格（フォークリフト、玉掛け、クレーンなど）

    出力形式は以下のJSONで返してください：
    {{
      "年齢": "",
      "性別": "",
      "地域": [],
      "寮": "",
      "免許": []
    }}

    入力: "{user_input}"
    """

    try:
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは求人条件を正確に構造化するアシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = res["choices"][0]["message"]["content"]
        import json
        return json.loads(content)
    except Exception as e:
        st.error("条件抽出に失敗しました")
        return None

# マッチング処理
def match_jobs(df, conditions):
    df_match = df.copy()
    if conditions["年齢"]:
        df_match = df_match[df_match["年齢"].str.contains(conditions["年齢"], na=False)]
    if conditions["性別"]:
        df_match = df_match[df_match["性別"].str.contains(conditions["性別"], na=False)]
    if conditions["地域"]:
        df_match = df_match[df_match["勤務地"].str.contains('|'.join(conditions["地域"]), na=False)]
    if conditions["寮"]:
        df_match = df_match[df_match["寮"].str.contains(conditions["寮"], na=False)]
    for keyword in conditions["免許"]:
        df_match = df_match[df_match["資格"].str.contains(keyword, na=False)]
    return df_match

# 表示要約関数
def summarize_jobs(df):
    return [f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}"
            for _, row in df.iterrows()]

# ユーザー入力
user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛け など）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    conditions = extract_conditions_with_gpt(user_input)

    if conditions:
        matched = match_jobs(df_jobs, conditions)
        matched_count = len(matched)

        if matched_count == 0:
            reply = "申し訳ありません、条件に一致する求人が見つかりませんでした。条件を変更してもう一度お試しください。"
        elif matched_count > 5:
            reply = f"{matched_count}件の求人が見つかりました。Excelでダウンロードしてご確認ください。"
            st.download_button("📥 Excelで抽出する", matched.to_excel(index=False), file_name="matching_jobs.xlsx")
        else:
            summaries = summarize_jobs(matched.head(5))
            prompt = f"以下の求人情報を求職者に自然な文章で紹介してください：\n\n" + "\n".join(summaries)
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
    else:
        with st.chat_message("assistant"):
            st.error("条件抽出に失敗しました")

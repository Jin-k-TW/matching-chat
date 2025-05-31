import streamlit as st
import pandas as pd
from openai import OpenAI
import os

# OpenAI APIクライアントの初期化
client = OpenAI()

# Excel読み込み（キャッシュ付き）
@st.cache_data
def load_job_data():
    return pd.read_excel("全体案件.xlsx", sheet_name="Sheet1")

df_jobs = load_job_data()

# 入力された希望条件からフィルタ条件を抽出
def extract_conditions(user_input):
    conditions = {
        "年齢": "",
        "性別": "",
        "地域": [],
        "免許": [],
        "寮": "",
    }

    # 年齢（表現揺れ含む）
    if "20" in user_input:
        conditions["年齢"] = "20"
    elif "30" in user_input:
        conditions["年齢"] = "30"
    elif "40" in user_input:
        conditions["年齢"] = "40"
    elif "50" in user_input:
        conditions["年齢"] = "50"

    # 性別（表現揺れをカバー）
    if "男" in user_input:
        conditions["性別"] = "男"
    elif "女" in user_input:
        conditions["性別"] = "女"

    # 都道府県抽出
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

    # 寮 or 通勤
    if "寮" in user_input:
        conditions["寮"] = "あり"
    elif "通勤" in user_input:
        conditions["寮"] = "なし"

    # 免許（複数ワード対応）
    for keyword in ["リフト", "フォークリフト", "玉掛け", "クレーン", "溶接", "電気工事", "危険物"]:
        if keyword in user_input:
            conditions["免許"].append(keyword)

    return conditions

# フィルタによる求人抽出
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

# GPTへの要約用の求人データ整形
def summarize_jobs(df):
    summaries = []
    for _, row in df.iterrows():
        summaries.append(f"【勤務地】{row['勤務地']}｜【仕事内容】{row['仕事内容']}｜【給与】{row['給与']}｜【寮】{row['寮']}")
    return summaries

# --- Streamlit UI ---

st.title("📋 MatchingChat（GPTモデル切替対応）")

# 🔄 モデル選択セレクタ
model_choice = st.selectbox("使用するモデルを選んでください", ["gpt-3.5-turbo", "gpt-4"])

# 🎯 ユーザー入力
user_input = st.chat_input("希望条件をご入力ください（例：40代男性、東京・埼玉、寮希望、リフト・玉掛けなど）")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        # 条件抽出とマッチ
        conditions = extract_conditions(user_input)
        matched = match_jobs(df_jobs, conditions)
        matched_count = len(matched)

        if matched_count == 0:
            reply = "申し訳ありません、条件に一致する求人が見つかりませんでした。"
        elif matched_count > 5:
            reply = f"{matched_count}件の求人が見つかりました。より詳細な条件をご入力いただくか、Excelで出力してください。"
            st.download_button("📥 Excelで抽出する", matched.to_excel(index=False), file_name="matching_jobs.xlsx")
        else:
            summaries = summarize_jobs(matched.head(5))
            prompt = f"""以下の求人情報をもとに、求職者の希望条件に合いそうなおすすめを自然な文章で紹介してください。

条件: {user_input}

求人一覧:
{chr(10).join(summaries)}
"""
            res = client.chat.completions.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": "あなたは優秀な求人紹介アシスタントです。求職者に合った仕事を、わかりやすく丁寧に提案してください。"},
                    {"role": "user", "content": prompt}
                ]
            )
            reply = res.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"エラーが発生しました：{str(e)}")

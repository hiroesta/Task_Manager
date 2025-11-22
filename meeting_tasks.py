import os
import json
from openai import OpenAI

# ====== 設定 ======
TRANSCRIPT_FILE = "transcript.txt"  # Teamsの文字起こしファイル
OUTPUT_JSON = "tasks.json"          # タスクリストの保存先
OUTPUT_MERMAID = "diagram.mmd"      # アローダイアグラム用の出力ファイル

MODEL_NAME = "gpt-4.1-mini"         # 適宜変更可

# 自分の呼ばれ方（会議内での名前・呼称）
USER_ALIASES = ["大江さん", "Dさん"]

# OpenAI APIキーは環境変数 OPENAI_API_KEY に入れておく想定
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
あなたはプロジェクトマネジメントの専門家兼テキスト解析エンジンです。
与えられた会議の文字起こしから、ユーザー本人に割り当てられたタスクだけを抽出し、
タスクの依存関係を推論してJSON形式で出力してください。

出力は必ず次のJSONスキーマに従ってください:

{
  "tasks": [
    {
      "id": "一意なID (T1, T2 のような文字列)",
      "title": "短いタスク名",
      "detail": "必要ならタスクの詳細。不要なら空文字でもよい。",
      "owner": "自分",
      "deadline": "YYYY-MM-DD または null",
      "depends_on": ["T1", "T2", ...]
    }
  ]
}

注意:
- 会話の中で、ユーザーの名前や「〜さんお願い」「〜担当で」などの表現から、
  ユーザーに割り当てられたタスクのみを抽出してください。
- 「まず」「そのあと」「終わったら」「…が完了してから」などの表現から依存関係を推論してください。
- 不明な締切は null にしてください。
- JSON以外のテキストは出力しないでください。
"""


def call_openai_for_tasks(transcript: str, user_aliases: list[str]) -> dict:
    """文字起こしからタスクJSONを生成"""
    aliases_str = ", ".join(user_aliases)
    user_prompt = f"""
ユーザーの呼ばれ方: {aliases_str}

以下が会議の文字起こしです。この内容からタスクを抽出してください。

---
{transcript}
---
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    # {"tasks":[...]} の dict が返ってくる想定
    return response.choices[0].message.parsed


def tasks_to_mermaid(tasks: list[dict]) -> str:
    """タスクJSON → Mermaidのアローダイアグラム記法に変換"""
    lines = ["graph LR"]

    # ノード定義
    for task in tasks:
        # ラベル内にダブルクォートがあると壊れるのでエスケープ（簡易）
        title = task["title"].replace('"', '\\"')
        lines.append(f'  {task["id"]}["{title}"]')

    # 依存関係（矢印）
    for task in tasks:
        for dep in task.get("depends_on", []):
            lines.append(f"  {dep} --> {task['id']}")

    return "\n".join(lines)


def main():
    # 1. 文字起こしファイル読み込み
    with open(TRANSCRIPT_FILE, encoding="utf-8") as f:
        transcript = f.read()

    # 2. OpenAIでタスク抽出
    result = call_openai_for_tasks(transcript, USER_ALIASES)
    tasks = result.get("tasks", [])

    # 3. JSONとして保存
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 4. Mermaidコード生成＆保存
    mermaid_code = tasks_to_mermaid(tasks)
    with open(OUTPUT_MERMAID, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    # 5. コンソールに概要表示
    print("=== 抽出されたタスク一覧 ===")
    for t in tasks:
        deps = ", ".join(t.get("depends_on", [])) or "（依存なし）"
        print(f"- {t['id']}: {t['title']}  [依存: {deps}]")

    print(f"\nタスクJSON: {OUTPUT_JSON}")
    print(f"Mermaidコード: {OUTPUT_MERMAID} に出力しました。")


if __name__ == "__main__":
    main()

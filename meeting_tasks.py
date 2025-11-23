import os
import json
from pathlib import Path
from openai import OpenAI
import argparse

# ====== 設定 ======
OUTPUT_JSON = "./output/tasks.json"          # タスクリストの保存先
OUTPUT_MERMAID = "./output/diagram.mmd"      # アローダイアグラム用の出力ファイル
OUTPUT_ROOT = Path("output")             # 出力先ルート

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


import json
from openai import OpenAI

client = OpenAI()

MODEL_NAME = "gpt-4.1-mini"  # ここは存在するモデル名にしておく

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
- 出力は**有効なJSONのみ**を返し、説明文や余計な文章は一切出力しないでください。
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
        # response_format は一旦使わず、自前で JSON としてパースする
        # response_format={"type": "json_object"},
    )

    # ← ここがさっきと違うところ！
    content = response.choices[0].message.content

    # 必要なら一回中身を見る
    # print(content)

    data = json.loads(content)  # JSON文字列としてパース
    return data  # {"tasks": [...]} の dict を返す


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
    # ======== 引数処理 ========
    parser = argparse.ArgumentParser(description="会議文字起こしからタスク抽出してdiagram.mmdを生成するツール")
    parser.add_argument("input_file", help="入力となる文字起こしファイル（.txtなど）")
    args = parser.parse_args()

    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"エラー: 入力ファイルが見つかりません → {input_path}")
        return

    # ======== 文字起こし読み込み ========
    transcript = input_path.read_text(encoding="utf-8")

    # ======== タスク抽出 ========
    result = call_openai_for_tasks(transcript, USER_ALIASES)
    tasks = result.get("tasks", [])

    # ======== Mermaid生成 ========
    mermaid_code = tasks_to_mermaid(tasks)  # ← 関数名はあなたのコードに合わせる

    # ======== 出力フォルダ作成（連番 + 参照ファイル名） ========
    base_name = input_path.stem  # ファイル名（拡張子なし）
    OUTPUT_ROOT.mkdir(exist_ok=True)

    existing_numbers = []
    for d in OUTPUT_ROOT.iterdir():
        if d.is_dir() and d.name.split("_", 1)[-1] == base_name:
            num_str = d.name.split("_")[0]
            if num_str.isdigit():
                existing_numbers.append(int(num_str))

    next_no = max(existing_numbers) + 1 if existing_numbers else 1
    folder_name = f"{next_no:03d}_{base_name}"
    run_dir = OUTPUT_ROOT / folder_name
    run_dir.mkdir(parents=True, exist_ok=False)

    # ======== 保存 ========
    json_path = run_dir / "tasks.json"
    mmd_path = run_dir / "diagram.mmd"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mmd_path.write_text(mermaid_code, encoding="utf-8")

    # ======== 表示 ========
    print("=== 抽出されたタスク一覧 ===")
    for t in tasks:
        deps = ", ".join(t.get("depends_on", [])) or "（依存なし）"
        print(f"- {t['id']}: {t['title']} [依存: {deps}]")

    print(f"\n出力フォルダ: {run_dir}")
    print(f"  - tasks.json")
    print(f"  - diagram.mmd")


if __name__ == "__main__":
    main()

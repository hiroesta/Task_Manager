# functions.py
import json
from pathlib import Path
from typing import List, Dict, Any

from config import client, MODEL_NAME, OUTPUT_ROOT

# システムプロンプト
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
- 出力は有効なJSONのみを返し、説明文や余計な文章は一切出力しないでください。
"""


def _parse_json_content(content: str) -> Dict[str, Any]:
    """
    モデルの出力から JSON 部分だけを抜き出して dict にして返す。
    - 素直なJSON
    - 前後に説明文がついたJSON
    - ```json ... ``` に囲まれたJSON
    などに耐えるためのヘルパー。
    """
    if not content or not content.strip():
        raise ValueError("モデルから空のレスポンスが返されました（content が空です）。")

    text = content.strip()

    # 1. まずはそのまま JSON として試す
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. ```json ... ``` 形式を想定
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            inner = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                # だめなら inner をベースに次の処理へ
                text = inner

    # 3. 先頭の { から最後の } までを抜き出して再トライ
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        inner = text[start : end + 1]
        try:
            return json.loads(inner)
        except json.JSONDecodeError as e:
            snippet = inner[:200].replace("\n", "\\n")
            raise ValueError(
                f"JSON として解釈できませんでした（抜き出し後）。先頭200文字: {snippet}"
            ) from e

    # 4. どうしても JSON が見つからない
    snippet = text[:200].replace("\n", "\\n")
    raise ValueError(f"レスポンス内に JSON らしき部分が見つかりません。先頭200文字: {snippet}")


def call_openai_for_tasks(transcript: str, user_aliases: List[str]) -> Dict[str, Any]:
    """
    会議の文字起こしテキストからタスク情報(JSON)を生成する
    """
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
        # response_format は使わず、自前で JSON をパースする
    )

    content = response.choices[0].message.content

    # デバッグしたいときは一時的にコメントアウトを外す
    # print("=== DEBUG raw content ===")
    # print(content)

    data = _parse_json_content(content)
    return data  # {"tasks": [...]} の dict


def tasks_to_mermaid(tasks: List[Dict[str, Any]]) -> str:
    """
    タスク配列 → Mermaid の graph 記法に変換
    """
    lines: List[str] = ["graph LR"]

    # ノード定義
    for task in tasks:
        task_id = str(task.get("id", "UNKNOWN"))
        title = str(task.get("title", "")).replace('"', '\\"')
        lines.append(f'  {task_id}["{title}"]')

    # 依存関係（矢印）
    for task in tasks:
        task_id = str(task.get("id", "UNKNOWN"))
        for dep in task.get("depends_on", []) or []:
            lines.append(f"  {dep} --> {task_id}")

    return "\n".join(lines)


def create_output_dir(input_path: Path) -> Path:
    """
    output 配下に「連番_参照ファイル名」のフォルダを作成して Path を返す。
    例: output/001_meeting
    """
    OUTPUT_ROOT.mkdir(exist_ok=True)

    base_name = input_path.stem  # 拡張子なしファイル名
    existing_numbers: List[int] = []

    for d in OUTPUT_ROOT.iterdir():
        if not d.is_dir():
            continue

        parts = d.name.split("_", 1)
        if len(parts) != 2:
            continue

        num_str, name_part = parts
        if not num_str.isdigit():
            continue

        if name_part != base_name:
            continue

        existing_numbers.append(int(num_str))

    next_no = max(existing_numbers) + 1 if existing_numbers else 1
    folder_name = f"{next_no:03d}_{base_name}"
    run_dir = OUTPUT_ROOT / folder_name
    run_dir.mkdir(parents=True, exist_ok=False)

    return run_dir

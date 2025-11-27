# meeting_tasks.py
import argparse
import json
from pathlib import Path

from config import USER_ALIASES
from functions import call_openai_for_tasks, tasks_to_mermaid, create_output_dir
from render_ddm import render_ddm  # ← 追加 import


def main() -> None:
    # ======== 引数処理 ========
    parser = argparse.ArgumentParser(
        description="Teams会議の文字起こしからタスク抽出＋Mermaidフロー図を生成するツール"
    )
    parser.add_argument(
        "input_file",
        help="入力となる文字起こしファイルのパス（例: scripts/meeting.txt）",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"エラー: 入力ファイルが見つかりません → {input_path}")
        return

    # ======== 文字起こし読み込み ========
    transcript = input_path.read_text(encoding="utf-8")

    # ======== タスク抽出 (OpenAI) ========
    try:
        result = call_openai_for_tasks(transcript, USER_ALIASES)
    except Exception as e:
        print("タスク抽出中にエラーが発生しました。")
        print(f"type: {type(e).__name__}")
        print(f"detail: {e}")
        return

    tasks = result.get("tasks", [])

    if not tasks:
        print("タスクが抽出されませんでした。プロンプトや入力内容を見直してください。")
        return

    # ======== Mermaid生成 ========
    mermaid_code = tasks_to_mermaid(tasks)

    # ======== 出力フォルダ作成（連番_参照ファイル名） ========
    run_dir = create_output_dir(input_path)
    json_path = run_dir / "tasks.json"
    mmd_path = run_dir / "diagram.mmd"
    ddm_path = run_dir / "diagram.ddm"  # mkddm 用 .ddm ファイル（中身は mermaid と同じ想定）

    # ======== 保存 ========
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    mmd_path.write_text(mermaid_code, encoding="utf-8")
    ddm_path.write_text(mermaid_code, encoding="utf-8")

    # ======== コンソール表示 ========
    print("=== 抽出されたタスク一覧 ===")
    for t in tasks:
        deps = ", ".join(t.get("depends_on", []) or []) or "（依存なし）"
        print(f"- {t.get('id', 'UNKNOWN')}: {t.get('title', '')}  [依存: {deps}]")

    print("\n=== 出力ファイル ===")
    print(f"出力フォルダ: {run_dir}")
    print(f"  - {json_path.name}")
    print(f"  - {mmd_path.name}")
    print(f"  - {ddm_path.name}")

    # ======== mkddm でレンダリング（別モジュールに委譲） ========
    render_ddm(ddm_path)


if __name__ == "__main__":
    main()

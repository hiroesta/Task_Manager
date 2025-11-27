# render_ddm.py
import os
import subprocess
from pathlib import Path


def render_ddm(ddm_path: Path) -> None:
    """
    mkddm フォルダに移動して `npm run render <ddm_path>` を実行し、
    終了後に元のディレクトリに戻る。

    ddm_path: 実際に生成された .ddm ファイルへの絶対 or 相対 Path
    """
    ddm_path = ddm_path.resolve()

    # meeting_tasks.py が置かれているディレクトリを「プロジェクトルート」とみなす
    project_root = Path(__file__).resolve().parent
    mkddm_dir = project_root / "mkddm"

    if not mkddm_dir.exists():
        print("\n[注意] mkddm フォルダが見つからなかったため、npm run render はスキップしました。")
        print(f"想定パス: {mkddm_dir}")
        return

    # mkddm から見た .ddm ファイルの相対パスを作成
    ddm_rel = os.path.relpath(ddm_path, mkddm_dir)

    print("\n=== mkddm でダイアグラムをレンダリングします ===")
    print(f"作業ディレクトリ: {mkddm_dir}")
    print(f"実行コマンド   : npm run render {ddm_rel}")

    original_cwd = Path.cwd()
    try:
        # mkddm ディレクトリに移動して npm 実行
        os.chdir(mkddm_dir)

        # Windows を想定して shell=True + 文字列コマンド
        cmd = f'npm run render "{ddm_rel}"'
        completed = subprocess.run(cmd, shell=True)

        if completed.returncode != 0:
            print(f"\n[npm] npm run render 実行中にエラーが発生しました（終了コード: {completed.returncode}）。")
        else:
            print("\n[npm] npm run render が正常に完了しました。")
    except FileNotFoundError:
        print("\nエラー: npm コマンドが見つかりませんでした。Node.js / npm がインストールされているか確認してください。")
    finally:
        # 必ず元のディレクトリに戻る
        os.chdir(original_cwd)
        print(f"\n作業ディレクトリを元に戻しました: {original_cwd}")

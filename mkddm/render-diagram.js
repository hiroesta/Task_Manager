// render-diagram.js
// 使い方:
//   node render-diagram.js input.mmd
//   node render-diagram.js input.mmd output.png

const { exec } = require("child_process");
const path = require("path");

const inputPath = process.argv[2];
const outputPathArg = process.argv[3];

if (!inputPath) {
  console.error("使い方: node render-diagram.js input.mmd [output.png]");
  process.exit(1);
}

// 出力ファイル名（第2引数がなければ input.mmd → input.png にする）
const defaultOutput = (() => {
  const parsed = path.parse(inputPath);
  return path.join(parsed.dir, `${parsed.name}.png`);
})();

const outputPath = outputPathArg || defaultOutput;

// npx で mermaid-cli (mmdc) を呼び出す
const cmd = `npx -y @mermaid-js/mermaid-cli -i "${inputPath}" -o "${outputPath}"`;

console.log("実行コマンド:", cmd);

exec(cmd, (error, stdout, stderr) => {
  if (error) {
    console.error("エラーが発生しました:");
    console.error(stderr || error.message);
    process.exit(1);
  }

  if (stdout) {
    console.log(stdout);
  }
  if (stderr) {
    console.log(stderr);
  }

  console.log(`✅ 画像を出力しました: ${outputPath}`);
});

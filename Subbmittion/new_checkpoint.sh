#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ $# -ne 1 || ! $1 =~ ^[0-9]+$ ]]; then
  echo "Cách dùng: ./new_checkpoint.sh <số checkpoint>" >&2
  exit 2
fi

number=$1
target="CheckPoint${number}"
if [[ -e "$target" ]]; then
  echo "Đã tồn tại: $target" >&2
  exit 1
fi

cp -R _template "$target"
mv "$target/main.tex" "$target/checkpoint${number}.tex"
sed -i "s/__CP__/${number}/g" "$target/cover.tex"
echo "Đã tạo $target/checkpoint${number}.tex"
echo "Mở file đó trong VS Code và chọn LaTeX Workshop > Build LaTeX project."

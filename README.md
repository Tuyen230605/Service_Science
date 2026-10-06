# Báo cáo LaTeX

## Cấu trúc thư mục

```text
Subbmittion/
├── _common/                 # Preamble và cấu hình build dùng chung
├── _template/               # Mẫu tạo checkpoint mới
├── CheckPoint1/
│   ├── checkpoint1.tex      # File chính, ghép toàn bộ báo cáo
│   ├── cover.tex            # Trang bìa
│   ├── sections/            # Nội dung chia theo từng phần
│   ├── figures/             # Hình của Checkpoint 1
│   ├── glossary.tex         # Thuật ngữ
│   ├── references.bib       # Tài liệu tham khảo
│   └── build/               # PDF và file trung gian do LaTeX tạo
├── CheckPoint2/             # Bộ khung cho checkpoint tiếp theo
├── Archive/                 # Bản nháp cũ, không được ghép vào báo cáo
└── new_checkpoint.sh        # Tạo bộ khung cho checkpoint mới
```

Các thư mục `build/` bên trong từng checkpoint là nơi lưu PDF và file tạm. Không sửa các file `.aux`, `.bbl`, `.bcf`, `.log`, `.glo`, `.gls` hoặc `.synctex.gz` trong đó. Thư mục `build/` rỗng ở cấp workspace không có vai trò và đã được xóa.

## Cài đặt lần đầu

### Ubuntu / Debian

1. Cài [Visual Studio Code](https://code.visualstudio.com/docs/setup/linux) bằng gói `.deb` chính thức.
2. Cài extension LaTeX Workshop trong VS Code: mở **Extensions** (`Ctrl+Shift+X`), tìm `LaTeX Workshop` của James Yu và chọn **Install**. Có thể cài bằng Terminal nếu lệnh `code` đã có trong PATH:

   ```bash
   code --install-extension James-Yu.latex-workshop
   ```

3. Cài TeX Live và các công cụ mà báo cáo này dùng:

   ```bash
   sudo apt update
   sudo apt install -y latexmk biber texlive-latex-extra texlive-lang-other texlive-fonts-recommended texlive-science
   ```

   Bộ này gồm trình biên dịch LaTeX, `latexmk`, `biber`, hỗ trợ tiếng Việt, thuật toán, glossary, TikZ và các gói dùng trong báo cáo.

4. Kiểm tra các lệnh đã sẵn sàng:

   ```bash
   pdflatex --version
   latexmk -v
   biber --version
   makeglossaries --version
   ```

### Windows

1. Cài [Visual Studio Code cho Windows](https://code.visualstudio.com/docs/setup/windows). Chọn **User Installer** nếu chỉ cài cho tài khoản Windows hiện tại.
2. Cài TeX Live:
   - Tải `install-tl-windows.exe` từ [trang TeX Live chính thức](https://tug.org/texlive/windows.html).
   - Chạy installer. Chọn cài đặt đầy đủ nếu máy còn đủ dung lượng; gói đầy đủ giúp có sẵn các thư viện mà báo cáo đang dùng. Quá trình tải và cài có thể mất thời gian.
   - Để thư mục cài đặt mặc định và bật tùy chọn thêm TeX Live vào `PATH` nếu installer hỏi. TeX Live thường tự thêm thư mục lệnh vào PATH.
   - Đóng rồi mở lại VS Code sau khi cài.

   TeX Live cho Windows là lựa chọn dễ dùng nhất cho repository này. Nếu chọn MiKTeX thay thế, bật cài package còn thiếu khi được hỏi và cài thêm Perl; `latexmk` cần Perl để chạy trong LaTeX Workshop.

3. Mở **Extensions** trong VS Code (`Ctrl+Shift+X`), tìm `LaTeX Workshop` của James Yu rồi chọn **Install**. Có thể dùng Terminal nếu lệnh `code` đã có trong PATH:

   ```powershell
   code --install-extension James-Yu.latex-workshop
   ```

4. Mở PowerShell mới và kiểm tra công cụ:

   ```powershell
   pdflatex --version
   latexmk -v
   biber --version
   makeglossaries --version
   ```

   Nếu Windows báo không nhận ra lệnh, khởi động lại máy. Nếu vẫn vậy, thêm thư mục `bin\windows` bên trong thư mục TeX Live đã cài vào **Environment Variables → Path**, rồi mở lại VS Code.

5. Clone repository, mở thư mục repository trong VS Code, mở `Subbmittion/CheckPoint1/checkpoint1.tex`, rồi chọn **LaTeX Workshop → Build LaTeX project**. PDF được tạo tại `Subbmittion/CheckPoint1/build/checkpoint1.pdf`.

### macOS

Cài [MacTeX](https://tug.org/mactex/) rồi cài extension LaTeX Workshop từ Extensions trong VS Code. Nếu terminal không nhận các lệnh TeX, xem hướng dẫn PATH trong [hướng dẫn cài LaTeX Workshop](https://github.com/James-Yu/LaTeX-Workshop/wiki/Install).

## Mở và biên dịch báo cáo

1. Clone repository và mở thư mục gốc trong VS Code:

   ```bash
   git clone https://github.com/Tuyen230605/Service_Science.git
   cd Service_Science
   code .
   ```

2. Mở file chính `Subbmittion/CheckPoint1/checkpoint1.tex`.
3. Chọn biểu tượng **LaTeX Workshop** → **Build LaTeX project**.
4. Chọn **View LaTeX PDF** để xem kết quả. PDF nằm ở `Subbmittion/CheckPoint1/build/checkpoint1.pdf`.

Cấu hình `.vscode/settings.json` của repository đã chọn `latexmk` làm recipe mặc định và đưa file sinh ra vào `build/`. Các checkpoint dùng chung cấu hình LaTeX trong `Subbmittion/_common/`.

## Viết nội dung

- Sửa các file trong `CheckPoint1/sections/`; thứ tự ghép được ghi trong `checkpoint1.tex`.
- Sửa `cover.tex` để thay thông tin trang bìa.
- Đặt ảnh trong `figures/`, rồi dùng đường dẫn như `figures/framework_cp1.png`.
- Thêm nguồn vào `references.bib`, sau đó trích dẫn bằng `\cite{khoa}`.
- Khai báo thuật ngữ trong `glossary.tex`, rồi dùng `\gls{nhan}` trong nội dung.

## Tạo checkpoint mới

Từ Terminal chạy:

```bash
cd Subbmittion
./new_checkpoint.sh 3
```

Thay `3` bằng số checkpoint cần tạo. Lệnh tạo `CheckPoint3/` theo cùng cấu trúc, với file chính `checkpoint3.tex`. Mở file đó trong VS Code và viết nội dung tại `CheckPoint3/sections/01-overview.tex`.

# FinalProject — viết báo cáo song song cho 3 người

Bản khởi tạo theo hình thức báo cáo Checkpoint 2: A4, chữ serif, bìa UET có
khung, thông tin nhóm 8, mục lục, các mục đánh số và chú thích bảng/hình.
Nội dung được tổ chức theo rubric dự án cuối kỳ, hướng tới 12–20 trang chính
sau khi hoàn thiện. Đây là bản làm việc có TODO, chưa phải bản nộp hoàn chỉnh.

## Hai file điều phối

- `_main.tex`: file mở để biên dịch; quản lý package, định dạng, bìa và mục lục.
- `_content.tex`: ghép ba role, tài liệu tham khảo và các phụ lục chung.

Người dùng đã chỉ định tên `_main.tex`; file điều phối thứ hai được đặt là
`_content.tex` để tách cấu hình khỏi thứ tự nội dung. Mỗi role được `\input`
đúng một lần. Không đặt `\documentclass` hay `\begin{document}` trong role.

## Phân công

| File | Người nhận | Phạm vi | Đầu ra phải có |
|---|---|---|---|
| `role_1.tex` | Nhóm điền | Mục 1–4: bài toán, hệ thống, nguồn lực, AS-IS | Resource Map, Journey/Blueprint, BPMN AS-IS, điểm nghẽn gắn với biến đo |
| `role_2.tex` | Nhóm điền | Mục 5–6: dữ liệu, giả định, hàng đợi, mô phỏng, AS-IS | Tham số, công thức có nguồn, kiểm chứng, kết quả A0, giới hạn |
| `role_3.tex` | Nhóm điền | Mục 7–9: TO-BE, đối chứng, độ nhạy, kết luận | Quy tắc cải tiến, bảng so sánh, đánh đổi, rủi ro và kết luận có điều kiện |

Mỗi role có hướng dẫn đầu file, bản nháp nội dung, nguồn đầu vào, đầu ra bàn
giao và TODO cụ thể. Mục tiêu khoảng 4–6 trang/người; điều chỉnh theo độ sâu
phân tích và dung lượng rubric, không thêm trang chỉ để đủ số lượng.

## Quy tắc để làm song song

1. Mỗi người chỉ sửa `role_x.tex` của mình; hình mới đặt `figures/rx_*`.
   Label dùng tiền tố `r1:`, `r2:`, `r3:`. Dùng `\ref{...}` thay vì tự gõ số.
2. Chọn một người ghép bài quản lý hai file điều phối, nguồn trích dẫn và
   phụ lục AI. Không tự thay package, font hoặc thứ tự mục ở từng role.
3. Role 2 là đầu mối `analysis/`. Role 3 có thể viết ngay từ các bảng hiện có;
   khi cần đổi kịch bản, thống nhất với role 2 trước khi chạy lại. Không sửa
   tay bảng do Python sinh. Mọi số trong đoạn văn phải cập nhật theo cùng lần chạy.
4. Giao diện chung: Wq là thời gian từ vào hàng đợi điều dưỡng đến bắt đầu
   xử lý, đơn vị phút; lambda là yêu cầu/giờ; c là số kênh; A0/A1/A2 giữ nguyên
   tên và định nghĩa trong `role_3.tex`.
5. Thêm nguồn mới: đọc và kiểm chứng tài liệu, gửi khóa/tên nguồn cho người
   ghép bài để thêm vào `thebibliography` trong `_content.tex`. Các nguồn hiện
   tại là tài liệu và mã nội bộ; còn TODO bổ sung nguồn học thuật cho lý thuyết.
6. Điền lịch sử AI theo thành phần. Chưa biết lịch sử của tài sản cũ thì ghi
   chưa xác nhận; không tự nhận đã kiểm chứng hoặc đã tự vẽ.

## Prompt giao cho từng người / phiên làm việc

**Role 1:** “Đọc README và comment đầu role_1.tex. Hoàn thiện mục 1–4 theo
rubric và PDF Checkpoint 2. Chỉ sửa role_1.tex và figures/r1_*. Ưu tiên BPMN
AS-IS đúng ký pháp, Resource Map và ranh giới đo Wq. Không bịa dữ liệu quan sát.
Biên dịch qua _main.tex và bàn giao nguồn cùng các TODO chưa xử lý.”

**Role 2:** “Đọc README và comment đầu role_2.tex. Hoàn thiện dữ liệu, phương
pháp và kiểm chứng. Rà soát sai lệch tải cao, sự kiện đổi công suất tại ranh
giới giờ và tái lập đầu ra. Chỉ sửa role_2.tex, figures/r2_* và analysis/ khi
cần; báo role 3 mọi thay đổi số liệu. Phân biệt mô phỏng với quan sát thực.”

**Role 3:** “Đọc README và comment đầu role_3.tex. Hoàn thiện TO-BE, so sánh,
độ nhạy và kết luận từ bảng có nguồn. Chỉ sửa role_3.tex và figures/r3_*.
Không quy tác động A2 riêng cho AI; nêu chi phí chưa tính, mục tiêu phần đuôi
và giới hạn kiểm chứng. Chốt số liệu với role 2 trước khi kết luận.”

## Biên dịch

Từ thư mục `Subbmittion/FinalProject`:

```bash
mkdir -p build
latexmk -pdf -interaction=nonstopmode -file-line-error -outdir=build _main.tex
```

Hoặc dùng Tectonic (đã hỗ trợ nhánh Unicode trong preamble):

```bash
tectonic --keep-logs --outdir build _main.tex
```

PDF: `build/_main.pdf`. Trong VS Code/LaTeX Workshop, mở `_main.tex` và Build;
đầu mỗi role có magic comment trỏ tới file này. pdfLaTeX cần gói tiếng Việt
`vietnam`; Tectonic/XeLaTeX dùng TeX Gyre Termes, TeX Gyre Heros và Latin Modern
Mono trong TeX Live. Không cần biber vì bản này dùng `thebibliography`.

Bản khởi tạo đã biên dịch bằng Tectonic: 20 trang tổng cộng, trong đó 16 trang
nội dung chính. Đã xem bìa và các trang đại diện, kiểm tra tham chiếu và font
tiếng Việt. Nhánh pdfLaTeX được cung cấp cho cấu hình repository, chưa chạy
trên máy này vì không có trình biên dịch đó.

## Trạng thái số liệu và việc còn lại

- Đã ghép hình/bảng có sẵn, không chạy lại hoặc sửa mô phỏng khi tạo khung.
- Thiếu BPMN AS-IS hoàn chỉnh: role 1 xuất `figures/r1_bpmn_asis.pdf`, được
  tự chèn vào báo cáo. Journey/Blueprint và Resource Map cũng cần rà soát.
- Kiểm chứng tải cao hiện lệch khoảng −36.5%; cần làm rõ trước khi gọi mô
  phỏng là đã được kiểm chứng. Code chưa có sự kiện đổi ca độc lập.
- Bảng `tab_validation.tex` có cách in NaN thành vô cực. Bản nháp trình bày
  bốn cấu hình đã chạy và diễn giải riêng trường hợp không ổn định.
- Bảng `tab_assumptions.tex` ghi khoảng lambda 6–12 dù cấu hình thực là 4–12.
  Bản nháp dùng bảng giả định lấy trực tiếp từ CONFIG; bảng gốc chưa sửa.
- Kết quả độ nhạy dùng 30 ngày và seed khác so sánh chính 20 ngày; không
  diễn giải dòng nhu cầu ×1.0 như cùng một lần chạy.
- Trước khi nộp: xử lý TODO, kiểm tra nguồn/AI, đồng bộ số liệu, kiểm tra sơ
  đồ và dung lượng. Chỉ chuyển `\drafttrue` sang `\draftfalse` sau khi đã
  xử lý công việc; tắt hiển thị TODO không có nghĩa nội dung đã hoàn thành.

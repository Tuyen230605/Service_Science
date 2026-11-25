# FinalProject — vấn đề, phân tích và giải pháp

Trọng tâm: hàng chờ giờ cao điểm tại cửa hàng xăng giả định và bố trí nhân viên
phù hợp với nhu cầu. Mạch báo cáo: vấn đề → nguyên nhân giả định → phân tích
hàng đợi → đối chứng A0/A1/A2 → điều kiện và kế hoạch thử nghiệm.

## Làm song song

| File | Người nhận | Phạm vi |
|---|---|---|
| `role_1.tex` | Nhóm điền | Mục 1–4: vấn đề, phạm vi, hệ thống, nguồn lực, AS-IS |
| `role_2.tex` | Nhóm điền | Mục 5–6: dữ liệu, giả định, phương pháp, kiểm chứng, nguyên nhân |
| `role_3.tex` | Nhóm điền | Mục 7–9: giải pháp, đánh giá, kế hoạch thử và kết luận |

Mỗi người sửa role của mình; hình dùng tiền tố `r1_`, `r2_`, `r3_`, label dùng
`r1:`, `r2:`, `r3:`. Role 2 quản lý mã và sinh lại bảng; không sửa tay bảng sinh
bởi Python. Người ghép bài quản lý `_main.tex` và `_content.tex`.

## Cách diễn giải thống nhất

- Số liệu quy mô toàn Hà Nội là căn cứ tham chiếu; mức bình quân chia theo cửa
  hàng là ước tính, không phải số bán quan sát tại một cửa hàng nội thành.
- Lượt xe, giờ cao điểm, thời gian phục vụ và bỏ đi là giả định/mô phỏng.
- A1 kiểm tra điều chỉnh số kênh theo giờ. Cần ghép thành lịch ca có nghỉ và
  kiểm tra thực địa trước khi áp dụng; không khẳng định đã cắt giảm nhân sự.
- A2 kiểm tra giảm thời gian chiếm trụ, giả định 20%. Mức tiết kiệm là tiềm
  năng theo mô hình; chưa chứng minh bằng triển khai QR thực tế.
- Hóa đơn chỉ cho biết lượt đã mua; phải quan sát bổ sung thời điểm vào hàng,
  bắt đầu phục vụ, rời trụ và lượt bỏ đi để đo thời gian chờ.

## Phần mở rộng được bảo lưu

Nội dung SWOT/PESTEL, định vị, GLM và chiến lược dài hạn vẫn nằm trong các macro
`RoleOneSupplement`, `RoleTwoSupplement`, `RoleThreeSupplement` cuối từng role.
Các macro không được gọi trong `_content.tex`, nên không xuất hiện trong PDF.
Không lấy kết quả mở rộng làm kết luận của bản báo cáo trọng tâm.

Trước khi sử dụng lại phần mở rộng cần sửa/kiểm tra: chiến lược thích ứng đang
biết trước tham số kịch bản; cách tính giá trị mất đang gồm cả giao dịch đã
phục vụ; nhu cầu định vị tính từ xe máy nhưng lãi mỗi lượt dùng hỗn hợp ô tô/xe
máy. Đầu ra `ext_*` là kết quả phiên bản trước, chưa sinh lại với bộ mô phỏng
đã sửa. Các nguồn chưa mở kiểm chứng cũng phải được kiểm tra trước khi trích.

## Chạy và biên dịch

Từ thư mục gốc repo (mã dùng import dạng gói `FinalProject.analysis.*`; cần numpy, matplotlib):

```bash
python3 -m unittest FinalProject.analysis.test_simulate -v
python3 -m FinalProject.analysis.run_analysis
```

Bảng sinh ra nằm ở `FinalProject/tables/`, hình ở `FinalProject/figures/`.

Từ thư mục `FinalProject`:

```bash
mkdir -p build
tectonic --keep-logs --outdir build _main.tex
```

Đã sửa sự kiện đổi công suất tại đúng ranh giới giờ; ba kiểm tra hồi quy gồm
tăng kênh, giảm kênh và xe đến đúng giờ đổi ca. Đã chạy lại phân tích chính và
đồng bộ số trong báo cáo. Sai lệch kiểm chứng M/M/c ở tải cao vẫn là giới hạn
cần nêu; sửa sự kiện không có nghĩa toàn bộ mô hình đã được xác nhận.

PDF: `build/_main.pdf`. Giữ các TODO về số liệu thực và nguồn học thuật cho
nhóm hoàn thiện. Chưa có kết quả thử nghiệm tại cửa hàng thật.

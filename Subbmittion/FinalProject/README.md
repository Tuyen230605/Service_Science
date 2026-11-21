# FinalProject — Cửa hàng xăng dầu nội thành Hà Nội (Nhóm 8, INT3501)

Đề tài: hàng đợi, phân bổ nhân viên bơm và chiến lược dịch vụ tại một cửa hàng
xăng đại diện ở nội thành Hà Nội (8 vòi, mở 06:00–22:00). Báo cáo A4, bìa UET,
viết song song bởi 3 người. Đây là bản làm việc có TODO, chưa phải bản nộp.

## Hai file điều phối

- `_main.tex`: preamble, bìa, mục lục, macro `\resulttable`, `\exttable` và kiểu TikZ dùng chung.
- `_content.tex`: ghép ba role, tài liệu tham khảo (có URL nguồn) và phụ lục.

## Phân công

| File | Người nhận | Phạm vi | Đầu ra chính |
|---|---|---|---|
| `role_1.tex` | Nhóm điền | Mục 1–4: bối cảnh, 4 bài toán/4 mục tiêu, tầm nhìn–sứ mệnh, hệ thống dịch vụ, Resource Map, bên liên quan, Blueprint, BPMN AS-IS, SWOT, PESTEL | Mục tiêu đo được, sơ đồ AS-IS có mốc đo $a_i,b_i,d_i$ |
| `role_2.tex` | Nhóm điền | Mục 5–7: hiệu chỉnh từ số liệu công bố, M/M/c, mô phỏng, kiểm chứng, AS-IS, định vị 2/5 điểm, dự báo học máy | Bảng tham số có đơn vị và loại căn cứ (R/E/G) |
| `role_3.tex` | Nhóm điền | Mục 8–11: A0/A1/A2, lịch tối ưu, TO-BE, độ nhạy, rủi ro, kịch bản A/B/C, trải nghiệm khách hàng, kết luận | Quyết định có số liệu và đề xuất định hướng |

Quy tắc làm song song giữ nguyên: mỗi người chỉ sửa role của mình, hình mới đặt
`figures/rx_*`, label dùng tiền tố `r1:`, `r2:`, `r3:`; không sửa tay bảng sinh
từ Python; mọi số trong đoạn văn phải khớp log của lần chạy cuối.

## Chạy lại phân tích

```bash
cd analysis
python3 run_analysis.py        # BT1: AS-IS, A0/A1/A2, độ nhạy, rủi ro -> data/run_log.txt
python3 extension_analysis.py  # BT2–BT4: định vị, kịch bản, khách hàng, học máy -> data/ext_run_log.txt
```

Chỉ cần `numpy` và `matplotlib`. Hai script chạy khoảng 15 giây mỗi script.

## Biên dịch

```bash
tectonic --keep-logs --outdir build _main.tex
```

## Trạng thái dữ liệu

- **Số liệu công bố (R)**: 453 cửa hàng và 110.000 m³ xăng/tháng ở Hà Nội; dân số
  quận 2019; lương nhân viên bán xăng; chiết khấu bán lẻ; giá điều chỉnh 11/2026;
  Tết 2025/2026; đợt 17 cửa hàng tạm dừng bán 3/2026; Chỉ thị 20 và vùng phát thải thấp.
  Nguồn ghi trong `thebibliography`; được tìm ngày 21/11/2026, **nhóm cần mở lại
  từng URL để kiểm chứng**.
- **Ước tính (E)** từ số liệu công bố: lượt xe/ngày, tỷ trọng xe máy, chi phí giờ
  nhân viên, CLV.
- **Giả định (G)**: phân bố theo giờ, thời gian phục vụ, ngưỡng bỏ đi 20 xe, mức
  giảm 20% khi số hóa, tọa độ/chi phí 5 điểm ứng viên, độ kiên nhẫn theo thế hệ.
- Lượt xe đến và lịch sử nhu cầu cho học máy là **mô phỏng**. Khi có dữ liệu hóa
  đơn điện tử theo giờ của một cửa hàng thật, thay `HOURLY_SHARE`, `SERVICE_ASIS`
  và lịch sử trong `extension_analysis.py` rồi chạy lại.
- Nội dung chính hiện khoảng 26 trang, vượt khung 12–20 trang của rubric; có thể
  chuyển SWOT/PESTEL, ma trận phủ, bảng ứng dụng học máy và hình độ nhạy sang phụ lục.

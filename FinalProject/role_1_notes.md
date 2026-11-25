# Ghi chú bàn giao của TV1 (Mô hình dịch vụ)

Cập nhật: 26/11/2026. Bản này làm trên main mới nhất (commit `new` của Tuan-Anh, 25/11 22:12): `role_1.tex` dùng bản của TV1 (đã rút gọn, thêm phân tích định lượng theo góp ý của nhóm); `_content.tex` giữ nguyên các nguồn và dòng khai báo AI Tuan-Anh đã thêm. File này không đưa vào PDF; dùng để nhóm phối hợp và rà soát.

## 1. TV1 đã làm gì, nằm ở đâu

| Batch | Yêu cầu trong bảng phân công | Kết quả | Vị trí |
|---|---|---|---|
| 0 | Thống nhất phạm vi và cấu hình trạm xăng | Cấu hình 8 vòi, 06:00–22:00, AS-IS 6 nhân viên/giờ; định nghĩa lượt khách, kênh phục vụ, mốc aᵢ/bᵢ/dᵢ, kết thúc ngoại lệ, quy trình thanh toán, trong/ngoài phạm vi | `role_1.tex`, Mục 1.3, Bảng `r1:boundary` |
| 1 | Work System Framework, Resource Map, BPMN AS-IS | WSF đủ 9 thành phần (Hình `r1:wsf`); Resource Map có ranh giới, 5 loại nguồn lực, chú giải (Hình `r1:resource-map`) và bảng lợi ích/chi phí/rủi ro (`r1:stakeholders`) | `role_1.tex`, Mục 2–3 |
| 2 | Hoàn thiện BPMN AS-IS, phân tích điểm nghẽn thanh toán | BPMN 2 pool + 3 lane + pool thuế, message flow, 4 nhánh ngoại lệ, chú thích W/F/H và aᵢ/bᵢ/dᵢ ngay trên sơ đồ; bảng chẩn đoán; mục điểm nghẽn thanh toán (TT1–TT3) | `role_1.tex`, Mục 4; `figures/r1_bpmn_asis.bpmn` |
| 3 | Đề xuất thay đổi quy trình, lợi ích và đánh đổi | BPMN TO-BE, bảng thay đổi AS-IS → TO-BE kèm quy tắc vận hành và người chịu trách nhiệm, bảng tác động đến khách và nhân viên | `role_1_tobe.tex` (chưa ghép); `figures/r1_bpmn_tobe.bpmn` |
| 4 | Rà soát mô hình | Kiểm tra BPMN bằng 6 kịch bản (cuối Mục 4.1); checklist rubric và các điểm lệch giữa các role ở mục 4 bên dưới | `role_1.tex`, Mục 4.1; file này |

Nguồn TV1 thêm vào `_content.tex` (chỉ thêm, không sửa nguồn cũ): `bpmn202`, `l2b`, `l3b`, `tbtc2024`. Ba nguồn Tuan-Anh thêm (`maglio2008`, `alter2013`, `vargo2004`) được giữ và được trích ở Mục 2–3. Phụ lục C ghi "Role 1 mở bản gốc, kiểm tra thông tin xuất bản và nội dung trích" cho ba nguồn này, nên TV1 cần mở đọc thật.

**Phân tích định lượng mới (25/11)** — tính từ `analysis/data/lambda_by_hour.csv` và E[S] = 1,568 phút trong `run_log.txt`, khớp Bảng `r2:hourly`:
- 8/16 giờ có ρ ≤ 0,60 (thừa kênh); 08–09, 17–18, 18–19 có ρ ≥ 0,92 (thiếu kênh).
- Từ 17–18 sang 18–19, λ tăng 6% nhưng Wq tăng 4,5 lần (2,7 lên 12,2 phút).
- Mất 1 kênh ở 3 giờ đỉnh thì ρ = 1,11–1,18 > 1; ở giờ thấp vẫn ≤ 0,85.
- Giảm E[S] x% tương đương nhân số kênh với 1/(1−x): 20% ≈ +1,5 kênh; bớt 12,5 giây/xe đưa 18–19 về ρ = 0,85, còn 08–09 và 17–18 chỉ cần bớt 7,5 giây.

## 2. Việc cần thành viên khác làm

**TV3 (trưởng nhóm, người ghép bài)**

1. Ghép phần TO-BE. Trong `role_3.tex`, xóa khối từ dòng `\subsection{Quy trình TO-BE}` đến ngay trước `\FloatBarrier` nằm trên `\section{Đánh giá, độ nhạy và giới hạn}`, rồi thay bằng một dòng `\input{role_1_tobe}`. Nhãn cũ `r3:bpmn` không được tham chiếu ở đâu khác. Bản ghép đã được biên dịch thử ngày 26/11 trên main mới nhất: không lỗi, không còn tham chiếu "??".
2. Số trang: trên main hiện tại (có phần TV1), nội dung chính kết thúc đúng trang 20. Ghép `role_1_tobe.tex` làm tăng đúng một trang (lên 21) vì sơ đồ TO-BE chiếm trọn một trang ngang; bỏ bảng tác động cũng không đủ để về 20. Nếu ghép, cần cắt khoảng một trang ở phần khác.
3. Cập nhật Phụ lục C (khai báo AI) cho đúng phần của TV1, ví dụ:
   - Dòng *Văn bản, bố cục*: "Claude (Anthropic) viết lại Mục 1–4 và phần TO-BE theo yêu cầu của TV1 ngày 24–26/11/2026; TV1 rà soát và chịu trách nhiệm nội dung."
   - Dòng *Sơ đồ*: "Claude dựng tệp BPMN AS-IS/TO-BE (`figures/r1_bpmn_*.bpmn`) và mã TikZ cho WSF, Resource Map; TV1 kiểm tra ký pháp theo L3B."
4. Biên dịch lại `build/_main.pdf` sau khi ghép. Bộ file của TV1 không đụng tới thư mục `build/`, để tránh xung đột file nhị phân.

**TV2 (dữ liệu)**

1. Không cần sửa bᵢ: TV1 đã theo định nghĩa của Bảng `r2:form` (bᵢ = lúc nhân viên cầm vòi bơm); chú thích bᵢ trên BPMN đã chuyển sang task bơm, Mục 1.3 và 4.1 sửa theo. Hệ quả nhỏ: vài giây xe vào trụ, báo yêu cầu trước khi cầm vòi được tính vào Wq chứ không vào S.
2. Thêm vào biểu mẫu quan sát: mốc eᵢ (lúc ngắt vòi bơm), hình thức thanh toán (tiền mặt / QR / thẻ / ứng dụng), kết quả giao dịch (thành công / lỗi / đổi hình thức). Khi có các cột này, nhóm tách được S_bơm và S_tt ≈ dᵢ − eᵢ để kiểm chứng giả thuyết TT1–TT3, cũng như mức giảm 20% của A2.

## 3. Phiếu quan sát thực địa cho TV1 (đối chiếu BPMN với một cửa hàng thật)

Thời lượng: 1 giờ cao điểm (17:00–19:00) và 1 giờ vắng. Mỗi lần đi ghi 30–50 lượt cho mỗi loại xe.

| Câu hỏi cần trả lời | Ghi chép |
|---|---|
| Cửa hàng có bao nhiêu trụ/vòi? Mấy vòi có người phụ trách vào giờ cao điểm và giờ vắng? | |
| Mỗi trụ có làn riêng không? Khách có đổi làn khi làn bên cạnh ngắn hơn không? | |
| Khách báo yêu cầu theo số tiền hay số lít? Có trường hợp nghe nhầm phải làm lại không (H1)? | |
| Thanh toán diễn ra trước hay sau khi bơm? Ai thu tiền? Có quầy thu riêng không? | |
| Tỷ lệ tiền mặt / QR / thẻ ước chừng bao nhiêu? QR có lúc phải chờ báo có lâu hoặc trả lại không (W2, F1)? | |
| Nhân viên có in hay đưa biên lai/HĐĐT không? Khách có phải chờ hóa đơn không? | |
| Có lúc vòi ngừng hoặc hết loại xăng không? Khi đó nhân viên xử lý thế nào, có báo cửa hàng trưởng không (F2, H2)? | |
| Khi hàng dài, có khách bỏ đi không? Hàng khoảng bao nhiêu xe thì bắt đầu có người bỏ đi (so với ngưỡng giả định 20 xe)? | |
| Mốc thời gian mỗi lượt: aᵢ (vào hàng), bᵢ (nhân viên cầm vòi bơm), eᵢ (ngắt vòi), dᵢ (rời trụ) | |

Nếu quy trình thật khác sơ đồ (ví dụ trả tiền trước khi bơm, hoặc có quầy thu riêng), sửa tệp `.bpmn`, cập nhật Bảng `r1:boundary` và báo TV2, TV3, vì thời gian phục vụ S sẽ đổi.

## 4. Checklist rà soát (Batch 4)

**Đối chiếu rubric**

- [x] Phạm vi: định nghĩa lượt khách, kênh phục vụ, điểm bắt đầu/kết thúc, trong/ngoài phạm vi (Mục 1.3); vấn đề được định lượng theo giờ (Mục 1.1).
- [x] Khung mô hình: chọn một khung (WSF), nêu lý do, áp dụng đủ 9 thành phần (Mục 2).
- [x] Resource Map: (i) ranh giới hệ thống; (ii) 5 loại nguồn lực; (iii) ai góp, ai dùng; (iv) dòng thông tin và tương tác; (v) lợi ích/chi phí/rủi ro (Bảng `r1:stakeholders`); có chú giải.
- [x] BPMN: sự kiện bắt đầu/kết thúc, cổng có điều kiện, pool/lane, message flow giữa các pool, ít nhất một nhánh ngoại lệ (có 4), không có sequence flow đi xuyên pool, điểm chờ không bị vẽ thành task.
- [x] Mỗi hình có dòng nguồn và nhãn AI ngay dưới hình.
- [ ] Đối chiếu với cửa hàng thật (phiếu ở mục 3). Còn TODO đỏ trong PDF bản nháp.

**Nhất quán giữa các role**

- [x] Mốc aᵢ, bᵢ, dᵢ ở Mục 5.2 (role 2) trùng với chú thích trên BPMN.
- [x] Định nghĩa bᵢ thống nhất giữa BPMN, Mục 1.3 và Bảng `r2:form` (nhân viên cầm vòi bơm).
- [x] Số liệu dùng chung khớp với mã: 8 vòi, 6 nhân viên, 97,3%/2,7%, ngưỡng 20 xe, 96/88/72 giờ công, chi phí công nghệ 250 nghìn đồng/ngày.
- [x] "Khách không dùng ứng dụng đi theo luồng AS-IS" (role 3) khớp với khối luồng AS-IS trong BPMN TO-BE.
- [x] Giới hạn "mọi vòi phục vụ mọi loại xe" (role 3) khớp với ghi chú hàng chung FCFS ở Bảng `r1:boundary`.
- [ ] Hình TO-BE hiện tại trong `role_3.tex` vẫn vẽ "xếp hàng chờ" thành task và chưa có nhánh ngoại lệ. Phần ghép `role_1_tobe.tex` sửa các điểm này.

## 5. Cách sửa sơ đồ BPMN

1. Mở https://demo.bpmn.io, kéo thả tệp `figures/r1_bpmn_asis.bpmn` (hoặc `r1_bpmn_tobe.bpmn`) vào trang.
2. Sửa xong, tải về cả tệp `.bpmn` và ảnh `.svg` bằng các nút ở góc dưới bên trái.
3. Đổi SVG sang PDF (trên Ubuntu: `rsvg-convert -f pdf -o r1_bpmn_asis.pdf r1_bpmn_asis.svg`; hoặc dùng Inkscape), rồi ghi đè tệp PDF cùng tên trong `figures/`. LaTeX dùng bản PDF.

Sơ đồ WSF và Resource Map là mã TikZ nằm ngay trong `role_1.tex`.

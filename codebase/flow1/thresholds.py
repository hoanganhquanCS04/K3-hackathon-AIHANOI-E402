"""Ngưỡng của cổng 1. CHỈ CHỨA SỐ — không hàm, không logic. Chủ: M2.

Lý do file này tồn tại riêng: tại CP5 phải chỉ được đúng một chỗ khi bị hỏi
"ngưỡng của các bạn là bao nhiêu, đo ra sao". Rải hằng số khắp code là mất khả
năng đó.

TRẠNG THÁI: giá trị dưới đây là TẠM, đặt để cổng 1 chạy và test được ngay.
Task 11 (scripts/calibrate_t1.py) đo trên 30 câu rồi GHI ĐÈ hai số T1_*, kèm bảng
phân bố commit ở eval/t1/distribution.md. Chưa chạy Task 11 thì chưa được đưa hai
số này vào spec.md hay lên slide.

Tín hiệu thực nghiệm đã có: probe trên index thật (419 chunk) cho ratio chỉ
1,13-1,22 kể cả với câu hỏi TRONG phạm vi — T1_RATIO = 1.30 nhiều khả năng là
quá cao và sẽ chặn oan cả câu trả lời được. Đây là lý do KHÔNG tự sửa số ở đây:
sửa tay theo cảm tính là đúng thứ Task 11 được lập ra để thay bằng phép đo.
"""

# Sàn tuyệt đối trên điểm BM25 thô của hit số 1.
# Bắt ca: câu ngoài phạm vi chứa đúng một token hiếm → ratio = inf nhưng abs bé.
T1_ABS = 5.0

# Tỷ số top1 / mean(top2..top5) trên điểm BM25 thô.
# Bắt ca: câu chung chung khớp lem nhem nhiều chunk → abs khá cao nhưng phân bố bẹt.
T1_RATIO = 1.30

# Hit 2 được coi là "gần bằng" hit 1 khi bm25[1] >= AMBIG_BAND * bm25[0].
# Gần bằng VÀ khác buổi → hỏi lại một câu thay vì đoán buổi.
AMBIG_BAND = 0.85

# Hằng số RRF khi hợp nhất BM25 với embedding (Task 13). Giá trị 60 là mặc định
# phổ biến của Reciprocal Rank Fusion.
RRF_K = 60

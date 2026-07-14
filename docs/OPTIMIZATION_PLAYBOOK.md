# Playbook Tối Ưu

Playbook này hướng dẫn team nên đổi gì sau mỗi kết quả từ portal. Vì không có GPU local, mọi thay đổi phải nhỏ, rõ nguyên nhân và có thể rollback.

## Luật 1: Mỗi Lần Chỉ Đổi Một Nhóm Tham Số

Mỗi lần nộp chỉ nên thay đổi một nhóm flag rõ ràng. Nếu điểm tăng, ta cần biết vì sao tăng. Nếu điểm giảm, ta cần biết phải rollback gì.

Luôn ghi lại:

- tên profile;
- điểm tổng;
- ERS nếu portal có trả;
- accuracy hoặc accuracy drop nếu portal có trả;
- ghi chú/log chính từ portal;
- config chính xác đã dùng.

## Nếu Submission Crash Hoặc OOM

Dùng `v1_safe_memory`.

Nguyên nhân khả dĩ: server reserve quá nhiều GPU memory hoặc KV cache cho MiG 18GB.

Hành động:

- giảm `gpu_memory_utilization`;
- giảm `max_model_len`;
- chưa thêm quantization hoặc speculative decoding;
- nộp lại và xem server có qua healthcheck không.

## Nếu Request Bị Reject Vì Context Length

Dùng `v1_long_context`.

Nguyên nhân khả dĩ: `max_model_len` thấp hơn độ dài prompt của một số request trong trace ẩn.

Hành động:

- tăng `max_model_len`;
- giữ nguyên các flag khác;
- so sánh xem điểm tăng hay có lỗi memory mới không.

## Nếu Chạy Ổn Nhưng Điểm Latency Thấp

Dùng `v1_high_memory`.

Nguyên nhân khả dĩ: server ổn định, nhưng scheduler/KV cache còn có thể tận dụng thêm GPU memory.

Hành động:

- tăng nhẹ `gpu_memory_utilization`;
- giữ nguyên `max_model_len`;
- nộp lại và so sánh điểm.

## Nếu Accuracy Tụt

Rollback mọi thay đổi có thể ảnh hưởng chất lượng output.

Ở V1, baseline chưa bật weight quantization, speculative decoding hoặc custom kernel. Nếu các phiên bản sau bị tụt accuracy, nghi ngờ trước:

- quantization;
- speculative decoding quá aggressive;
- thay đổi sampling;
- thay đổi dtype chưa được kiểm chứng;
- thay đổi prompt/request wrapper nếu sau này có thêm proxy.

## Ý Tưởng Tối Ưu Sau Khi Có Baseline Hợp Lệ

Chỉ thử sau khi V1 đã có điểm hợp lệ:

- `v2_short_context`: giảm `max_model_len` để giảm áp lực KV cache nếu TTFT p95 cao.
- `v2_high_memory`: tăng nhẹ `gpu_memory_utilization` nếu run ổn nhưng TBT còn cao.
- `v2_more_conservative_context`: thử context ngắn hơn nữa nếu không có dấu hiệu context reject.
- tuning KV cache dtype nếu image vLLM hỗ trợ;
- tuning `max_num_batched_tokens` và concurrency nếu log cho thấy queueing hoặc batching kém;
- speculative decoding nếu có draft model tương thích và accuracy vẫn ổn;
- model quantization nếu còn đủ lượt nộp và có baseline để rollback.

## Kết Luận Sau V1

V1 đã chạy ổn với `failed_count=0` và `penalty=1`, nên không cần ưu tiên sửa crash/OOM. Bottleneck hiện tại là latency: `ttft_p95_ms=10571` và `tbt_median_ms=59`.

Bước hợp lý tiếp theo là thử `v2_short_context` trước để kiểm tra việc giảm `max_model_len` có làm TTFT/TBT tốt hơn không.

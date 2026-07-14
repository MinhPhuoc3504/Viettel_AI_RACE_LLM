# Hướng Dẫn Đọc Kết Quả Portal

Portal trả về các chỉ số giúp team quyết định bước tối ưu tiếp theo. Không nên chỉ nhìn mỗi điểm tổng.

## Các Metric Chính

`final_score`

Điểm cuối cùng của lần nộp. Đây là metric xếp hạng quan trọng nhất.

`erc`

Tỷ lệ hoặc chỉ số capacity hiệu quả. Giá trị cao hơn thường tốt hơn.

`ers`

Điểm hiệu năng theo cách portal hiển thị. Trong kết quả V1, `ers` trùng với `final_score`.

`penalty`

Hệ số phạt accuracy. `1` là tốt nhất. Nhỏ hơn `1` nghĩa là output bị đánh giá tụt chất lượng.

`passed_slo`

Số request đạt SLO. V1 đạt `83/120`, tức còn nhiều request chưa đủ nhanh.

`failed_count`

Số request lỗi. Nếu lớn hơn `0`, ưu tiên sửa stability trước khi tối ưu tốc độ.

`ttft_p50_ms`

Median time-to-first-token. Cho biết request điển hình phải chờ bao lâu để có token đầu tiên.

`ttft_p95_ms`

Time-to-first-token ở nhóm chậm nhất. Nếu rất cao, hệ thống có tail latency xấu, thường do queueing, context dài, batching hoặc memory pressure.

`tbt_median_ms`

Thời gian sinh token median. Tương đương tín hiệu gần với TPOT/TBT. Nếu cao, decode đang chậm.

`accuracy_drop`

Lưu raw đúng như portal trả về. Không tự diễn giải nếu portal không nói rõ scale.

## Quy Tắc Ra Quyết Định

Nếu `failed_count > 0`: dùng profile an toàn hơn như `v1_safe_memory`.

Nếu `penalty < 1`: rollback thay đổi có khả năng ảnh hưởng output.

Nếu `ttft_p95_ms` rất cao nhưng không fail: thử giảm `max_model_len` hoặc giảm pressure lên KV cache.

Nếu `tbt_median_ms` cao nhưng run ổn: thử tăng nhẹ `gpu_memory_utilization` hoặc các tuning liên quan decode/batching.

Nếu `passed_slo` tăng nhưng score giảm: xem lại penalty hoặc tail latency.


# Phân Tích Sau V1 Và Bước Tiếp Theo

## Kết Quả V1

V1 `v1_baseline` đã có kết quả:

| Metric | Giá trị |
|---|---:|
| final_score | 12.89 |
| erc | 0.691667 |
| penalty | 1 |
| passed_slo | 83 |
| total_count | 120 |
| failed_count | 0 |
| warmup_count | 0 |
| ttft_p50_ms | 888 |
| ttft_p95_ms | 10571 |
| tbt_median_ms | 59 |

## Nhận Định

V1 chạy ổn vì `failed_count=0` và `penalty=1`. Như vậy server không crash, không OOM rõ ràng và chưa bị phạt accuracy.

Điểm thấp chủ yếu do latency:

- `ttft_p95_ms=10571` rất cao, nghĩa là nhóm request chậm nhất phải chờ token đầu tiên quá lâu.
- `tbt_median_ms=59` cao hơn ngưỡng tốt trong đề, làm TPOT/TBT kéo điểm xuống.
- `passed_slo=83/120` nghĩa là còn 37 request chưa đạt SLO.

## Bước V2 Đề Xuất

Ưu tiên thử `v2_short_context`:

```powershell
python scripts/render_compose.py --config configs/submissions/v2_short_context.yaml --output docker-compose.yml
```

Lý do: giảm `max_model_len` từ `32768` xuống `16384` có thể giảm áp lực KV cache và giúp vLLM xử lý request nhanh hơn. Đây là thay đổi có kiểm soát và không ảnh hưởng trực tiếp đến logits/accuracy.

Nếu V2 bị context reject, rollback về `v1_baseline` hoặc thử lại `v1_long_context` tùy log portal.

Nếu V2 chạy ổn nhưng TBT vẫn cao, thử `v2_high_memory`.


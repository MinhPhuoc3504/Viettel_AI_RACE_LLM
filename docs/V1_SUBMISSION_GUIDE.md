# Hướng Dẫn Bản Nộp V1

Tài liệu này giải thích harness nộp bài đầu tiên cho Viettel AI Race LLM. Mục tiêu là để mọi người trong team, kể cả chưa quen với LLM serving, hiểu được bản V1 là gì, dùng để làm gì, tại sao chọn cách này, và có thể tự phát triển tiếp.

## V1 Là Gì

V1 là một harness theo hướng **submission-first**. Team không có GPU/môi trường giống hệ thống chấm, nên repo này được thiết kế để:

- sinh `docker-compose.yml` hợp lệ để nộp lên portal;
- giữ cấu hình từng lần nộp ở dạng có thể tái lập;
- ghi lại điểm/log sau mỗi lần portal chấm;
- giúp team chọn bước tối ưu tiếp theo dựa trên kết quả thật.

V1 chưa nhằm mục tiêu là bản nhanh nhất cuối cùng. Nó là baseline ổn định đầu tiên để có điểm hợp lệ và tạo vòng lặp học từ kết quả.

## Vì Sao Bắt Đầu Bằng Baseline vLLM Conservative

Điểm cuộc thi phụ thuộc vào hiệu năng và độ chính xác:

```text
Score = 100 * ERS * accuracy_penalty
```

`ERS` thưởng cho request có TTFT và TPOT thấp:

- TTFT là thời gian từ lúc gửi request đến token đầu tiên.
- TPOT là thời gian trung bình để sinh mỗi token sau token đầu tiên.

Accuracy Gate phạt nếu chất lượng model giảm. Nếu model trả lời kém hơn baseline quá nhiều, server dù nhanh vẫn có thể bị điểm rất thấp hoặc về 0.

Vì không benchmark local được, V1 tránh các tối ưu rủi ro:

- chưa dùng weight quantization;
- chưa dùng speculative decoding;
- chưa viết custom CUDA/Triton kernel;
- chưa dùng CPU/NVMe offload.

Thay vào đó, V1 dùng official vLLM server với cấu hình memory cẩn thận.

## Các File Trong Harness

`docker-compose.yml`

- File thật sự nộp lên portal.
- Được sinh từ profile bằng `scripts/render_compose.py`.

`configs/submissions/v1_baseline.yaml`

- Profile đầu tiên nên nộp.
- Dùng `gpu_memory_utilization=0.90` và `max_model_len=32768`.
- Mục tiêu: có điểm hợp lệ đầu tiên, giảm rủi ro OOM/crash.

`configs/submissions/v1_safe_memory.yaml`

- Dùng nếu baseline crash, OOM hoặc fail healthcheck.
- Giảm áp lực bộ nhớ.

`configs/submissions/v1_high_memory.yaml`

- Dùng nếu baseline chạy ổn nhưng điểm latency thấp.
- Tăng nhẹ lượng GPU memory vLLM được phép dùng.

`configs/submissions/v1_long_context.yaml`

- Dùng nếu log portal báo prompt bị reject vì context length quá nhỏ.
- Tăng `max_model_len`.

`scripts/render_compose.py`

- Đọc một profile submission.
- Ghi ra `docker-compose.yml`.
- Giúp sinh file nộp deterministic, tránh sửa YAML thủ công bị sai.

`scripts/record_submission.py`

- Chạy sau khi portal trả kết quả.
- Ghi score, status, notes, hash file và log vào `results/submissions.jsonl`.

`scripts/summarize_results.py`

- Chuyển `results/submissions.jsonl` thành `results/LEADERBOARD_NOTES.md`.
- Giúp team so sánh các lần nộp.

`docs/OPTIMIZATION_PLAYBOOK.md`

- Hướng dẫn nên thử gì sau mỗi loại kết quả từ portal.

## Cách Tạo Bản Nộp V1

Từ thư mục gốc repo:

```powershell
python scripts/render_compose.py --config configs/submissions/v1_baseline.yaml --output docker-compose.yml
```

Sau đó nộp file `docker-compose.yml` được sinh ra lên portal.

Nếu máy có Docker, có thể kiểm tra hình dạng YAML trước khi nộp:

```powershell
docker compose config
```

Lệnh này không chứng minh model sẽ chạy được trên GPU của BTC, nhưng bắt được lỗi cú pháp compose.

## Cách Ghi Lại Kết Quả Portal

Ví dụ sau một lần chạy thành công:

```powershell
python scripts/record_submission.py `
  --profile v1_baseline `
  --config configs/submissions/v1_baseline.yaml `
  --status success `
  --score 42.7 `
  --ers 0.427 `
  --accuracy 0.39 `
  --notes "Lan dau co diem hop le"
```

Sau đó tạo lại bảng tổng hợp:

```powershell
python scripts/summarize_results.py
```

Mở `results/LEADERBOARD_NOTES.md` để so sánh các lần nộp.

## Vì Sao Chọn `max_model_len=32768`

Compose mẫu trong đề dùng `262144`, rất lớn. Context càng dài thì KV cache càng tốn VRAM. Trên MiG H200 18GB, đặt context quá lớn có thể giảm concurrency hoặc gây áp lực bộ nhớ.

V1 bắt đầu với `32768` vì xác suất fit cao hơn và vẫn đủ cho nhiều workload prompt dài. Nếu portal báo request bị reject do context length, chuyển sang `v1_long_context`.

## Vì Sao Chọn `gpu_memory_utilization=0.90`

Giá trị cao hơn cho phép vLLM dùng nhiều memory hơn cho KV cache và batching, có thể cải thiện throughput. Nhưng đặt quá sát giới hạn dễ OOM hoặc fragmentation, nhất là trong môi trường chấm ẩn.

V1 bắt đầu ở `0.90` để ưu tiên có điểm hợp lệ. Nếu chạy ổn nhưng chậm, thử `v1_high_memory` với `0.92`.

## Nên Thử Gì Sau V1

Dùng kết quả portal để chọn profile tiếp theo:

| Kết quả portal | Hành động tiếp theo |
|---|---|
| Crash, OOM, healthcheck failed | Nộp `v1_safe_memory` |
| Context length rejected | Nộp `v1_long_context` |
| Chạy ổn nhưng điểm thấp | Nộp `v1_high_memory` |
| Accuracy drop | Rollback các thay đổi có thể ảnh hưởng output |
| Không có log hữu ích, chỉ thấy điểm thấp | Chỉ đổi một flag nhỏ rồi ghi lại kết quả |

Với kết quả V1 hiện tại, server đã chạy ổn nhưng latency còn cao. Hướng ưu tiên là thử `v2_short_context`, sau đó so sánh với `v1_baseline` trong `results/LEADERBOARD_NOTES.md`.

## Những Hướng Chưa Dùng Ở V1

Quantization có thể giảm memory và tăng tốc, nhưng có thể làm giảm accuracy GPQA. Chỉ nên thử khi đã có baseline hợp lệ và có đường rollback.

Speculative decoding có thể tăng tốc decode, nhưng thêm độ phức tạp và có thể lỗi nếu draft model hoặc version vLLM không tương thích.

Custom CUDA/Triton kernel rất mạnh nhưng tốn công phát triển và khó debug. Đây không phải bước đầu phù hợp khi team chưa có phần cứng local giống môi trường chấm.

CPU/NVMe offload có thể tránh OOM, nhưng thường làm latency xấu đi. Vì công thức điểm phạt latency rất mạnh, offload nên là fallback hơn là lựa chọn đầu tiên.

## Checklist Trước Khi Nộp

- `docker-compose.yml` được sinh từ đúng config mong muốn.
- Config dùng cho lần nộp được lưu lại.
- Tên profile rõ ràng và không nhập nhằng.
- Không sửa tay `docker-compose.yml` sau khi render, trừ khi có lý do cụ thể.
- Sau khi portal trả kết quả, ghi lại ngay bằng `scripts/record_submission.py`.

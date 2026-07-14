# Workflow Thử Nghiệm Liên Tục

Mục tiêu của thư mục này là biến quá trình thi thành một vòng lặp có kiểm soát. Vì team không có GPU local, portal là nguồn benchmark thật duy nhất.

## Vòng Lặp Chuẩn

1. Chọn một profile trong `configs/submissions/`.
2. Sinh `docker-compose.yml`.
3. Nộp portal.
4. Nhận điểm/log.
5. Ghi kết quả bằng `scripts/record_submission.py`.
6. Sinh bảng tổng hợp bằng `scripts/summarize_results.py`.
7. Chạy `scripts/propose_next.py` để xem gợi ý.
8. Chỉ đổi một nhóm tham số cho lần nộp tiếp theo.

## Lệnh Thường Dùng

Liệt kê profile:

```powershell
python scripts/list_profiles.py
```

Sinh compose:

```powershell
python scripts/render_compose.py --config configs/submissions/v2_short_context.yaml --output docker-compose.yml
```

Ghi kết quả portal:

```powershell
python scripts/record_submission.py --profile v2_short_context --config configs/submissions/v2_short_context.yaml --status success --score <score> --notes "<ghi chú>"
```

Tổng hợp và gợi ý:

```powershell
python scripts/summarize_results.py
python scripts/propose_next.py
```

## Nguyên Tắc

- Không sửa tay `docker-compose.yml` nếu không có lý do rõ ràng.
- Không đổi nhiều flag cùng lúc.
- Mỗi profile phải có mục tiêu cụ thể.
- Mọi điểm số phải được ghi lại ngay sau khi portal trả kết quả.
- Khi điểm giảm, rollback về profile tốt nhất trước đó.


# Viettel AI Race LLM Harness

Repo này là harness phục vụ cuộc thi Viettel AI Race LLM vòng 1.

Team không có môi trường GPU giống hệ thống chấm, nên workflow chính là:

1. Sinh `docker-compose.yml` từ một profile cấu hình.
2. Nộp file đó lên portal cuộc thi.
3. Nhận điểm/log từ portal.
4. Ghi lại kết quả.
5. So sánh các lần nộp và chọn bước tối ưu nhỏ tiếp theo.

Các tài liệu nên đọc trước:

- [Đề bài cuộc thi](COMPETITION_BRIEF.md)
- [Hướng dẫn bản nộp V1](docs/V1_SUBMISSION_GUIDE.md)
- [Lý thuyết, config và kỹ thuật tối ưu](docs/THEORY_AND_TUNING_GUIDE.md)
- [Playbook tối ưu sau mỗi lần nộp](docs/OPTIMIZATION_PLAYBOOK.md)
- [Cách đọc kết quả portal](docs/PORTAL_RESULT_GUIDE.md)
- [Workflow thử nghiệm liên tục](experiments/README.md)
- [Phân tích sau V1](experiments/NEXT_STEPS.md)

Sinh bản nộp baseline:

```powershell
python scripts/render_compose.py --config configs/submissions/v1_baseline.yaml --output docker-compose.yml
```

Sau khi portal trả kết quả, ghi lại kết quả:

```powershell
python scripts/record_submission.py --profile v1_baseline --config configs/submissions/v1_baseline.yaml --status success --score 0 --notes "thay bằng kết quả/log thật từ portal"
python scripts/summarize_results.py
```

Xem các profile hiện có và gợi ý bước tiếp theo:

```powershell
python scripts/list_profiles.py
python scripts/propose_next.py
```

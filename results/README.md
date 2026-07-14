# Thư mục kết quả

Thư mục này dùng để lưu kết quả các lần nộp lên portal.

Sau mỗi lần portal trả điểm/log:

1. Chạy `scripts/record_submission.py` để append một bản ghi vào `submissions.jsonl`.
2. Chạy `scripts/summarize_results.py` để tạo lại `LEADERBOARD_NOTES.md`.

Không sửa tay `LEADERBOARD_NOTES.md` nếu không cần. File đó nên được sinh lại từ dữ liệu trong `submissions.jsonl`.


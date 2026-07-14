# Viettel AI Race LLM - Competition Brief

- **Vòng thi:** Vòng 1 - Sơ loại
- **Thời gian:** 02/07/2026 - 30/07/2026
- **Model mục tiêu:** `Qwen/Qwen3.5-2B`
- **Serving framework bắt buộc:** vLLM

## Đề bài và quy định

### 1. Tổng quan Phase 1

Đây là vòng thi mô phỏng trực tiếp thách thức mà các đội ngũ hạ tầng AI đang đối mặt: phục vụ LLM đáp ứng đồng thời thông lượng cao, độ trễ thấp, độ chính xác ổn định và hiệu quả trên tài nguyên GPU hữu hạn.

**Nhiệm vụ của thí sinh:** Triển khai và tối ưu một LLM inference server cho mô hình `Qwen/Qwen3.5-2B` xử lý một file trace gồm 120 requests mô phỏng traffic production. Mục tiêu là tối đa hóa tỷ lệ request được đáp ứng đúng hạn (**Effective Request Capacity**) trong khi vẫn phải vượt qua bài kiểm tra chất lượng đầu ra (**Accuracy Gate**).

**Hạ tầng và môi trường đánh giá:** Toàn bộ quá trình chạy benchmark được thực hiện tự động trên hệ thống của Ban tổ chức (BTC). Thí sinh sẽ serve endpoint trên 1 instance MiG và BTC sẽ thực hiện benchmark trực tiếp vào endpoint đó:

- **Hạ tầng phần cứng:** 1 instance MiG H200 (18GB VRAM, 3 Core CPU, 8GB RAM) được cấp phát tự động cho mỗi lượt chấm.
- **Hệ điều hành & Driver:** Ubuntu 22.04 LTS, CUDA 12.x.
- **Model:** `Qwen/Qwen3.5-2B` (Dense Transformer, gốc BF16).
- **Nguồn weights:** Tải từ HuggingFace Hub (mã hash cố định do BTC công bố).

### 2. Tiêu chí đánh giá và cách tính điểm

**Effective Request Score** được đánh giá dựa theo tốc độ trên 2 metrics TTFT và TPOT. Công thức cụ thể như sau:

$$
ERS = \frac{1}{N}\sum_{i=1}^{N} S_{\text{request},i} \in [0,1]
$$

với $N$ là tổng số request.

Trong đó:

$$
S_{\text{request}} =
\begin{cases}
0, & \text{if error, timeout, or 0 output tokens} \\
w \cdot s_{\text{ttft}} + (1-w)\cdot s_{\text{tpot}}, & \text{if request succeeds}
\end{cases}
$$

$$
s_{\text{ttft}}
=
(x_{\text{ttft}})^\gamma
=
\left[
\operatorname{clamp}
\left(
\frac{C_{\text{ttft}}-\text{TTFT}}
{C_{\text{ttft}}-F_{\text{ttft}}},
0,1
\right)
\right]^\gamma
$$

và

$$
s_{\text{tpot}}
=
(x_{\text{tpot}})^\gamma
=
\left[
\operatorname{clamp}
\left(
\frac{C_{\text{tpot}}-\text{TPOT}_{\text{mean}}}
{C_{\text{tpot}}-F_{\text{tpot}}},
0,1
\right)
\right]^\gamma
$$

### Tham số cấu hình

| Ký hiệu | Ý nghĩa | Giá trị |
|---|---|---:|
| $F_{\text{ttft}}$ | Floor của TTFT | 100 ms |
| $C_{\text{ttft}}$ | Ceiling của TTFT | 1500 ms |
| $F_{\text{tpot}}$ | Floor của TPOT | 20 ms |
| $C_{\text{tpot}}$ | Ceiling của TPOT | 45 ms |
| $\gamma$ | Hệ số lũy thừa | 2 |
| $w$ | Trọng số của TTFT | 0.5 |

### Accuracy Gate (GPQA Diamond)

Được đánh giá độc lập qua 100 câu hỏi cố định trích từ tập GPQA Diamond. Độ sụt giảm chất lượng $(\Delta)$ được tính bằng điểm phần trăm tuyệt đối so với reference baseline chạy bằng trọng số BF16 gốc (mặc định baseline đạt `0.4`).

$$
\Delta
=
\text{baseline\_accuracy}
-
\text{team\_gpqa\_accuracy}
$$

Trong đó, `baseline_accuracy` là điểm reference accuracy của mô hình gốc chạy bằng trọng số BF16.

Dựa trên độ sụt giảm $\Delta$, hệ thống áp dụng hàm phạt $f(\Delta)$ (**Accuracy decay function**) - một hàm bậc nhất từng đoạn (piecewise linear) với giá trị đầu ra thuộc đoạn $[0,1]$, quy định mức độ trừ điểm vào tổng điểm cuối cùng:

$$
f(\Delta)=
\begin{cases}
1.0, & \text{if } \Delta \le 0.1 \\
1.0-\dfrac{\Delta-0.10}{0.06}, & \text{if } 0.1 < \Delta < 0.16 \\
0.0, & \text{if } \Delta \ge 0.16
\end{cases}
$$

Điểm số cuối cùng của mỗi đội được tính bằng cách kết hợp điểm hiệu năng phục vụ (ERS) với hình phạt sụt giảm chất lượng (Accuracy drop):

$$
\text{Score} = 100 \times ERS \times f(\Delta)
$$

Trong đó:

- **ERS (Effective Request Score):** Điểm số trung bình đánh giá hiệu năng xử lý request trên toàn bộ trace (đã mô tả ở phần ERS).
- $f(\Delta)$: Hệ số phạt dựa trên mức sụt giảm độ chính xác.

### 3. Không gian tối ưu (Optimization Scope)

Thí sinh chỉ được phép sử dụng serving framework **vLLM** cho bài thi này. Các hướng tiếp cận bao gồm:

- **Quantization:** Các kỹ thuật Online Quantization.
- **KV Cache & Memory:** Tối đa hóa lượng request xử lý đồng thời bằng Paged Attention; KV cache quantization (FP8, INT8); Prefix caching và Semantic caching; Offloading xuống CPU/NVMe.
- **Serving & Scheduling:** Ứng dụng Dynamic/Continuous batching; Speculative decoding (với draft model hoặc self-speculative); Memory-aware scheduling.
- **System & Runtime:** Viết custom CUDA/Triton kernels; Tích hợp Fused attention kernels (FlashAttention, FlashInfer); Tối ưu hóa memory layout và CUDA Graphs.

### 4. Quy trình và quy chuẩn nộp bài (Submission)

#### Quy trình thực hiện (Workflow)

1. **Develop & Package:** Thí sinh phát triển code giải pháp, tối ưu hệ thống và đóng gói toàn bộ thành một Docker Image.
2. **Push Image:** Đẩy (Push) Docker Image hoàn chỉnh lên Docker Hub cá nhân hoặc tổ chức dưới dạng công khai (Public).
3. **Submit:** Thí sinh truy cập hệ thống Portal của BTC, gửi file cấu hình `docker-compose.yml` (trong đó có khai báo chính xác đường dẫn Image trên Docker Hub và lệnh thực thi).
4. **Automated Evaluation:** Hệ thống tự động pull Image từ Docker Hub về, dựng container trên 1 instance MiG H200 (18GB VRAM), kiểm tra trạng thái hoạt động (Healthcheck) và tiến hành chạy benchmark tự động.
5. **Leaderboard:** Kết quả và log trả về trong khoảng 15 phút; bảng xếp hạng tự động cập nhật.

**File trace cho phase 1 vòng online:** `trace-round1.jsonl`

**Docker image baseline:**

```text
https://hub.docker.com/layers/vllm/vllm-openai/v0.22.1/images/sha256-55c9bcee9fc66644b139fddae8a7a03e4c0c8a25ab5c64b0ce614554a8abf5d5
```

#### File `docker-compose.yml` mẫu

```yaml
services:
  model:
    image: vllm/vllm-openai:v0.22.1

    entrypoint:
      - python3 # Don't change this to vllm-server
      - -m # Don't change this to vllm-server
      - vllm.entrypoints.openai.api_server # Don't change this to vllm-server

    command:
      - --model=/model # Don't change this to vllm-server
      - --served-model-name=Qwen3.5-2B # Don't change this to vllm-server
      - --host=0.0.0.0 # Don't change this to vllm-server
      - --port=8000 # Don't change this to vllm-server
      - --max-model-len=262144
      - --gpu-memory-utilization=0.95
      - --tensor-parallel-size=1
      - --enable-prefix-caching

    ports:
      - "8000:8000"

    shm_size: "2g"

    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

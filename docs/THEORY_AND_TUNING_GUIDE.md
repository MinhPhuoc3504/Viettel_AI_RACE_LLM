# Lý Thuyết, Config Và Kỹ Thuật Tối Ưu LLM Serving

Tài liệu này là nền tảng kiến thức cho team khi làm Viettel AI Race LLM. Mục tiêu không phải học thuộc flag, mà là hiểu:

- mỗi config đang điều khiển phần nào của hệ thống;
- kỹ thuật tối ưu đó tác động vào TTFT, TBT/TPOT, memory hay accuracy;
- khi portal trả kết quả thì nên suy luận thế nào để chọn lần nộp tiếp theo.

## 1. Bài Toán Thực Chất Là Gì

Team không train model mới. Model đã cố định là `Qwen/Qwen3.5-2B`.

Việc của team là chạy model đó như một inference server:

```text
request từ benchmark -> vLLM server -> model sinh token -> trả response
```

BTC sẽ gửi 120 request vào endpoint của team. Điểm cao khi:

- server không crash;
- không OOM;
- không timeout;
- không trả 0 token;
- token đầu tiên ra nhanh;
- các token tiếp theo sinh nhanh;
- chất lượng output không tụt quá baseline.

Do team không có GPU local giống BTC, portal là nguồn benchmark thật duy nhất. Vì vậy chiến lược tối ưu phải là:

```text
nộp một config nhỏ -> nhận metric -> ghi lại -> suy luận bottleneck -> đổi một nhóm config -> nộp lại
```

## 2. Luồng Xử Lý Một Request LLM

Một request LLM thường đi qua các giai đoạn:

1. **Nhận request:** API server nhận prompt/messages.
2. **Tokenization:** chuyển text thành token id.
3. **Prefill:** model đọc toàn bộ input prompt để tạo trạng thái ban đầu.
4. **Decode:** model sinh từng output token.
5. **Trả response:** server stream hoặc trả toàn bộ kết quả.

Hai giai đoạn quan trọng nhất để tối ưu:

- **Prefill:** ảnh hưởng mạnh đến TTFT.
- **Decode:** ảnh hưởng mạnh đến TBT/TPOT.

Prompt càng dài thì prefill càng nặng. Output càng dài thì decode càng quan trọng.

## 3. TTFT, TBT Và TPOT

### TTFT

`TTFT` là `Time To First Token`: thời gian từ lúc request tới server đến khi token đầu tiên được sinh ra.

TTFT cao thường do:

- prompt dài;
- request bị xếp hàng chờ;
- prefill chậm;
- batching chưa hợp lý;
- `max_model_len` quá lớn làm memory/KV cache pressure cao;
- GPU memory quá căng, gây fragmentation hoặc scheduling kém.

Trong đề, TTFT tốt khi gần `100 ms`, và xấu dần tới khoảng `1500 ms`. Portal V1 trả `ttft_p95_ms=10571`, nghĩa là tail latency rất cao.

### TBT / TPOT

`TBT` thường hiểu là `Time Between Tokens`, gần với `TPOT` trong đề. Nó đo thời gian sinh các token sau token đầu tiên.

TBT/TPOT cao thường do:

- decode chậm;
- batch decode không hiệu quả;
- memory bandwidth bị nghẽn;
- KV cache lớn hoặc không tối ưu;
- attention kernel chưa tối ưu;
- GPU memory utilization chưa phù hợp.

Trong đề, TPOT tốt khi gần `20 ms`, và xấu dần tới `45 ms`. Portal V1 trả `tbt_median_ms=59`, nghĩa là decode đang chậm hơn ngưỡng tốt.

## 4. KV Cache Là Gì Và Vì Sao Rất Quan Trọng

LLM Transformer sinh token tự hồi quy. Khi sinh token thứ 100, model cần thông tin từ 99 token trước đó. Nếu tính lại toàn bộ từ đầu mỗi lần thì rất chậm.

`KV cache` lưu lại key/value của attention cho các token đã xử lý. Nhờ đó khi sinh token mới, model không phải tính lại mọi thứ.

KV cache giúp nhanh hơn nhưng tốn VRAM. Kích thước KV cache tăng theo:

- batch size;
- số request đang chạy đồng thời;
- độ dài prompt;
- số token output;
- `max_model_len`;
- số layer và hidden dimension của model;
- dtype của cache, ví dụ BF16/FP16/FP8.

Với MiG H200 18GB, KV cache là tài nguyên rất quan trọng. Nếu config dành quá nhiều VRAM cho context dài, server có thể:

- giảm concurrency;
- queue request lâu hơn;
- tăng TTFT p95;
- OOM;
- hoặc chạy được nhưng điểm thấp.

## 5. vLLM Làm Gì

vLLM là serving framework chuyên cho LLM inference. Trong cuộc thi này, thí sinh bắt buộc dùng vLLM.

vLLM giúp:

- chạy OpenAI-compatible API server;
- quản lý KV cache;
- batch nhiều request;
- schedule prefill/decode;
- dùng Paged Attention để quản lý memory hiệu quả hơn;
- tận dụng GPU tốt hơn so với code inference đơn giản.

Trong harness hiện tại, server được chạy bằng:

```yaml
entrypoint:
  - python3
  - -m
  - vllm.entrypoints.openai.api_server
```

Đây là cách start API server của vLLM theo mẫu BTC.

## 6. Giải Thích Từng Config Đang Dùng

Các profile nằm trong `configs/submissions/*.yaml`. Script `scripts/render_compose.py` đọc profile và sinh `docker-compose.yml`.

### `image`

Ví dụ:

```yaml
image: vllm/vllm-openai:v0.22.1
```

Đây là Docker image chứa vLLM server.

Tác dụng:

- quyết định version vLLM;
- quyết định các flag được hỗ trợ;
- quyết định CUDA/runtime/library bên trong container.

Rủi ro:

- đổi image có thể làm server không tương thích;
- version khác có thể đổi behavior hoặc flag;
- image custom có thể tối ưu tốt hơn nhưng tăng rủi ro build/deploy.

V1 giữ official image để giảm rủi ro.

### `model_path`

Ví dụ:

```yaml
model_path: /model
```

Khi render compose, nó thành:

```text
--model=/model
```

Đây là nơi vLLM load model weights. Theo mẫu đề, BTC có thể mount model vào `/model`.

Nếu BTC không mount `/model`, cần đổi sang HuggingFace model id hoặc path đúng theo hướng dẫn portal.

### `served_model_name`

Ví dụ:

```yaml
served_model_name: Qwen3.5-2B
```

Khi render compose:

```text
--served-model-name=Qwen3.5-2B
```

Đây là tên model mà OpenAI-compatible API expose ra. Benchmark có thể gọi đúng model name này.

Không nên đổi tùy tiện nếu đề/mẫu đã yêu cầu tên này.

### `host`

```yaml
host: 0.0.0.0
```

`0.0.0.0` nghĩa là server lắng nghe trên mọi network interface trong container.

Nếu đặt `127.0.0.1`, hệ thống bên ngoài container có thể không gọi được endpoint. Vì vậy phải dùng `0.0.0.0`.

### `port`

```yaml
port: 8000
```

Server mở port `8000`. Compose map:

```yaml
ports:
  - "8000:8000"
```

BTC sẽ gọi endpoint trên port này. Không nên đổi nếu portal mặc định gọi `8000`.

### `max_model_len`

Ví dụ:

```yaml
max_model_len: 32768
```

Khi render:

```text
--max-model-len=32768
```

Đây là độ dài context tối đa mà server cho phép. Nó ảnh hưởng rất mạnh tới memory và latency.

Tăng `max_model_len`:

- nhận được prompt dài hơn;
- giảm nguy cơ context length reject;
- nhưng tăng KV cache pressure;
- có thể giảm concurrency;
- có thể tăng TTFT/TBT;
- có thể OOM.

Giảm `max_model_len`:

- giảm áp lực KV cache;
- có thể cải thiện TTFT/TBT;
- tăng khả năng xử lý đồng thời;
- nhưng có thể reject request prompt dài.

Diễn giải các profile hiện tại:

| Profile | `max_model_len` | Ý nghĩa |
|---|---:|---|
| `v1_long_context` | 65536 | Dùng nếu bị reject vì context dài |
| `v1_baseline` | 32768 | Baseline cân bằng |
| `v2_short_context` | 16384 | Thử giảm pressure để cải thiện latency |
| `v2_more_conservative_context` | 8192 | Thử giảm mạnh nếu chắc trace không quá dài |

Với kết quả V1 `ttft_p95_ms=10571` và `tbt_median_ms=59`, thử giảm `max_model_len` là hợp lý vì run không fail nhưng tail latency rất xấu.

### `gpu_memory_utilization`

Ví dụ:

```yaml
gpu_memory_utilization: 0.90
```

Khi render:

```text
--gpu-memory-utilization=0.90
```

Đây là tỷ lệ VRAM vLLM được phép dùng.

Tăng giá trị này:

- vLLM có thêm memory cho KV cache;
- có thể xử lý batch/concurrency tốt hơn;
- có thể giảm queueing;
- nhưng tăng rủi ro OOM hoặc fragmentation.

Giảm giá trị này:

- an toàn hơn;
- giảm rủi ro OOM;
- nhưng có thể ít KV cache hơn, throughput thấp hơn.

Diễn giải các profile hiện tại:

| Profile | `gpu_memory_utilization` | Ý nghĩa |
|---|---:|---|
| `v1_safe_memory` | 0.85 | Fallback khi crash/OOM |
| `v1_baseline` | 0.90 | Điểm khởi đầu ổn định |
| `v1_high_memory` | 0.92 | Tăng nhẹ sau khi baseline ổn |
| `v2_high_memory` | 0.94 | Thử aggressive hơn nếu vẫn không OOM |

Vì V1 `failed_count=0`, team có thể thử tăng memory sau khi thử giảm context. Nhưng không nên vừa giảm context vừa tăng memory trong cùng một lần nếu muốn biết nguyên nhân điểm thay đổi.

### `tensor_parallel_size`

```yaml
tensor_parallel_size: 1
```

Khi render:

```text
--tensor-parallel-size=1
```

Tensor parallel chia model qua nhiều GPU. Đề cho 1 MiG instance, nên đặt `1`.

Nếu đặt lớn hơn số GPU thực tế, server có thể fail.

### `enable_prefix_caching`

```yaml
enable_prefix_caching: true
```

Khi render:

```text
--enable-prefix-caching
```

Prefix caching giúp reuse phần prefix giống nhau giữa nhiều request.

Tác dụng:

- giảm prefill nếu nhiều prompt có phần đầu giống nhau;
- cải thiện TTFT;
- đặc biệt hữu ích nếu benchmark có template/system prompt lặp.

Rủi ro:

- tốn thêm logic/cache management;
- nếu request không có prefix chung, lợi ích ít;
- thường khá an toàn vì không đổi output.

V1 bật prefix caching vì đây là tối ưu ít rủi ro accuracy.

### `shm_size`

```yaml
shm_size: 2g
```

Đây là shared memory cho container.

Tác dụng:

- giúp các thư viện multiprocessing/PyTorch tránh thiếu shared memory;
- giảm rủi ro lỗi runtime kỳ lạ.

Không phải flag trực tiếp cải thiện điểm, nhưng giúp container ổn định.

## 7. Giải Thích Từng Profile Submission

### `v1_baseline`

Mục tiêu: có bản nộp hợp lệ đầu tiên.

Config chính:

```yaml
max_model_len: 32768
gpu_memory_utilization: 0.90
enable_prefix_caching: true
```

Kết quả V1:

| Metric | Giá trị |
|---|---:|
| final_score | 12.89 |
| erc | 0.691667 |
| passed_slo | 83/120 |
| failed_count | 0 |
| penalty | 1 |
| ttft_p50_ms | 888 |
| ttft_p95_ms | 10571 |
| tbt_median_ms | 59 |

Kết luận:

- ổn định;
- không bị penalty;
- không fail;
- nhưng latency cao.

### `v1_safe_memory`

Mục tiêu: fallback khi baseline OOM/crash/fail healthcheck.

```yaml
max_model_len: 16384
gpu_memory_utilization: 0.85
```

Tác dụng:

- giảm áp lực VRAM;
- tăng xác suất server start và chạy hết benchmark.

Khi dùng:

- portal báo OOM;
- server crash;
- healthcheck failed;
- nhiều request fail do runtime.

Không nên dùng nếu baseline đã ổn và chỉ cần tăng điểm, vì quá conservative có thể làm throughput kém.

### `v1_high_memory`

Mục tiêu: tăng nhẹ memory nếu baseline ổn nhưng điểm latency yếu.

```yaml
max_model_len: 32768
gpu_memory_utilization: 0.92
```

Tác dụng:

- thêm không gian cho KV cache;
- có thể cải thiện batching/concurrency.

Rủi ro:

- tăng khả năng OOM;
- nếu memory đã đủ, điểm có thể không cải thiện.

### `v1_long_context`

Mục tiêu: xử lý trace có prompt dài hơn baseline.

```yaml
max_model_len: 65536
gpu_memory_utilization: 0.90
```

Khi dùng:

- portal log báo context length exceeded;
- request bị reject do prompt dài.

Rủi ro:

- tăng KV cache pressure;
- có thể làm TTFT/TBT xấu hơn;
- có thể giảm concurrency.

### `v2_short_context`

Mục tiêu: giảm latency sau V1.

```yaml
max_model_len: 16384
gpu_memory_utilization: 0.90
```

Lý do:

- V1 không fail nhưng TTFT p95 và TBT cao;
- giảm context có thể giảm pressure và cải thiện scheduler/cache.

Đây là profile được gợi ý tiếp theo.

### `v2_high_memory`

Mục tiêu: cải thiện latency bằng cách cho vLLM dùng nhiều VRAM hơn.

```yaml
max_model_len: 32768
gpu_memory_utilization: 0.94
```

Khi dùng:

- run ổn định;
- không penalty;
- TBT cao;
- không thấy OOM.

Rủi ro:

- nếu quá sát giới hạn VRAM, có thể OOM hoặc tail latency tệ hơn.

### `v2_more_conservative_context`

Mục tiêu: thử giảm context mạnh để xem latency có cải thiện rõ không.

```yaml
max_model_len: 8192
gpu_memory_utilization: 0.90
```

Khi dùng:

- đã thử `v2_short_context`;
- không thấy context reject;
- muốn kiểm tra giả thuyết “context quá lớn làm latency cao”.

Rủi ro:

- nếu trace có prompt dài, nhiều request sẽ fail/reject.

## 8. Các Kỹ Thuật Tối Ưu Trong Đề

### Continuous Batching

Batching là gom nhiều request chạy cùng nhau trên GPU.

Batching thường trong deep learning truyền thống là chờ đủ batch rồi chạy. LLM serving phức tạp hơn vì request đến không đều và độ dài output khác nhau.

`Continuous batching` cho phép vLLM liên tục thêm request mới vào batch đang chạy khi có slot trống.

Tác dụng:

- tăng GPU utilization;
- giảm idle time;
- tăng throughput;
- có thể giảm TPOT/TBT nếu batch được tổ chức tốt.

Rủi ro:

- batch quá lớn có thể làm từng request chờ lâu hơn;
- TTFT có thể xấu nếu queueing tăng.

Team hiện chưa trực tiếp tune batching flag. Sau khi có vài kết quả, có thể nghiên cứu các flag liên quan scheduler/batched tokens nếu image hỗ trợ.

### Paged Attention

Paged Attention là kỹ thuật quản lý KV cache theo kiểu page/block thay vì cấp phát một vùng liên tục lớn.

Tác dụng:

- giảm fragmentation;
- tận dụng VRAM tốt hơn;
- giúp nhiều request có độ dài khác nhau chạy hiệu quả hơn.

Đây là một trong các lý do vLLM nhanh và phù hợp với serving.

Team không cần tự bật Paged Attention bằng config riêng trong V1; đây là cơ chế cốt lõi của vLLM.

### Prefix Caching

Prefix caching lưu lại phần tính toán của prefix prompt giống nhau.

Ví dụ nhiều request có cùng system prompt:

```text
Bạn là trợ lý AI...
Question: ...
```

Phần “Bạn là trợ lý AI...” có thể được reuse.

Tác dụng:

- giảm prefill;
- giảm TTFT;
- không ảnh hưởng accuracy nếu cache đúng.

Khi hiệu quả:

- trace có prompt template lặp;
- nhiều câu hỏi dùng chung instruction/system prompt.

Khi ít hiệu quả:

- mọi prompt hoàn toàn khác nhau;
- prefix quá ngắn.

### Semantic Caching

Semantic caching là cache theo ý nghĩa gần giống, không chỉ prefix giống hệt.

Ví dụ hai câu hỏi khác chữ nhưng cùng ý nghĩa có thể reuse response hoặc intermediate result.

Tác dụng tiềm năng:

- giảm số lần gọi model;
- giảm latency mạnh nếu cache hit.

Rủi ro trong cuộc thi:

- dễ trả lời sai nếu cache match nhầm;
- có thể ảnh hưởng accuracy;
- khó dùng nếu không kiểm soát được trace;
- cần proxy/service riêng phức tạp hơn.

V1 không dùng semantic caching.

### KV Cache Quantization

KV cache quantization lưu KV cache bằng dtype nhỏ hơn, ví dụ FP8/INT8 thay vì BF16/FP16.

Tác dụng:

- giảm VRAM dùng cho KV cache;
- tăng context/concurrency có thể xử lý;
- có thể cải thiện throughput nếu memory bandwidth là bottleneck.

Rủi ro:

- có thể ảnh hưởng chất lượng output;
- tùy model/version vLLM/GPU có hỗ trợ ổn không;
- nếu implementation chưa ổn định có thể crash hoặc sai output.

Khi nên thử:

- baseline đã ổn;
- điểm bị giới hạn bởi memory/KV cache;
- còn đủ lượt nộp để rollback nếu penalty tăng.

### Weight Quantization

Weight quantization giảm precision của trọng số model, ví dụ BF16 xuống INT8/FP8/AWQ/GPTQ.

Tác dụng:

- giảm VRAM chứa weights;
- có thể tăng tốc inference;
- cho phép nhiều memory hơn cho KV cache.

Rủi ro:

- có thể giảm accuracy GPQA;
- cần image/model format phù hợp;
- có thể làm output khác baseline.

Vì đề có Accuracy Gate, không nên thử weight quantization quá sớm.

### Speculative Decoding

Speculative decoding dùng một draft model nhỏ hoặc cơ chế self-speculative để đoán trước nhiều token, sau đó model chính verify.

Tác dụng:

- giảm thời gian decode;
- có thể cải thiện TBT/TPOT nếu draft nhanh và acceptance rate cao.

Rủi ro:

- cần draft model tương thích;
- cấu hình phức tạp;
- có thể không hỗ trợ tốt trong image hiện tại;
- nếu setup sai có thể không nhanh hơn hoặc fail.

Chỉ nên thử sau khi baseline và các tuning memory/context đã rõ.

### FlashAttention / FlashInfer / Fused Attention Kernels

Attention kernel là phần tính attention trên GPU. Kernel tốt giúp giảm thời gian compute và memory movement.

Tác dụng:

- tăng tốc prefill/decode;
- giảm memory overhead;
- cải thiện TTFT/TBT.

Rủi ro:

- phụ thuộc GPU, CUDA, version vLLM;
- tự tích hợp kernel custom là việc khó;
- image official thường đã có lựa chọn kernel hợp lý.

Ở giai đoạn đầu, team nên dùng kernel mặc định của vLLM image.

### CUDA Graphs

CUDA Graphs ghi lại một chuỗi CUDA operations rồi replay để giảm overhead launch kernel.

Tác dụng:

- giảm overhead CPU/GPU launch;
- tốt cho workload có shape lặp lại.

Rủi ro:

- shape động của LLM serving phức tạp;
- tùy framework tự quản lý;
- không phải thứ nên tự can thiệp sớm.

### CPU/NVMe Offload

Offload chuyển một phần dữ liệu từ GPU xuống CPU/NVMe khi thiếu VRAM.

Tác dụng:

- tránh OOM;
- cho phép model/context lớn hơn chạy được.

Rủi ro:

- CPU/NVMe chậm hơn VRAM rất nhiều;
- latency thường xấu;
- cuộc thi phạt latency mạnh nên offload không phải lựa chọn đầu tiên.

Chỉ dùng nếu không còn cách nào để server chạy.

### Memory-Aware Scheduling

Scheduler quyết định request nào được chạy, batch nào được ghép, khi nào prefill/decode.

Memory-aware scheduling nghĩa là scheduler cân nhắc memory còn lại để tránh OOM và giảm queueing.

Tác dụng:

- giảm crash/OOM;
- cải thiện tail latency;
- tăng số request thành công.

Trong vLLM, nhiều logic scheduling đã có sẵn. Team có thể tác động gián tiếp qua:

- `max_model_len`;
- memory utilization;
- các flag batching nếu sau này thêm.

## 9. Giải Thích Các Tham Số Kết Quả Portal

### `final_score`

Điểm cuối cùng để so sánh leaderboard.

Nếu `final_score` tăng, đó là tín hiệu tốt. Nhưng phải xem vì sao tăng để biết có ổn định không.

### `score`

Trong harness, `score` là điểm tổng lưu lại. Hiện team lưu bằng `final_score`.

### `erc`

Portal hiển thị `erc=0.691667` ở V1.

Có thể hiểu là capacity/score hiệu quả dạng tỷ lệ. Giá trị cao hơn là tốt hơn. Với V1, `passed_slo=83/120`, tỷ lệ này gần:

```text
83 / 120 = 0.691666...
```

Vì vậy trong kết quả hiện tại, `erc` phản ánh tỷ lệ request đạt SLO.

### `ers`

Portal V1 hiển thị `ers=12.89`, trùng với `final_score=12.89`.

Trong đề, ERS là điểm hiệu năng request trước khi nhân 100 và penalty. Portal có thể hiển thị theo scale khác. Harness lưu raw đúng như portal trả về, không tự diễn giải lại.

### `penalty`

Hệ số phạt accuracy. V1 có:

```text
penalty = 1
```

Nghĩa là không bị phạt. Nếu `penalty < 1`, cần ưu tiên xem lại những thay đổi có thể ảnh hưởng output.

### `accuracy_drop`

V1 portal trả:

```text
accuracy_drop = 1
```

Tên này hơi dễ gây hiểu nhầm vì trong đề `accuracy_drop` thường là độ tụt accuracy, còn portal có thể hiển thị raw theo scale riêng. Harness lưu nguyên giá trị portal. Khi phân tích, ưu tiên nhìn `penalty`; nếu `penalty=1` thì chưa bị phạt accuracy.

### `passed_slo`

Số request đạt SLO. V1:

```text
passed_slo = 83
total_count = 120
```

Nghĩa là 83 request đạt yêu cầu, 37 request chưa đạt.

Muốn tăng điểm, cần tăng `passed_slo`, nhưng không được làm tăng fail hoặc penalty.

### `total_count`

Tổng số request trong benchmark. V1 là `120`.

### `failed_count`

Số request lỗi. V1:

```text
failed_count = 0
```

Đây là tín hiệu tốt: server không fail request.

Nếu `failed_count > 0`, ưu tiên sửa stability trước khi tối ưu tốc độ.

### `warmup_count`

Số request warmup nếu portal có chạy warmup. V1 là `0`.

Warmup thường không tính điểm hoặc dùng để làm nóng hệ thống. Với V1 không có warmup.

### `ttft_p50_ms`

Median TTFT. V1:

```text
ttft_p50_ms = 888
```

Request điển hình mất 888 ms để có token đầu tiên. So với floor 100 ms và ceiling 1500 ms trong đề, p50 này chưa quá tệ nhưng vẫn còn xa mức tốt.

### `ttft_p95_ms`

95th percentile TTFT. V1:

```text
ttft_p95_ms = 10571
```

Đây là vấn đề lớn. Một nhóm request chậm nhất mất hơn 10 giây mới có token đầu tiên.

Nguyên nhân khả dĩ:

- queueing quá lâu;
- prompt/context dài;
- prefill bị nghẽn;
- memory pressure;
- batch scheduling không tốt;
- `max_model_len` quá lớn so với nhu cầu thật.

Hướng thử:

- giảm `max_model_len`;
- nếu không OOM và TBT cao, thử tăng memory utilization;
- sau này mới tune batching.

### `tbt_median_ms`

Median time-between-tokens. V1:

```text
tbt_median_ms = 59
```

Trong đề, TPOT tốt quanh 20 ms và xấu dần tới 45 ms. `59 ms` là cao, nghĩa là decode chưa tốt.

Hướng thử:

- giảm context/memory pressure;
- tăng memory utilization nếu run ổn;
- sau này xem xét KV cache dtype hoặc decode-related tuning.

## 10. Cách Suy Luận Đổi Config Từ Kết Quả

### Trường hợp 1: `failed_count > 0`

Ưu tiên stability.

Hành động:

- dùng `v1_safe_memory`;
- giảm `gpu_memory_utilization`;
- giảm `max_model_len`;
- không thêm kỹ thuật mới.

### Trường hợp 2: `penalty < 1`

Ưu tiên accuracy.

Hành động:

- rollback quantization/speculative/sampling change;
- quay về profile gần nhất không bị penalty;
- không tối ưu tốc độ bằng cách làm output khác đi.

### Trường hợp 3: `ttft_p95_ms` cao, `failed_count=0`

Tail latency xấu nhưng server ổn.

Hành động:

- thử `v2_short_context`;
- nếu không context reject, có thể thử `v2_more_conservative_context`;
- nếu context reject, quay lại context cao hơn.

### Trường hợp 4: `tbt_median_ms` cao, server ổn

Decode chậm.

Hành động:

- thử tăng nhẹ `gpu_memory_utilization`;
- sau đó mới nghĩ đến KV cache dtype hoặc speculative decoding;
- không bật nhiều kỹ thuật cùng lúc.

### Trường hợp 5: `passed_slo` tăng nhưng score không tăng

Kiểm tra:

- penalty có giảm không;
- p95 có tệ hơn không;
- fail có tăng không;
- score portal có scale khác không.

Không chỉ nhìn một metric đơn lẻ.

## 11. Quy Trình Tối Ưu Khuyến Nghị Cho Team

Mỗi lần nộp phải có giả thuyết.

Ví dụ:

```text
Giả thuyết: max_model_len=32768 đang gây KV cache pressure, làm TTFT p95 cao.
Thử nghiệm: dùng v2_short_context với max_model_len=16384, giữ các flag khác.
Kỳ vọng: ttft_p95_ms giảm, tbt_median_ms giảm hoặc không tăng, failed_count vẫn 0.
Rollback: nếu context reject hoặc passed_slo giảm mạnh, quay về v1_baseline.
```

Sau mỗi lần portal trả kết quả:

1. Ghi lại bằng `scripts/record_submission.py`.
2. Chạy `scripts/summarize_results.py`.
3. Chạy `scripts/propose_next.py`.
4. Đọc `results/LEADERBOARD_NOTES.md`.
5. Chọn đúng một thay đổi cho lần tiếp theo.

## 12. Lộ Trình Tối Ưu Sau V1

Thứ tự khuyến nghị:

1. `v2_short_context`: giảm `max_model_len` từ 32768 xuống 16384.
2. Nếu không context reject và điểm tăng: cân nhắc `v2_more_conservative_context`.
3. Nếu run ổn nhưng TBT vẫn cao: thử `v2_high_memory`.
4. Nếu có OOM/crash: dùng `v1_safe_memory`.
5. Nếu latency vẫn kém sau context/memory tuning: nghiên cứu batching-related flags.
6. Nếu memory rõ ràng là bottleneck: nghiên cứu KV cache quantization.
7. Nếu decode là bottleneck chính: nghiên cứu speculative decoding.
8. Chỉ thử weight quantization khi có đủ lượt nộp và chấp nhận rủi ro accuracy.

## 13. Checklist Khi Tạo Profile Mới

Mỗi profile mới nên trả lời được:

- Profile này đang kiểm tra giả thuyết gì?
- Nó đổi flag nào so với baseline?
- Nó kỳ vọng cải thiện metric nào?
- Rủi ro là gì?
- Khi nào rollback?

Ví dụ tên profile tốt:

- `v3_kv_cache_fp8`
- `v3_batch_tokens_8192`
- `v4_spec_decode_small_draft`

Tên profile không tốt:

- `test1`
- `new`
- `fast`
- `fix`

## 14. Nguyên Tắc Quan Trọng Nhất

Không tối ưu theo cảm giác. Hãy tối ưu theo metric.

Với mỗi kết quả portal, hỏi theo thứ tự:

1. Server có fail không?
2. Có bị penalty accuracy không?
3. TTFT p50/p95 đang thế nào?
4. TBT/TPOT đang thế nào?
5. Passed SLO tăng hay giảm?
6. Thay đổi lần này có đúng giả thuyết không?

Nếu không trả lời được câu 6, lần nộp đó không giúp team học được gì.


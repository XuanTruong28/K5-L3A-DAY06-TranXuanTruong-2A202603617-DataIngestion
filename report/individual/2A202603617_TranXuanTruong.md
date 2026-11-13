# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - Chủ đề: Đa dạng thực vật biển và ứng dụng công nghiệp rong biển (Marine Plants & Seaweed Industry).
  - Nguồn tài liệu: Sách *A guide to the seaweed industry* (FAO Fisheries Technical Paper No. 441, Dennis J. McHugh). Nguồn chính thức: UN FAO Knowledge Repository (`https://www.fao.org/3/y4765e/y4765e.pdf`).
  - Bản quyền: Ấn phẩm giáo dục/nghiên cứu mở công khai của FAO (Public Domain / Open Access FAO).
  - Quy tắc tính trang: Tổng 118 trang vật lý; loại bỏ 12 trang bìa và mục lục sơ khởi; tính 101 trang nội dung khoa học thực tế (từ trang vật lý 13 đến 118). Mỗi trang chuẩn hóa chứa 800 – 4.500 ký tự.
- **Chuẩn hóa, lỗi và giới hạn:**
  - Chuẩn hóa Unicode NFKC, chuẩn hóa ngắt dòng `\n`, loại bỏ khoảng trắng thừa, xóa các dòng header lặp lại của sách; giữ nguyên cấu trúc phân đoạn tự nhiên (`\n\n`).
  - Không có trang nào bị lỗi OCR do file PDF số hóa nguyên bản 100%.
- **Embedding model & Vector store:**
  - Embedding Model: `SentenceTransformer('all-MiniLM-L6-v2')`, 384 chiều, chạy local CPU.
  - Vector Store: `ChromaDB` (v1.5.9), lưu tại`starter/results/chroma/chroma.sqlite3` (~14.4 MB), metric Cosine Similarity.
  - Lệnh chạy: `python -m starter.src.run`. Chi phí API: 0 USD.
- **Metadata bắt buộc và trường lọc:**
  - Metadata bắt buộc: `document_id`, `source`, `page`.
  - Trường lọc bổ sung: `chapter` (Tên chương) và `category` (Overview, Agar, Alginate, Carrageenan, Food).
  - Lý do chọn: Cuốn sách phân định rất rõ các họ loài rong và nhóm sản phẩm theo chương mục; trường `chapter` giúp loại bỏ nhầm lẫn giữa các loài thuộc các chương khác nhau khi truy xuất.

## Cấu hình và benchmark
- **3 Cấu hình (A / B / C):**
  - Cấu hình A: Cắt cố định `fixed_size` (kích thước 500 ký tự, overlap 50 ký tự), không dùng bộ lọc metadata.
  - Cấu hình B: Cắt theo đoạn văn logic `by_paragraph` (tối đa 800 ký tự, ngắt theo câu), không dùng bộ lọc metadata.
  - Cấu hình C: Cắt theo đoạn văn `by_paragraph` giống B, CÓ áp dụng bộ lọc metadata (`where={"chapter": ...}`) khi câu hỏi có trường filter.
  - Khác biệt duy nhất B–C: B không lọc (tìm toàn bộ corpus), C lọc theo `chapter` khi có yêu cầu. Cùng corpus, cùng model, cùng vector store.
- **Bộ Benchmark (20 câu hỏi):**
  - Tách trước: 15 câu `dev` / 5 câu `test`.
  - Phân bố dạng câu: 11 câu trực tiếp, 3 câu diễn đạt lại, 3 câu điều kiện/ngoại lệ, 3 câu kiểm tra metadata filter (`q03`, `q08` thuộc dev; `q17` thuộc test).
  - Kiểm chứng: 100% đoạn trích `evidence_quote` đều tồn tại nguyên văn trên đúng số trang `gold_page` của PDF.
- **Tiêu chí chọn chiến lược trước khi xem test:** Ưu tiên Evidence Hit@3 cao nhất, sau đó đến Grounding Quality và Chunk Coherence; tài nguyên lưu trữ và thời gian tính toán là tiêu chí phụ.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| **Strategy A** *(Fixed 500)* | dev | 4/15 (26.67%) | 7/15 (46.67%) | 690 | ~4.2s | $0 |
| | test | 3/5 (60.00%) | 3/5 (60.00%) | 690 | ~1.4s | $0 |
| | **overall** | **7/20 (35.00%)** | **10/20 (50.00%)** | **690** | **~5.6s** | **$0** |
| **Strategy B** *(Paragraph 800)*| dev | 4/15 (26.67%) | 10/15 (66.67%) | 436 | ~2.8s | $0 |
| | test | 3/5 (60.00%) | 4/5 (80.00%) | 436 | ~1.1s | $0 |
| | **overall** | **7/20 (35.00%)** | **14/20 (70.00%)** | **436** | **~3.9s** | **$0** |
| **Strategy C** *(Paragraph + Filter)*| dev | 5/15 (33.33%) | 10/15 (66.67%) | 436 | ~2.9s | $0 |
| | test | 3/5 (60.00%) | 5/5 (100.00%) | 436 | ~1.1s | $0 |
| | **overall** | **8/20 (40.00%)** | **15/20 (75.00%)** | **436** | **~4.0s** | **$0** |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| **Strategy A** | 0.90 / 2 (n=10) | 15/15 (100%) | N/A (không dùng filter) | 0: 2 câu, 1: 0 câu, 2: 3 câu -> **1.20 / 2** |
| **Strategy B** | 1.90 / 2 (n=10) | 15/15 (100%) | N/A (không dùng filter) | 0: 1 câu, 1: 0 câu, 2: 4 câu -> **1.60 / 2** |
| **Strategy C** | 1.90 / 2 (n=10) | 15/15 (100%) | 3/3 (100%) | 0: 0 câu, 1: 0 câu, 2: 5 câu -> **2.00 / 2** |

- **Đường dẫn minh chứng:**
  - File trace top-3: `starter/results/traces.json`.
  - Nhật ký thí nghiệm: `artifacts/experiment_log.csv`.
  - Mẫu Coherence: Chọn 10 vị trí trang cố định (p.13, 14, 21, 23, 29, 39, 42, 63, 75, 85).
  - Mẫu Grounding: Đánh giá trên 5 câu test độc lập (`q16` đến `q20`).

## Phân tích và kết luận
- **So sánh A–B (Tác động của Chunking):**
  - Chuyển từ cắt cố định 500 ký tự (A) sang cắt theo đoạn văn 800 ký tự (B) giúp Evidence Hit@3 tăng từ 50% lên 70% (+20%).
  - Chunk Coherence tăng vọt từ 0.90 lên 1.90/2 do không còn hiện tượng câu văn bị xé đôi giữa chừng.
  - Số lượng chunk giảm từ 690 xuống 436 (tiết kiệm 36.8% bộ nhớ và thời gian nhúng vector).
- **So sánh B–C (Tác động của Metadata Filter):**
  - Cấu hình B và C có cùng cấu trúc chunk. Khi thêm bộ lọc `chapter`, Hit@3 trên tập test tăng từ 80% lên 100% (5/5 câu), Hit@1 tăng từ 35% lên 40%.
  - Điểm Grounding đạt **2.0/2 tuyệt đối** trên tập test.
- **Hai ví dụ lỗi cụ thể từ trace:**
  1. *Lỗi lẫn lộn ngữ cảnh ngoài chương (Câu q17 - test):* Hỏi về việc thu hoạch chi *Pterocladia* trong Chương 2 (trang 21). Ở Cấu hình B (không filter), top-3 trả về các trang 28, 18, 47 (trang 47 thuộc Chương 5 về Alginate do có từ "harvesting"). Ở Cấu hình C, nhờ có filter `Chapter 2`, các trang ngoài chương bị chặn hoàn toàn, hệ thống truy xuất chính xác trang 21 vào top-3.
  2. *Lỗi cắt đứt câu từ (Câu q01 - dev):* Hỏi về 3 nhóm sắc tố rong biển ở trang 13. Cấu hình A cắt ngang chữ *"Chlorophyceae, respec-"* ở cuối chunk, khiến mô hình embedding không nhận diện trọn vẹn ngữ nghĩa ở top-1 (Hit@1=0). Trong khi Cấu hình B giữ trọn cả đoạn và đạt Hit@1=1.
- **Chiến lược được chọn & Đánh đổi:**
  - *Chọn Chiến lược C*. Lý do: Đạt Hit@3 cao nhất (75% overall, 100% test), Grounding tuyệt đối 2.0/2, Coherence 1.9/2 và số lượng chunk gọn nhất (436 chunks).
  - *Đánh đổi:* Cần đầu tư công sức trích xuất và chuẩn hóa trường metadata `chapter` ở khâu ingestion, và câu hỏi truy vấn cần mang thông tin ngữ cảnh để kích hoạt bộ lọc.
- **Hạn chế:**
  - Tập test gồm 5 câu là kích thước mẫu nhỏ theo yêu cầu thời gian buổi lab; khi triển khai thực tế cần mở rộng lên 50–100 câu test để độ tin cậy thống kê cao hơn.
  - Mô hình embedding `all-MiniLM-L6-v2` tối ưu cho tiếng Anh, nếu mở rộng sang tài liệu tiếng Việt cần đổi sang model đa ngữ (`paraphrase-multilingual-MiniLM-L12-v2`).
- **Hướng cải tiến mở rộng:**
  - Thử nghiệm Hybrid Retrieval (kết hợp Dense Embedding với từ khóa BM25) để bắt chính xác hơn các tên loài khoa học hiếm gặp.
  - Áp dụng kỹ thuật Parent-Document Retriever (tìm kiếm trên các chunk nhỏ nhưng trả về đoạn văn lớn hơn cho LLM) để tăng cường tối đa tính liên tục của ngữ cảnh.

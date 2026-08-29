# Báo cáo sự cố — Data Reliability Game Day

## Phạm vi

Ba lỗi có kiểm soát đã được đưa vào hệ thống và điều tra bằng kết quả kiểm tra
contract, dbt tests, tín hiệu anomaly, phép tính SLO và lineage. Trạng thái
healthy cuối cùng được xác minh bằng public test suite và dbt build.

## Sự cố 1 — Trùng khóa đơn hàng

### Mức độ nghiêm trọng

Critical

### Phát hiện và nguyên nhân gốc

Batch orders có 603 dòng thay vì 600 dòng. Orders contract phát hiện một check
`unique(order_id)` bị lỗi với severity critical. Nguyên nhân gốc là các bản ghi
đơn hàng bị đưa vào batch nhiều hơn một lần.

### Phạm vi ảnh hưởng

```text
raw_orders -> stg_orders -> fct_daily_revenue -> ceo_revenue_dashboard
```

### Giảm thiểu và khôi phục

Block hoặc quarantine batch lỗi, loại bỏ các order ID trùng, nạp lại seed và
chạy lại contract cùng dbt tests. Khôi phục được xác nhận khi unique check,
dbt unique test và output revenue downstream đều healthy.

## Sự cố 2 — Nạp thiếu dữ liệu orders

### Mức độ nghiêm trọng

Warning / ảnh hưởng vận hành cao

### Phát hiện và nguyên nhân gốc

Batch chỉ có 150 dòng, tương đương 25% so với 600 dòng kỳ vọng. Các contract
checks vẫn pass, chứng minh rằng schema hợp lệ không đồng nghĩa với việc dữ
liệu được nạp đầy đủ. Row-count anomaly detector trả về `is_anomaly=true` với
điểm auto/MAD khoảng 5.53. Nguyên nhân gốc là quá trình ingestion bị thiếu một
phần.

### Phạm vi ảnh hưởng

```text
raw_orders -> stg_orders -> fct_daily_revenue -> ceo_revenue_dashboard
```

### Giảm thiểu và khôi phục

Dừng publish revenue mart, chạy lại ingestion cho khoảng thời gian bị thiếu và
chạy lại anomaly, dbt cũng như các kiểm tra output downstream.

## Sự cố 3 — Knowledge base bị cũ

### Mức độ nghiêm trọng

Warning với ảnh hưởng tới người dùng

### Phát hiện và nguyên nhân gốc

KB contract phát hiện một freshness check bị lỗi: timestamp `published_at` mới
nhất đã cũ khoảng 190 phút, trong khi giới hạn cho phép là 60 phút. Tín hiệu
text-length không phát hiện được sự cố này, cho thấy freshness cần được theo
dõi như một SLI riêng. Nguyên nhân gốc là quá trình publish hoặc refresh index
bị trễ.

### Phạm vi ảnh hưởng

```text
kb_documents -> kb_active_docs -> rag_index -> support_agent
```

### Giảm thiểu và khôi phục

Tạm dừng KB indexing hoặc rollback về phiên bản được phê duyệt gần nhất còn
fresh. Refresh lại documents và xác minh freshness, phiên bản active document,
phiên bản index cùng một mẫu câu trả lời của support agent trước khi hoạt động
trở lại.

## Phòng ngừa / Công việc cần thực hiện

| Công việc | Người phụ trách | Hạn hoàn thành | Lý do |
|---|---|---|---|
| Block các critical contract failures và quarantine batch lỗi | Data Platform | Trước release tiếp theo | Ngăn dữ liệu sai đi vào mart |
| Theo dõi volume theo weekday bằng baseline robust | Data Reliability | Trước release tiếp theo | Phát hiện ingestion thiếu mà không hard-code số dòng |
| Thêm KB freshness SLO và kiểm tra index version | Support AI | Trước release tiếp theo | Ngăn agent sử dụng policy cũ |
| Duy trì dbt unit tests cho SCD/customer joins | Analytics Engineering | Liên tục | Ngăn revenue bị nhân đôi |
| Sử dụng burn rate hai cửa sổ cho việc paging | SRE | Trước khi production rollout | Tránh page do spike tạm thời |

## Checklist khôi phục

- [x] Đã triển khai contract validation cho orders và KB
- [x] Generic, singular và unit tests của dbt pass trên dữ liệu healthy
- [x] Anomaly detection bắt được volume drop
- [x] Dataset lineage và column lineage thể hiện blast radius
- [x] Đã triển khai SLO, error budget và multi-window burn logic
- [x] Batch duplicate critical được tự động quarantine kèm đường dẫn audit
- [x] Đã phát OpenLineage COMPLETE events cho cả hai pipeline domain
- [x] Đã chạy SodaCL contract trên bảng orders trong DuckDB
- [x] Đã cài và chạy Elementary OSS trong dbt
- [x] Public tests pass
- [x] Ba controlled faults tạo ra đúng các tín hiệu kỳ vọng

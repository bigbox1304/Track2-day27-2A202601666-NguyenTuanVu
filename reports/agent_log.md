# Nhật ký quyết định của AI Agent

## Quyết định 1 — Giữ stable API

- Giả thuyết: hidden evaluation import `student_api.py`, vì vậy tên các hàm public và những key bắt buộc trong kết quả phải được giữ nguyên.
- Đề xuất của agent: cải thiện phần implementation phía sau các wrapper hiện tại và chỉ bổ sung metadata fields.
- Bằng chứng/test: `python -m pytest tests_public -q` pass với 10 tests.
- Quyết định: chấp nhận.
- Lý do: behavior được cải thiện mà không phá vỡ interface đã tài liệu hóa.

## Quyết định 2 — Validate cả orders và KB contract

- Giả thuyết: KB contract dùng `fields` còn orders contract dùng `columns`, đồng thời stale KB là một fault bắt buộc.
- Đề xuất của agent: cho validator hỗ trợ cả hai section, declared types, string lengths, freshness và severity actions.
- Bằng chứng/test: stale KB tạo một freshness check lỗi với `action=warn`; KB healthy không có lỗi.
- Quyết định: chấp nhận.
- Lý do: một validator dùng chung cho cả hai dataset và cung cấp metadata có thể hành động.

## Quyết định 3 — Dùng baseline anomaly robust và theo mùa

- Giả thuyết: một z-score global duy nhất dễ bị ảnh hưởng bởi outlier và weekday seasonality.
- Đề xuất của agent: `auto` ưu tiên history cùng segment, dùng MAD khi đủ dữ liệu và fallback về z-score; known events sẽ suppress các alert đã biết trước.
- Bằng chứng/test: volume-drop scenario trả về `is_anomaly=true`; các z-score public tests pass.
- Quyết định: chấp nhận.
- Lý do: detector vẫn đơn giản, dễ giải thích và ít nhạy với history bị lệch.

## Quyết định 4 — Bảo vệ customer join

- Giả thuyết: nhiều active SCD rows có thể nhân revenue dù SQL vẫn chạy thành công.
- Đề xuất của agent: xếp hạng các active customer versions theo `valid_from`, giữ phiên bản mới nhất, thêm singular test và dbt unit tests.
- Bằng chứng/test: dbt hoàn thành 21/21, bao gồm hai unit tests và `assert_unique_active_customer`.
- Quyết định: chấp nhận.
- Lý do: transformation đúng và failure mode được kiểm thử rõ ràng.

## Quyết định 5 — Chỉ page khi burn kéo dài

- Giả thuyết: một spike ngắn không nên page nếu chưa được xác nhận bởi long window.
- Đề xuất của agent: chỉ page khi cả short và long burn windows vượt ngưỡng đáng kể; các trường hợp khác trả về warning/info.
- Bằng chứng/test: `multiwindow_burn(20, 10)` page, còn `multiwindow_burn(20, 1)` không page.
- Quyết định: chấp nhận.
- Lý do: tạo policy hai cửa sổ có thể hành động và tránh page do nhiễu tạm thời.

## Quyết định 6 — Tự động quarantine batch critical

- Giả thuyết: critical contract failure phải ngăn dữ liệu lan truyền và giữ lại các dòng lỗi để replay/debug.
- Đề xuất của agent: quarantine chọn lọc các lỗi theo row-level và quarantine toàn bộ batch với dataset-level critical failures.
- Bằng chứng/test: duplicate PK tạo quarantine CSV chứa 6 dòng, gồm 3 bản ghi trùng và 3 bản ghi gốc.
- Quyết định: chấp nhận.
- Lý do: batch lỗi được cô lập mà không xóa bằng chứng.

## Quyết định 7 — Phát OpenLineage events local

- Giả thuyết: dataset lineage cần có thể export theo event format chuẩn ngay cả khi chưa có Marquez server.
- Đề xuất của agent: phát OpenLineage `COMPLETE` events cho luồng orders-to-dashboard và KB-to-support-agent vào JSONL sink.
- Bằng chứng/test: mỗi baseline run thêm hai events vào `reports/openlineage_events.jsonl` với run ID, job, inputs và outputs.
- Quyết định: chấp nhận.
- Lý do: event sink không cần dependency ngoài và sau này có thể thay bằng OpenLineage transport.

## Quyết định 8 — Bổ sung Soda và Elementary observability

- Giả thuyết: các bonus còn lại yêu cầu SodaCL contract và Elementary dbt package chạy thật, không chỉ có placeholder files.
- Đề xuất của agent: chạy Soda trên bảng orders trong DuckDB và thêm Elementary làm dbt dependency kèm compatibility flag.
- Bằng chứng/test: Soda tạo scan result pass; Elementary được cài qua `dbt deps` và `dbt build`.
- Quyết định: chấp nhận sau khi xác minh tương thích phiên bản.
- Lý do: cả hai công cụ đều có evidence local và mở rộng các lớp validation/observability hiện tại.

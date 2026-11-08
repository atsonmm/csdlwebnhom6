## THÔNG BÁO

## và yêu cầu đánh giá Project cuối kỳ năm 2026 Về việc đăng ký nhóm, đề tài

Học phần: Cơ sở dữ liệu Web và Hệ thống thông tin

Ngành: Khoa học dữ liệu

Project cuối kỳ là một hệ thống thông tin Web có cơ sở dữ liệu (CSDL), do nhóm sinh viên tự phân tích, xây dựng, kiểm thử và bảo vệ. Trọng tâm đánh giá là thiết kế dữ liệu, truy vấn, tính đúng đắn của nghiệp vụ và khả năng làm chủ sản phẩm của từng thành viên.

## I. THÀNH VIÊN NHÓM VÀ ĐĂNG KÝ ĐỀ TÀI

## 1. Thành lập nhóm và đăng ký đề tài

Mỗi nhóm gồm 03 hoặc 04 sinh viên, trong đó có 01 trưởng nhóm là đầu mối liên hệ. Sinh viên chưa có nhóm báo giảng viên để được sắp xếp. Việc thay đổi thành viên sau khi đăng ký phải được giảng viên chấp thuận.

Nhóm gửi thông tin đăng ký trên kênh của lớp: tên nhóm; họ tên, mã sinh viên và GitHub username của từng thành viên; trưởng nhóm và thông tin liên hệ; tên đề tài; người sử dụng; 03 nghiệp vụ chính; các bảng và quy mô dữ liệu dự kiến; URL repository; phân công ban đầu.

## 2. Phạm vi đề tài

Đề tài phải khác CourseHub về bài toán và quy tắc nghiệp vụ. Được tham khảo cách tổ chức mã, kỹ thuật và quy trình đã học; không chấp nhận chỉ đổi tên bảng, đổi nhãn giao diện hoặc sao chép nguyên hệ thống mẫu.

Phạm vi tối thiểu: 03 luồng nghiệp vụ hoàn chỉnh, 02 nhóm quyền sử dụng và 02 báo cáo/thao tác thống kê lấy dữ liệu từ CSDL. Đăng nhập, đăng xuất và các màn hình thêm/sửa/xóa của cùng một đối tượng không được tách nhỏ để tính thành nhiều nghiệp vụ.

Ví dụ: lập phiếu mượn - kiểm tra sách còn - ghi nhận sách đang mượn là một luồng nghiệp vụ; trả sách và xử lý trả muộn là luồng khác.

## 3. Công nghệ áp dụng

Sử dụng PostgreSQL, Python/FastAPI, giao diện React và Git/GitHub theo nội dung thực hành. Công nghệ khác chỉ sử dụng khi được giảng viên chấp thuận và vẫn đáp ứng đủ yêu cầu CSDL quan hệ. Không thay toàn bộ CSDL bằng MongoDB, tệp JSON hoặc dữ liệu giả lập (mock data) trong giao diện.

Thang điểm Project tối đa 12 điểm cho mỗi sinh viên. Điểm cơ bản tối đa 10 điểm; các khoản cộng được quy định tại mục IX, nhưng tổng điểm cuối cùng không vượt quá 12 điểm.


## II. VAI TRÒ VÀ PHÂN CÔNG

Mỗi nhóm tổ chức công việc theo chu trình: làm rõ yêu cầu - thiết kế - phát triển - kiểm thử - tích hợp - bàn giao. Một người có thể kiêm nhiệm nhiều vai trò, nhưng mỗi đầu việc phải có người thực hiện, người kiểm tra và sản phẩm bàn giao rõ ràng.

## 1. Phân bố vai trò trong nhóm

| Vai trò chính | Nhóm 03 người | Nhóm 04 người |
| --- | --- | --- |
| Thành viên 1 | Trưởng nhóm; Backend; tích hợp | Trưởng nhóm; Backend; tích hợp và |
|   | và phát hành. | phát hành. |
| Thành viên 2 | CSDL; Backend; nghiệp vụ dữ | CSDL; Backend; nghiệp vụ dữ liệu. |
|   | liệu. |   |
| Thành viên 3 | Frontend; kiểm thử; phối hợp triển | Frontend người dùng; thiết kế giao |
|   | khai hạ tầng. | diện. |
|   | Không có. Ba thành viên cùng chia | Frontend quản trị/thống kê; kiểm thử; |
| Thành viên 4 | sẻ kiểm thử, tài liệu và hạ tầng theo | đầu mối triển khai hạ tầng. |
|   | phần phụ trách. |   |

Cách chia trên là phương án khuyến nghị. Các vai trò trên là vai trò cơ bản của dự án, ngoài ra còn có thể có các role đặc thù khác như BA, DevOps. Nhóm được điều chỉnh theo đề tài, nhưng không để trống khâu nào và phải ghi rõ người kiêm nhiệm. Nhóm 03 người tập trung vào nghiệp vụ cốt lõi, áp dụng cùng thang điểm, không bị trừ điểm vì ít thành viên hơn.

## 2. Trách nhiệm của trưởng nhóm

Trưởng nhóm chịu trách nhiệm chung về phạm vi, phân công, tích hợp và bản phát hành cuối cùng. Trưởng nhóm chủ trì làm rõ yêu cầu; phân chia và theo dõi đầu việc; quản lý repository, nhánh và việc hợp nhất mã; tổ chức review/kiểm thử; nhận bàn giao các cấu phần; xử lý các điểm không tương thích giữa Frontend, Backend và CSDL; chốt tài liệu, phiên bản và sản phẩm sẵn sàng nộp.

Trưởng nhóm đồng thời là Release/Integration Owner của nhóm: trực tiếp đóng gói và chốt bản phát hành cuối cùng sau khi nhận bàn giao từ các thành viên. Mỗi người vẫn phải tự chuẩn bị Dockerfile/cấu hình/tài liệu cho phần mình phụ trách; trưởng nhóm không làm thay toàn bộ các cấu phần mà chịu trách nhiệm kiểm tra, tích hợp, gắn tag/release, tổ chức dựng lại và xác nhận bản cuối chạy được. Điểm trách nhiệm trưởng nhóm là +1,0 khi có đủ minh chứng tại mục IX.

## 3. Trách nhiệm của mỗi thành viên

Mỗi thành viên phải trực tiếp xây dựng một phần chức năng hoặc xử lý dữ liệu chạy được; có truy vấn và kiểm thử liên quan; rà soát phần việc của người khác; tự viết hướng dẫn bàn giao. Không phân công một người chỉ làm slide, báo cáo hoặc kiểm thử thủ công.

Bảng phân công đặt trong README hoặc tài liệu nhóm, ghi rõ: họ tên/GitHub username - vai trò - hạng mục - người kiểm tra - sản phẩm bàn giao - liên kết minh chứng. Khi thay đổi phân công, cập nhật tại đây và trên Issue liên quan.


## 4. Phân công theo khâu và yêu cầu bàn giao

Người thực hiện tự kiểm tra trước khi bàn giao. Người kiểm tra phải là thành viên khác; trưởng nhóm xác nhận kết quả chung. Mã của trưởng nhóm cũng phải được thành viên khác rà soát.

| Khâu | Người thực hiện và phối hợp | Bàn giao và xác nhận |
| --- | --- | --- |
|   | Trưởng nhóm chủ trì; cả nhóm làm rõ người | Mô tả nghiệp vụ/Issue có đầu vào, kết quả mong |
| Yêu cầu | dùng, nghiệp vụ, phạm vi và quy tắc. | đợi và điều kiện hoàn thành; cả nhóm thống |
|   |   | nhất trước khi làm. |
|   | CSDL phụ trách ERD; Backend thiết kế API | ERD, luồng xử lý, quy ước API và bản phác |
| Thiết kế | và xử lý; Frontend phác giao diện. Trưởng | giao diện khớp nhau. Thay đổi cấu trúc dữ |
|   | nhóm kiểm tra sự thống nhất. | liệu/API phải được thông báo cho bên sử dụng. |
|   | Người phụ trách CSDL tổng hợp schema, | Script dựng CSDL, dữ liệu mẫu/lớn, truy vấn, |
| CSDL và dữ | dữ liệu, migration; thành viên khác viết truy | chỉ mục và kết quả kiểm tra. Backend kiểm tra |
| liệu | vấn theo phần việc. | khả năng sử dụng; người kiểm tra chạy lại trên |
|   |   | CSDL thử. |
|   | Người phụ trách Backend triển khai API, | API chạy được, mô tả đầu vào/đầu ra và ca kiểm |
| Backend | nghiệp vụ, phân quyền, transaction và xử lý | thử. Frontend xác nhận kết nối; thành viên khác |
|   | lỗi; phối hợp CSDL. | kiểm tra mã và tác động lên dữ liệu. |
|   | Người phụ trách Frontend xây màn hình, | Luồng thao tác dùng dữ liệu thật, nhất quán với |
| Frontend | biểu mẫu, báo cáo và kết nối API; có trạng | thiết kế. Backend và người kiểm tra đối chiếu |
|   | thái đang tải, rỗng và lỗi. | kết quả trên giao diện với CSDL. |
|   | Mỗi thành viên kiểm tra chéo, báo lỗi |   |
| Kiểm thử và | và sửa phần mình; đầu mối kiểm thử tổng | Có kết quả chạy thử, Issue lỗi và xác nhận |
| tích hợp | hợp kịch bản. Trưởng nhóm điều phối tích | sau sửa. Chỉ đóng đầu việc khi đạt điều kiện |
|   | hợp toàn hệ thống và quyết định khi có xung | hoàn thành và không làm hỏng luồng liên quan. |
|   | đột giữa các cấu phần. |   |
|   | Mỗi người chuẩn bị gói bàn giao của | Bản release có mã nguồn, Dockerfile/cấu |
| Đóng gói, | cấu phần mình phụ trách. Thành viên hạ | hình theo từng VM, .env.example, |
| triển khai và | tầng thực hiện cấu hình 03 VM và mạng. | migration/seed, backup/restore, README và |
| bàn giao | Trưởng nhóm nhận bàn giao, tích hợp, đóng | hướng dẫn triển khai. Một thành viên khác dựng |
|   | gói bản phát hành cuối, gắn tag/release và | lại theo tài liệu trước khi chốt. |
|   | chủ trì triển khai/kiểm tra bản nộp. |   |

Các xác nhận được ghi ngay trong Issue, Pull Request hoặc tài liệu kiểm thử; không cần lập biên bản riêng cho từng bước. Người phụ trách không được coi là đã bàn giao chỉ vì đã đẩy mã lên repository.


## III. YÊU CẦU VỀ CƠ SỞ DỮ LIỆU

Các ngưỡng số lượng dưới đây xác định phạm vi Project cuối kỳ. Đạt đủ số bảng hoặc số dòng không đồng nghĩa với đạt điểm tối đa; dữ liệu phải đúng quan hệ, phục vụ nghiệp vụ và được hệ thống sử dụng.

## 1. Thiết kế và toàn vẹn dữ liệu

CSDL có tối thiểu 06 bảng nghiệp vụ có ý nghĩa. Không tính bảng xác thực/phân quyền thuần túy, session, migration hoặc log kỹ thuật. Không tách bảng giả tạo để đủ số lượng.

Nộp ERD khớp với schema thực tế và mô tả các trường dữ liệu. Mỗi bảng có khóa chính; khóa ngoại, NOT NULL, UNIQUE, CHECK và cách xử lý xóa/sửa được áp dụng theo nghiệp vụ. Quan hệ nhiều-nhiều phải được biểu diễn phù hợp, không ghép danh sách mã vào một chuỗi thay cho quan hệ cần quản lý.

Mô tả các quy tắc quan trọng, nơi bảo vệ tại CSDL/Backend và ca kiểm tra dữ liệu hợp lệ, không hợp lệ. Không ấn định số lượng cho từng loại ràng buộc; chấm theo khả năng bảo vệ dữ liệu và lý do thiết kế.

## 2. Quy mô và chất lượng dữ liệu

Chuẩn bị 02 bộ dữ liệu cùng schema: bộ demo gọn, dễ đối chiếu kết quả; bộ dữ liệu lớn để đánh giá truy vấn và hiệu năng. Các ngưỡng 10.000 và 100.000 bản ghi áp dụng cho bộ dữ liệu lớn, không bắt buộc dùng toàn bộ dữ liệu này khi demo giao diện.

| Hạng mục | Yêu cầu |
| --- | --- |
| Bảng có nhiều dữ liệu | Tối thiểu 03 bảng nghiệp vụ, mỗi bảng từ 10.000 bản ghi. |
|   | Khuyến khích 04-05 bảng hoặc nhiều hơn khi phù hợp. |
| Bảng đánh giá hiệu | Ít nhất 01 bảng từ 100.000 bản ghi, có thể nằm trong 03 bảng trên, |
| năng | phải được dùng trong truy vấn đo. |
| Bảng danh mục và các | Số dòng phù hợp với bài toán và các bảng liên quan. Không ép |
| bảng còn lại | khoa, phòng học, trạng thái... đạt 10.000 dòng. |

Mỗi nhóm đề xuất quy mô theo đề tài: tên/vai trò từng bảng, số dòng demo và dữ liệu lớn, khoảng thời gian mô phỏng, cách sinh và truy vấn sử dụng. Nếu đặc thù bài toán không phù hợp với ngưỡng chung, nhóm nêu lý do và phương án thay thế để giảng viên chấp thuận trước khi tạo bộ dữ liệu. Phương án được chấp thuận là căn cứ nghiệm thu; không tự hạ ngưỡng khi nộp bài.

Ví dụ giả lập cho quản lý trường học: 1.000 học sinh, 10 môn/học kỳ, 02 học kỳ/năm trong 03 năm tạo 60.000 dòng học sinh - môn - học kỳ. Với 03 điểm thành phần có 180.000 dòng kết quả; điểm danh 180 ngày/năm tạo 540.000 dòng. Như vậy, dữ liệu lớn nằm ở hoạt động phát sinh, không nhất thiết ở bảng học sinh.

Phải có script sinh dữ liệu, hướng dẫn chạy lại và thống kê số dòng từng bảng. Dữ liệu đúng quan hệ, trạng thái, ngày tháng; không sao chép dòng vô nghĩa. Dùng dữ liệu giả lập hoặc nguồn được phép, không công khai dữ liệu cá nhân thật.


## 3. Truy vấn SQL và view

Có ít nhất 08 truy vấn nghiệp vụ khác nhau, bao phủ: JOIN nhiều bảng, tổng hợp, truy vấn con/EXISTS, CTE, hàm cửa sổ, tra cứu có lọc và phân trang. Một truy vấn có thể kết hợp nhiều kỹ thuật. Chỉ đổi tham số hoặc tên cột không được tính là truy vấn mới.

Có ít nhất 01 view được sử dụng trong hệ thống. Các truy vấn chính phải phục vụ API, màn hình hoặc báo cáo; có 02 báo cáo/thống kê hiển thị trên giao diện. Nộp SQL, mục đích, đầu vào, kết quả mẫu và người phụ trách. Dùng ORM vẫn phải giải thích được SQL tương ứng.

## 4. Transaction và xử lý đồng thời

Triển khai ít nhất 01 nghiệp vụ ghi vào từ 02 bảng trong cùng transaction; kiểm tra cả trường hợp thành công và lỗi giữa chừng để xác nhận rollback. Có 01 tình huống tranh chấp với hai kết nối/yêu cầu chạy chồng lấn, kèm cách bảo vệ và kết quả kiểm tra. Không tính việc gọi lần lượt hai lần là kiểm thử đồng thời.

## 5. Chỉ mục và hiệu năng

Thiết kế 02 chỉ mục phục vụ truy vấn thực tế, ngoài chỉ mục do khóa chính/UNIQUE tạo. Phân tích 02 truy vấn trước và sau tối ưu; ít nhất một truy vấn dùng bảng 100.000 dòng hoặc quy mô thay thế đã được chấp thuận.

Minh chứng gồm SQL, tham số, quy mô dữ liệu, môi trường đo, kế hoạch EXPLAIN (ANALYZE, BUFFERS), thời gian và nhận xét. Đo lặp lại trên cùng môi trường và bộ dữ liệu; báo cáo trung thực kể cả khi chỉ mục chưa cải thiện hiệu năng. Không áp một mức tăng tốc cố định cho mọi đề tài.

## 6. Migration, sao lưu và khôi phục

Thực hiện 01 thay đổi schema có quản lý phiên bản trên CSDL đã có dữ liệu, kèm kiểm tra dữ liệu cũ và phương án xử lý khi lỗi. Sao lưu cấu trúc, dữ liệu và tệp của hệ thống nếu có; khôi phục sang môi trường thử và đối chiếu kết quả. Không tính xóa rồi tạo lại CSDL là migration, hoặc nộp tệp backup mà chưa thử khôi phục.

Toàn bộ nội dung CSDL phải cùng phục vụ đề tài và được kiểm tra trên PostgreSQL hoặc hệ quản trị đã được chấp thuận. Không dùng bài SQL hoặc demo tách rời hệ thống để thay thế.


## IV. PHÁT TRIỂN, KIỂM THỬ VÀ QUẢN LÝ MÃ NGUỒN

## 1. Yêu cầu ứng dụng và kiểm thử

Frontend và Backend phải thực hiện được các nghiệp vụ đã đăng ký trên CSDL thật. Có bản phác giao diện bằng Figma hoặc công cụ tương đương; giao diện dễ sử dụng, hiển thị đúng dữ liệu, có xử lý trạng thái rỗng và lỗi. Không bắt buộc hiệu ứng trang trí phức tạp.

Backend kiểm tra đầu vào và phân quyền, không chỉ ẩn nút trên giao diện. Truy vấn nhận dữ liệu người dùng phải được tham số hóa; không lưu mật khẩu dạng rõ, không để khóa bí mật trong mã nguồn. Tài liệu API có thể dùng OpenAPI/Swagger hoặc mô tả tương đương.

Kiểm thử phải bao phủ luồng thành công, dữ liệu sai/giá trị biên, phân quyền, rollback, đồng thời, migration và khôi phục. Có kiểm thử tự động cho các xử lý dữ liệu quan trọng. Mỗi ca ghi thao tác, kết quả mong đợi và thực tế; không ấn định số ca chỉ để đủ chỉ tiêu.

## 2. Làm việc và ghi nhận quá trình trên GitHub

Nhóm sử dụng 01 repository chung. Mỗi thành viên dùng tài khoản cá nhân. Các đầu việc chính thực hiện theo luồng: Issue - nhánh làm việc - commit - Pull Request - kiểm tra chéo - merge - xác nhận hoàn thành.

Issue ghi người phụ trách và điều kiện hoàn thành; Pull Request ghi thay đổi và cách đã kiểm tra. Người review phải nêu nhận xét kỹ thuật hoặc kết quả chạy thử; không chỉ ghi "OK". Tác giả xử lý góp ý trước khi merge. Không yêu cầu đủ một số lượng commit/Pull Request cố định.

Điểm quá trình được chấm theo từng cá nhân, đối chiếu phân công với lịch sử commit, nội dung thay đổi (diff), Issue, Pull Request, review, kiểm thử và bàn giao. Cần thể hiện được: ai làm, làm gì, có đúng vai trò, đã sửa sau góp ý và được ai kiểm tra.

Không chấm theo số dòng mã, số commit hay màu biểu đồ hoạt động. Khi làm cặp, dùng AI hoặc gộp commit, phải giữ thông tin đủ để xác định đóng góp thật. Không tạo commit rác, giả mạo lịch sử hoặc để một người đứng tên toàn bộ công việc.

Cập nhật trạng thái ngay trên Issue/Pull Request khi công việc thay đổi; không cần báo cáo tiến độ hằng tuần riêng. Lịch sử ít hoặc chưa rõ là căn cứ yêu cầu giải trình, không tự động kết luận gian lận.

## 3. Đóng gói trong quá trình phát triển

Mỗi thành phần phải có cấu hình chạy rõ ràng, Dockerfile phù hợp và .env.example không chứa bí mật. Dữ liệu CSDL và tệp phải được lưu bền vững. Trong quá trình phát triển có thể chạy cục bộ trên một máy; bản Project hoàn chỉnh phải triển khai theo kiến trúc 03 VM bắt buộc tại mục V.


## V. YÊU CẦU HẠ TẦNG BẮT BUỘC VÀ PHÁT HÀNH

## 1. Kiến trúc triển khai bắt buộc

Mọi nhóm phải triển khai bản Project hoàn chỉnh trên 03 máy ảo (VM) tách biệt cho Frontend, Backend và CSDL + Storage. Đây là yêu cầu bắt buộc của sản phẩm, không phải điểm cộng. Khi phát triển, nhóm có thể chạy trên một máy; khi nghiệm thu/bảo vệ phải chứng minh hệ thống hoạt động đúng trên kiến trúc 03 VM.

| Máy ảo | Thành phần và yêu cầu |
| --- | --- |
| VM 1 - Frontend | Chạy Frontend bằng Docker; cung cấp điểm truy cập cho người |
|   | dùng. Có thể đặt reverse proxy tại đây. |
| VM 2 - Backend | Chạy Backend/API bằng Docker; xử lý nghiệp vụ và kết nối tới VM |
|   | 3. Không đặt CSDL chính trên VM này. |
|   | Chạy PostgreSQL và thành phần lưu trữ tệp/object storage hoặc cơ |
| VM 3 - DB + Storage | chế lưu trữ bền vững tương đương. Có backup/restore và dữ liệu còn sau |
|   | khi khởi động lại dịch vụ. |

Ba VM phải có hệ điều hành khách và địa chỉ mạng riêng; 03 container hoặc 03 cổng trên cùng 01 VM không được tính là 03 VM. Có thể dựng 03 VM trên cùng một máy vật lý. Frontend không kết nối trực tiếp PostgreSQL; cổng CSDL và giao diện quản trị lưu trữ không được mở công khai. Tên miền và HTTPS không bắt buộc, nhưng được cộng điểm theo mục IX.

## 2. Trách nhiệm phát hành và triển khai

Người phụ trách từng cấu phần chịu trách nhiệm bàn giao mã, Dockerfile/cấu hình và hướng dẫn của cấu phần đó. Thành viên phụ trách hạ tầng chịu trách nhiệm cấu hình VM, kết nối mạng, reverse proxy và triển khai kỹ thuật. Trưởng nhóm là người nhận bàn giao cuối cùng, tích hợp các cấu phần, chốt phiên bản/tag, đóng gói release và chịu trách nhiệm xác nhận hệ thống 03 VM chạy được trước khi nộp. Cách tổ chức này tương ứng với vai trò Release/Integration Owner trong một nhóm dự án thực tế.


## VI. HỒ SƠ NỘP PROJECT CUỐI KỲ

Mã nguồn và cấu hình: repository kèm mã commit/tag bản nộp; Frontend, Backend, schema/migration, dữ liệu demo, script sinh dữ liệu lớn, SQL/view/chỉ mục, kiểm thử và cấu hình chạy.

Tài liệu: báo cáo PDF và bản nguồn; slide; README hướng dẫn cài đặt, chạy, tài khoản demo; mô tả API; phân công và đóng góp cá nhân. Báo cáo trình bày bài toán, kiến trúc, CSDL, nghiệp vụ, kiểm thử, kết quả và hạn chế; không ấn định số trang.

Minh chứng: số dòng từng bảng; truy vấn và kết quả; kiểm tra ràng buộc, transaction/đồng thời, hiệu năng, migration và khôi phục; các hạng mục điểm cộng nếu có. Có thể đặt trong thư mục docs và dẫn đường dẫn từ báo cáo, không sao chép lặp lại cùng nội dung.

Repository Private phải cấp quyền cho giảng viên. Không nộp mật khẩu thật, token, tệp .env hoặc dữ liệu cá nhân. Với dữ liệu lớn, nộp script tái tạo thay vì đưa dump lớn lên repository. Ngày nộp và lịch bảo vệ được thông báo riêng.

## VII. TIÊU CHÍ VÀ CÁCH TÍNH ĐIỂM

Điểm cơ bản tối đa 10; điểm Project sau cộng tối đa 12. Điểm sản phẩm chung (G) tối đa 6,0; điểm quá trình cá nhân (P) tối đa 2,0; bảo vệ cá nhân (V) tối đa 2,0. Hạ tầng 03 VM là yêu cầu bắt buộc và nằm trong tiêu chí sản phẩm/vận hành, không phải điểm cộng.

*1. Điểm sản phẩm chung (G): 6,0 điểm*

| Nội dung | Điểm | Căn cứ đánh giá |
| --- | --- | --- |
| Thiết kế và toàn vẹn | 1,5 | ERD, schema, quy tắc, ràng buộc thực thi và lý do thiết |
|   | kế. |   |
| Dữ liệu, SQL và view | 1,5 | Quy mô/chất lượng dữ liệu; script tái tạo; truy vấn, view |
|   | và báo cáo đúng. |   |
| Transaction và đồng thời | 0,8 | Nghiệp vụ ghi nhiều bảng; rollback; ca tranh chấp và |
|   | cách bảo vệ. |   |
| Hiệu năng | 0,7 | Chỉ mục có cơ sở; phép đo, kế hoạch thực thi và phân |
|   | tích kết quả. |   |
| API và giao diện | 0,8 | Luồng nghiệp vụ, phân quyền, kết nối CSDL, xử lý lỗi |
|   | và báo cáo. |   |
| Kiểm thử, vận hành, tài | 0,7 | Kiểm thử; migration; backup/restore; đóng gói; khả |
| liệu | năng dựng lại và bàn giao. |   |

Các nội dung CSDL trong bốn dòng đầu chiếm 4,5/6,0 điểm sản phẩm, chưa kể migration, khôi phục và bảo vệ CSDL.


## 2. Điểm quá trình cá nhân (P): 2,0 điểm

| Nội dung | Điểm | Căn cứ đánh giá |
| --- | --- | --- |
| Thực hiện vai trò và đóng | 1,0 | Phần việc thật, khớp phân công; chất lượng mã, truy vấn |
| góp |   | và kiểm thử; hoàn thành bàn giao theo vai trò. |
| Lịch sử và quy trình |   | Issue, commit/diff, nhánh, Pull Request và review phản |
| repository | 0,5 | ánh quá trình; truy vết được người làm và người kiểm |
|   | tra. |   |
| Phối hợp và xử lý góp ý | 0,5 | Rà soát công việc của bạn; phản hồi, sửa lỗi; thông báo |
|   |   | thay đổi liên quan; tài liệu bàn giao dùng được. |

## 3. Bảo vệ cá nhân (V): 2,0 điểm

Hiểu CSDL, SQL và quy tắc nghiệp vụ: 1,0 điểm. Giải thích luồng giao diện - API - CSDL và phần việc cá nhân: 0,5 điểm. Thực hiện chỉnh sửa/kiểm tra nhỏ không dùng AI: 0,5 điểm.

## 4. Công thức và nguyên tắc tính điểm

Điểm sinh viên i = min(12; G + Pi + Vi + D + S + C + L + A + Ti).

Trong đó: D là tên miền/subdomain (+0,25); S là SSL/HTTPS (+0,25); C là tự động build/test/deploy (+0,25); L là LaTeX (+0,5); A là chatbot (tối đa +1,0); Ti là trách nhiệm trưởng nhóm (+1,0 khi đủ điều kiện, thành viên khác bằng 0). Các khoản cộng chỉ được tính khi có minh chứng và tổng cuối cùng không vượt 12.

D, S, C, L và A là điểm cộng theo sản phẩm nhóm; Pi, Vi và Ti được xét riêng từng người. Điểm cộng không thay thế yêu cầu bắt buộc. Thành viên không có đóng góp thực chất cho hạng mục nhóm có thể không được hưởng điểm cộng tương ứng.

Ví dụ: một thành viên có G + Pi + Vi = 8,5; nhóm có tên miền (+0,25), HTTPS (+0,25), LaTeX (+0,5) và chatbot (+1,0) thì được 10,5 điểm. Nếu là trưởng nhóm và hoàn thành đầy đủ trách nhiệm, cộng thêm +1,0 thành 11,5. Nếu tổng các thành phần vượt 12 thì ghi nhận 12,0.

Chấm theo mức hoàn thành, tính đúng đắn và minh chứng của từng tiêu chí. Nội dung không có hoặc không xác minh được không nhận điểm tương ứng. Đạt đủ số bảng, số dòng hoặc có giao diện đẹp không đồng nghĩa với đạt điểm tối đa.


## VIII. THUYẾT TRÌNH, BẢO VỆ VÀ LIÊM CHÍNH HỌC THUẬT

Mỗi nhóm có 15 phút, gồm trình bày/demo và vấn đáp cá nhân. Tất cả thành viên phải có mặt, trực tiếp trả lời, không trả lời thay nhau. Demo tập trung vào nghiệp vụ, dữ liệu và kết quả kiểm tra; chuẩn bị sẵn môi trường, tài khoản và dữ liệu.

Giảng viên có thể yêu cầu mở lịch sử repository, giải thích phân công, đọc/sửa SQL, theo dõi luồng API hoặc kiểm tra dữ liệu. Nếu thời gian chung chưa đủ xác nhận năng lực, sinh viên được kiểm tra bổ sung, không suy đoán đóng góp chỉ từ lượt trình bày.

Để xác nhận khả năng làm chủ sản phẩm, V cần đạt ít nhất 1,0/2,0, trong đó phần CSDL/SQL đạt ít nhất 0,5/1,0. Sinh viên chưa đạt được kiểm tra xác nhận bổ sung 01 lần; nếu vẫn chưa đạt, điểm Project tối đa 4,0 và không xét điểm cộng. Không tự động coi kết quả bảo vệ yếu là gian lận.

Trường hợp được xác minh không có đóng góp thực chất sau khi đối chiếu phân công, mã, minh chứng và giải trình thì nhận 0 điểm Project. Không hưởng điểm nhóm chỉ vì có tên trong danh sách.

Được sử dụng AI trong quá trình phát triển, nhưng phải hiểu và kiểm chứng mã; ghi ngắn phạm vi hỗ trợ trong AI_USAGE.md hoặc báo cáo. Khi bảo vệ cá nhân, không dùng AI hoặc người khác hỗ trợ trả lời. Việc demo chatbot là trình diễn chức năng, không thay thế câu trả lời của sinh viên.

Phải ghi nguồn mã, dữ liệu và tài liệu tham khảo. Không mua, thuê, nhờ làm hộ, giả mạo minh chứng hoặc nhận sản phẩm của người khác là của mình. Các vi phạm được xử lý theo quy định học phần và Nhà trường.

## IX. ĐIỂM CỘNG

Các khoản cộng gồm trách nhiệm trưởng nhóm, tên miền/SSL, tự động triển khai, LaTeX và chatbot. Kiến trúc 03 VM ở mục V là yêu cầu bắt buộc, không nằm trong điểm cộng. Các khoản cộng chỉ áp dụng khi hạng mục chạy được, có minh chứng và cá nhân đạt điều kiện xác nhận tại mục VIII.

## 1. Trách nhiệm trưởng nhóm: +1,0 điểm

Chỉ xét cho 01 trưởng nhóm đã đăng ký và thực hiện đầy đủ vai trò Project Lead/Release Owner: phân công và điều phối; quản lý repository và việc hợp nhất; tổ chức review/kiểm thử; nhận bàn giao các cấu phần; tích hợp, đóng gói release cuối; phối hợp triển khai 03 VM; chốt tài liệu và bản nộp. Minh chứng lấy từ phân công, Issue/PR, lịch sử merge, kiểm thử, release/tag, tài liệu triển khai và giải trình của nhóm.

Khoản cộng này ghi nhận trách nhiệm xuyên suốt và trách nhiệm đối với bản phát hành cuối, khác với điểm quá trình cho phần kỹ thuật cá nhân. Không tự động cộng vì giữ tên trưởng nhóm hoặc là chủ repository; không hoàn thành trách nhiệm bàn giao/phát hành thì Ti = 0.


## 2. Tên miền, SSL và tự động triển khai: tối đa +0,75 điểm

Tên miền/subdomain: +0,25 điểm khi Web được cấu hình truy cập ổn định qua tên miền hoặc subdomain do nhóm quản lý/cấu hình, trỏ đúng tới hệ thống và demo được. Không bắt buộc mua tên miền; chấp nhận subdomain phù hợp.

SSL/HTTPS: +0,25 điểm khi điểm truy cập Web/API sử dụng chứng chỉ hợp lệ, điều hướng HTTP sang HTTPS phù hợp và không phát sinh lỗi mixed content trong luồng demo.

Tự động triển khai: +0,25 điểm khi có quy trình CI/CD hoặc workflow tương đương thực hiện build/test/deploy và nhóm chứng minh được ít nhất một lần triển khai thành công. Chỉ có Dockerfile hoặc script chạy tay chưa đủ.

## 3. Báo cáo LaTeX: +0,5 điểm

Báo cáo soạn bằng LaTeX, đủ nội dung, trình bày nhất quán; nộp PDF và mã nguồn đầy đủ để biên dịch lại. Chấp nhận mẫu có sẵn có ghi nguồn; không tính việc chèn toàn bộ báo cáo dưới dạng ảnh/PDF vào tệp LaTeX. Báo cáo Word vẫn được chấm đủ điểm cơ bản.

## 4. Chatbot tích hợp: tối đa +1,0 điểm

Chức năng và tích hợp: tối đa +0,5. Chatbot hoạt động ngay trong ứng dụng, phục vụ đề tài và khai thác dữ liệu/tài liệu nghiệp vụ của chính hệ thống. Ví dụ: tra cứu trạng thái hồ sơ, thống kê hoặc giải đáp quy trình dựa trên nguồn được quản lý. Chỉ gắn hộp chat chung hoặc dẫn sang dịch vụ bên ngoài không đủ điều kiện.

Kiểm chứng và an toàn: tối đa +0,5. Chỉ xét khi chatbot đã tích hợp chạy được. Có bộ câu hỏi thử và kết quả đối chiếu; phải chỉ ra dữ liệu/nguồn dùng trả lời, xử lý trường hợp không có thông tin và không tiết lộ dữ liệu ngoài quyền người dùng. Backend kiểm soát truy vấn và thao tác; không cho chatbot tự thực thi SQL tùy ý hoặc lộ khóa API.

Không bắt buộc tự huấn luyện mô hình hoặc mua dịch vụ AI. Nhóm phải giải thích cách chatbot lấy dữ liệu, tạo câu trả lời và kiểm soát quyền.

## X. Gợi ý một số công cụ hỗ trợ có thể hữu ích

| Nhóm chức năng | Danh sách các công cụ |
| --- | --- |
| IDE & Tool Code Chính | Cursor, Antigravity, VS Code + GitHub |
|   | Copilot, Claude Code, Bolt.new, Replit |
| Thiết kế giao diện, usecase | Figma, Lovable.dev, Excalidraw, |
|   | Eraser.io, Google Stitch |
| Thiết kế & Quản lý Database | DrawDB, PgAdmin4, Prisma Studio, |
|   | Supabase, Neon.tech, MongoDB Atlas, |
|   | Dbdiagram |
| Máy ảo & Hosting Server | Vercel, Netlify, Render, Koyeb, Oracle |


|   | Cloud (Always Free Tier), Cloudflare |
| --- | --- |
|   | Workers |
| Tên miền & DNS Miễn phí | Subdomain mặc định (Vercel, Render, |
|   | Supabase), GitHub Student Developer |
|   | Pack, js.org, is-a.dev, Cloudflare DNS |

# assets

Ảnh nền cho màn hình danh sách buổi.

Thả ảnh toà nhà trường vào đây, đặt tên đúng một trong các tên sau:

```
campus.jpg   campus.jpeg   campus.png   campus.webp
```

`theme.py` tự tìm theo thứ tự đó, nhúng base64 vào CSS (Streamlit không phục vụ
file cục bộ cho `url()` trong CSS). Không có file → app dùng gradient navy thay thế
và ghi một dòng nhắc, không vỡ giao diện.

Khuyến nghị: bề ngang ≥ 2000px, nén dưới ~600KB. Ảnh nhúng base64 nằm trong HTML
nên ảnh nặng làm mỗi lần rerun chậm thấy được.

Slide bài giảng thật (nếu xin được) đặt ở `codebase/slides/<buổi>-<phần>.png`,
rồi sửa `render_slide()` trong `app.py` — hiện đang là khung giữ chỗ.

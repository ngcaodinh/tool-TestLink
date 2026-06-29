# TestLink Tool

> Web-based management UI for **TestLink 1.9.16** — a project that wraps the TestLink XML-RPC API and direct MySQL access into a modern, dashboard-driven workflow.

---

## ✨ Why this tool? / Tại sao cần tool này?

TestLink ships with a dated, Java-Server-Pages-style UI that is slow to navigate and cumbersome for daily QA work. This tool re-implements the same workflow on top of TestLink's official XML-RPC API (plus direct MySQL for read-heavy views), so you keep TestLink as the single source of truth while getting a faster, friendlier experience.

TestLink có UI cũ kiểu JSP, thao tác chậm và rườm rà cho công việc QA hằng ngày. Tool này xây dựng lại cùng quy trình trên XML-RPC API chính thức của TestLink (kết hợp MySQL trực tiếp cho các view đọc nhiều), giữ TestLink làm nguồn dữ liệu duy nhất nhưng mang lại trải nghiệm nhanh và thân thiện hơn.

### Benefits / Lợi ích

| Benefit / Lợi ích | What you get / Chi tiết |
| --- | --- |
| **Single dashboard** / **Dashboard tập trung** | Project, plan, suite, testcase counts and recent executions on one screen. <br> Số liệu project/plan/suite/testcase và các lần chạy gần nhất trên cùng một màn hình. |
| **Faster bulk operations** / **Thao tác hàng loạt nhanh hơn** | Create test cases one-by-one **or** paste a JSON array to create dozens at once. <br> Tạo test case từng cái **hoặc** dán JSON để tạo hàng chục case cùng lúc. |
| **Direct DB reads** / **Đọc DB trực tiếp** | Suites, requirements and executions are queried straight from MySQL — no per-item XML-RPC round trips. <br> Suite, requirement và execution được truy vấn thẳng từ MySQL — không gọi XML-RPC từng item. |
| **Word report export** / **Xuất báo cáo Word** | One click generates a fully formatted `.docx` with TOC, suite tree, test cases, steps, custom fields, requirements, per-step results and metrics. <br> Một cú click sinh file `.docx` đầy đủ: mục lục, cây suite, test case, steps, custom fields, requirement, kết quả từng step và metrics. |
| **Requirements traceability** / **Truy vết requirement** | Manage Requirement Specifications and link test cases to requirements for coverage tracking. <br> Quản lý Requirement Specification và liên kết test case với requirement để theo dõi độ phủ. |
| **Lightweight stack** / **Stack nhẹ** | Flask + MySQL connector + `python-docx`. No build step, no Node, no database migration tool. <br> Flask + MySQL connector + `python-docx`. Không build step, không Node, không cần công cụ migration. |

---

## 🚀 Quick start / Hướng dẫn chạy nhanh

### 1. Prerequisites / Yêu cầu

- **Python 3.8+**
- **XAMPP / WAMP / MAMP** — Apache + MySQL running locally
- **TestLink 1.9.16** installed and reachable at `http://localhost/testlink-1.9.16`
- MySQL credentials matching TestLink's database (defaults below)

### 2. Install / Cài đặt

```bash
cd testlink-tool
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
# source venv/bin/activate

pip install -r requirements.txt
```

Dependencies: `flask`, `mysql-connector-python`, `python-docx`, `python-dateutil`.

### 3. Configure / Cấu hình

Edit `config.py` if your TestLink DB credentials differ from defaults:

```python
TESTLINK_URL = "http://localhost/testlink-1.9.16/lib/api/xmlrpc/v1/xmlrpc.php"
DB_HOST = "localhost"
DB_USER = "testlink"
DB_PASS = "123456789"
DB_NAME = "testlink"
HOST = "0.0.0.0"
PORT = 5050
```

### 4. Get an API key / Lấy API key

1. Sign in to TestLink at `http://localhost/testlink-1.9.16`
2. Click your username → **My Settings** → **API Interface**
3. Copy the API key / Copy API key

### 5. Run / Chạy

```bash
python app.py
```

Open `http://localhost:5050`, click **Settings**, paste the API key, save.

Mở `http://localhost:5050`, vào **Settings**, dán API key, lưu.

---

## 🧭 Feature tour / Sơ lược tính năng

| Page / Trang | What it does / Chức năng |
| --- | --- |
| **Dashboard** | Project/plan/suite/testcase counts + recent executions. <br> Số liệu project/plan/suite/testcase + các lần chạy gần nhất. |
| **Test Projects** | Create and manage projects with prefixes used to build case IDs (e.g. `PRJ-1`). <br> Tạo và quản lý project với prefix dùng cho ID (ví dụ `PRJ-1`). |
| **Test Plans** | Plans per project, with notes for context. <br> Plan theo project, có ghi chú mô tả. |
| **Test Suites** | Hierarchical suite tree (parent / child). <br> Cây suite phân cấp (cha / con). |
| **Test Cases** | Single + JSON bulk creation. Steps, expected results, keywords, optional direct add to a plan. <br> Tạo đơn lẫn tạo hàng loạt bằng JSON. Steps, kết quả mong đợi, keywords, có thể thêm thẳng vào plan. |
| **Executions** | Record pass/fail/blocked/warning per test case per build. <br> Ghi nhận pass/fail/blocked/warning cho từng test case theo build. |
| **Requirements** | Requirement Specifications + Requirements + bulk assign test cases. <br> Requirement Specification + Requirement + gán hàng loạt test case. |
| **Export** | One-click Word report (see below). <br> Báo cáo Word một cú click (xem bên dưới). |

### Word report contents / Nội dung báo cáo Word

1. Table of contents / Mục lục
2. Report header (plan / project / build) / Thông tin báo cáo
3. Suite descriptions / Mô tả suite
4. Test case summary / Tóm tắt test case
5. Test case steps / Steps của test case
6. Author info / Thông tin tác giả
7. Keywords / Keywords
8. Test case custom fields / Custom fields của test case
9. Linked requirements / Requirement liên quan
10. Execution notes / Ghi chú thực thi
11. Per-step execution notes / Ghi chú từng step
12. Test results (color-coded) / Kết quả test (theo màu)
13. Per-step results / Kết quả từng step
14. Build custom fields / Custom fields của build
15. Metrics (pass/fail ratios) / Tổng hợp metrics

---

## 🛠 Troubleshooting / Xử lý sự cố

| Problem / Lỗi | Fix / Cách xử lý |
| --- | --- |
| Cannot connect to DB / Không kết nối được DB | Start MySQL, check `config.py` credentials, confirm `testlink` DB exists. <br> Bật MySQL, kiểm tra `config.py`, xác nhận DB `testlink` tồn tại. |
| XML-RPC errors / Lỗi XML-RPC | Confirm `http://localhost/testlink-1.9.16` is reachable, then re-save API key in **Settings**. <br> Xác nhận URL TestLink truy cập được, lưu lại API key trong **Settings**. |
| `Project/Plan/Suite not found` | API key user lacks permissions, or the project is inactive in TestLink. <br> User của API key thiếu quyền, hoặc project không active trong TestLink. |
| Word report fails / Báo cáo Word lỗi | `pip install -r requirements.txt` again, confirm `python-docx` installed, ensure selected plan exists. <br> Chạy lại `pip install -r requirements.txt`, xác nhận `python-docx`, đảm bảo plan tồn tại. |

---

## 📁 Project layout / Cấu trúc

```
testlink-tool/
├── app.py                 # Flask routes
├── api_client.py          # XML-RPC + direct MySQL access
├── report_generator.py    # Word (.docx) report builder
├── config.py              # Connection + server config
├── requirements.txt
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   ├── projects.html
│   ├── plans.html
│   ├── suites.html
│   ├── testcases.html
│   ├── executions.html
│   ├── requirements.html
│   ├── req_spec_detail.html
│   └── settings.html
└── static/
    └── style.css
```

---

## 🔌 TestLink API methods used

`createTestProject`, `getTestProjects`, `createTestPlan`, `getTestPlansForTestProject`, `createTestSuite`, `getFirstLevelTestSuitesForTestProject`, `createTestCase`, `addTestCaseToTestPlan`, `getTestCasesForTestPlan`, `createBuild`, `getBuildsForTestPlan`, `reportTCResult`, `getUser`.

Read-heavy views (suites tree, requirements, executions) go through MySQL directly for speed.

---

## 📜 License / Giấy phép

 Use freely with your own TestLink installation.
 Sử dụng tự do cùng cài đặt TestLink của bạn.

---

## 🙏 Acknowledgements

- [TestLink](https://testlink.org/) — the underlying test management system
- Built with [Flask](https://flask.palletsprojects.com/) and [python-docx](https://python-docx.readthedocs.io/)

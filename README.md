# Blog Management System — Tasks 2 & 7

A robust and high-performance Blog Management System built with **FastAPI**, featuring advanced security, intelligent caching, and real-time monitoring.

## 🚀 Features

### 🔐 Authentication & Security (Task 2)
- **JWT Dual-Token System:** Secure Access and Refresh token rotation.
- **Role-Based Access Control (RBAC):** Distinct permissions for Admins, Authors, and Readers.
- **Strict Validation:** Comprehensive input validation using Pydantic field validators.
- **Password Safety:** High-entropy hashing with Bcrypt.

### ⚡ Performance & Reliability (Task 7)
- **Intelligent Caching:** Custom In-memory TTL cache with automatic invalidation on data changes.
- **Request Middleware:** Automatic tracking of request latency and status codes.
- **Professional Logging:** Structured logs with rotation (App logs & Error logs).
- **Unit Testing:** 50+ tests covering Auth, CRUD, Caching, and Metrics.

### 📊 Monitoring Dashboard
- **Admin Only:** Real-time metrics dashboard available at `/metrics/dashboard`.
- **KPIs:** Live tracking of Uptime, Request Volume, Success Rate, and Latency.
- **Recent Requests:** Live log of the last 100 HTTP requests.

---

## 🛠 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MOHAMED-DONIA/Blog-Management-System.git
   cd Blog-Management-System
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

4. **Access Documentation:**
   Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger UI.

---

## 🧪 Testing
Run the comprehensive test suite:
```bash
python -m pytest tests/
```

---

## 📂 Project Structure
- `app/`: Main application logic (routes, models, services, core).
- `frontend/`: Dashboard HTML and static assets.
- `tests/`: Pytest suite for all modules.
- `logs/`: Application operation and error logs.

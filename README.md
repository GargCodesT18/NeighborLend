# NeighbourLend

NeighbourLend is a full-stack application featuring a FastAPI Python backend and a React (Vite) frontend.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Node.js** (v16 or higher recommended)
- **Python** (v3.8 or higher)
- **Git**

## Cloning the Repository

To get started, clone the repository to your local machine:

```bash
git clone <your-repository-url>
cd se
```

---

## 1. Backend Setup (FastAPI)

The backend is built with FastAPI and uses SQLAlchemy for database management.

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up Environment Variables:**
   Create a `.env` file in the `backend` directory based on your configuration needs (e.g., database connection string, secret keys).

6. **Run the backend server:**
   ```bash
   uvicorn main:app --reload
   ```
   *(Note: Replace `main:app` with the correct entry point if it differs in your project. The server typically runs on `http://localhost:8000`)*

---

## 2. Frontend Setup (React/Vite)

The frontend is built with React and Vite for fast development.

1. **Navigate to the frontend directory:**
   Open a new terminal window/tab, and from the root project folder, run:
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Set up Environment Variables (if required):**
   Create a `.env` file in the `frontend` directory if your frontend needs any API keys or configuration (e.g., `VITE_API_URL=http://localhost:8000`).

4. **Start the development server:**
   ```bash
   npm run dev
   ```
   *The frontend will typically run on `http://localhost:5173`.*

---

## Usage

Once both servers are running:
1. Open your browser and navigate to `http://localhost:5173` to view the frontend application.
2. The frontend will communicate with your local backend API running at `http://localhost:8000`.

## Database

The project currently uses a local database (`neighborlend.db`). Alembic can be used for database migrations if you make schema changes.

```bash
# To run migrations (if alembic is configured)
alembic upgrade head
```

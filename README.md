# Library Crowd Prediction System

A full-stack research project that predicts how crowded a library will be at a
given date/hour — **without any IoT hardware** (no cameras, no PIR/motion
sensors, no RFID gates). Instead, it uses a machine learning model trained on
time-context patterns (hour of day, weekday/weekend, exam periods, semester
breaks) to forecast occupancy. This is the project's **novelty**: zero extra
hardware cost, no privacy concerns from cameras, and it can be deployed using
data any library already has (or, as here, a realistic synthetic dataset).

සරලව කිවුවොත් — library එකේ occupancy predict කරන්න camera/sensor නැතුව,
කාලය-පදනම් pattern (hour, weekday/weekend, exam week, holiday) විශ්ලේෂණය
කරලා ML model එකකින් crowd level ගණනය කරනවා. මේකයි project එකේ novelty කොටස.

---

## Project structure

```
library-crowd-prediction/
├── dataset/
│   ├── generate_dataset.py       # generates synthetic historical data
│   └── library_occupancy.csv     # generated dataset (3360 rows)
├── model/
│   ├── train_model.py            # trains the RandomForest model
│   ├── library_crowd_model.pkl   # trained model (also copied into backend/)
│   └── metrics.json              # MAE / R2 evaluation results
├── backend/                      # FastAPI service
│   ├── main.py
│   ├── requirements.txt
│   ├── library_crowd_model.pkl
│   ├── metrics.json
│   └── .env.example
├── frontend/                     # React (Vite) dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   └── components/
│   │       ├── DayForecastChart.jsx
│   │       └── HistoryTable.jsx
│   ├── package.json
│   └── .env.example
└── supabase/
    └── schema.sql                # run this in Supabase SQL editor
```

---

## How the system works (research summary)

1. **Dataset (synthetic, since no IoT sensors exist):**
   `dataset/generate_dataset.py` builds an hourly occupancy dataset for 40
   weeks of a typical academic calendar. It encodes realistic behaviour:
   weekday lunch/evening peaks, quiet weekends, sharp spikes during exam
   weeks, and near-empty weeks during semester breaks, plus random noise.
   Output: `library_occupancy.csv` (3,360 hourly rows).

2. **Model:** `model/train_model.py` trains a `RandomForestRegressor`
   (scikit-learn) using 5 features — `hour`, `day_of_week`, `is_weekend`,
   `is_exam_period`, `is_semester_break` — to predict `occupancy_percent`.
   On a held-out 20% test split it reaches **R² ≈ 0.95, MAE ≈ 5.4%**.

3. **Backend (FastAPI, Python):** loads the trained model and exposes REST
   endpoints (`/predict`, `/predict/day`, `/history`, `/metrics`). Every
   prediction is logged to a **Supabase** Postgres table so you have a
   history of past forecasts.

4. **Frontend (React + Vite):** a dashboard where you pick a date/hour,
   see the predicted occupancy %, a full-day forecast chart, and recent
   prediction history pulled from Supabase.

5. **Database:** Supabase (hosted Postgres) — `supabase/schema.sql` creates
   the `predictions` table used for logging/history.

> **Note on the dataset:** Since this project intentionally avoids IoT
> sensors, there's no live ground-truth occupancy feed. The dataset here is
> synthetic but pattern-realistic, which is a normal and acceptable approach
> for a prototype/research project — just be sure to state this clearly as a
> **limitation** in your report, and mention that swapping in a real
> historical entry-log (student ID swipe records) would be the natural next
> step.

---

python --version

## Step-by-step: running the whole project

### 1. Get the code onto your machine
Unzip the project folder anywhere, e.g. `~/library-crowd-prediction`.

### 2. (Optional but recommended) Re-generate the dataset & retrain the model
The trained model is already included in `backend/`, so you can skip this —
but if you want to regenerate everything from scratch:

```bash
cd dataset
python3 generate_dataset.py        # creates library_occupancy.csv

cd ../model
pip install scikit-learn pandas joblib
python3 train_model.py             # creates library_crowd_model.pkl + metrics.json

# copy the fresh model into the backend
cp library_crowd_model.pkl metrics.json ../backend/
```

### 3. Set up Supabase (for history logging)
1. Create a free project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** → **New query**, paste the contents of
   `supabase/schema.sql`, and run it. This creates the `predictions` table.
3. Go to **Project Settings → API** and copy:
   - **Project URL** → this is `SUPABASE_URL`
   - **anon public key** → this is `SUPABASE_KEY`
     (for a quick local prototype the anon key is fine since the schema's
     RLS policy allows all access — tighten this before any real deployment)

### 4. Run the backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# now edit .env and paste your SUPABASE_URL and SUPABASE_KEY

uvicorn main:app --reload --port 8000
```

Check it's alive: open **http://localhost:8000** in a browser — you should
see a JSON message with `model_metrics` and `supabase_connected: true`.

Interactive API docs (auto-generated by FastAPI): **http://localhost:8000/docs**

### 5. Run the frontend (React)

Open a **new terminal** (keep the backend running):

```bash
cd frontend
npm install

cp .env.example .env
# by default VITE_API_BASE_URL=http://localhost:8000 — leave as-is
# unless your backend runs elsewhere

npm run dev
```

Open **http://localhost:5173** in your browser. You'll see the dashboard:
pick a date and hour, click **Generate forecast**, and you'll get:
- the predicted occupancy % for that exact hour
- a full-day bar chart (08:00–19:00)
- a running history table (pulled from Supabase)

### 6. Building for production (optional)

```bash
# frontend
cd frontend
npm run build      # outputs static files to frontend/dist/

# backend — run with a production server, e.g.:
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## API reference (backend)

| Method | Endpoint            | Description                                      |
|--------|----------------------|---------------------------------------------------|
| GET    | `/`                  | Health check + model metrics + Supabase status    |
| POST   | `/predict`           | Body: `{ "date": "YYYY-MM-DD", "hour": 8-19 }`     |
| GET    | `/predict/day`       | Query: `?date_str=YYYY-MM-DD` — full-day forecast |
| GET    | `/history?limit=50`  | Recent logged predictions from Supabase           |
| GET    | `/metrics`           | Model evaluation metrics (MAE, R²)                |

---

## Troubleshooting

- **"supabase_connected": false** on the `/` endpoint → your `.env` isn't
  being read. Make sure `backend/.env` exists (not just `.env.example`) and
  restart `uvicorn`.
- **CORS errors in the browser console** → confirm the backend is running on
  the same URL set in `frontend/.env` (`VITE_API_BASE_URL`).
- **`ModuleNotFoundError` when running the backend** → activate your virtual
  environment before `pip install -r requirements.txt`.
- **Exam/break dates don't match your real calendar** → edit
  `EXAM_DATE_RANGES` and `BREAK_DATE_RANGES` near the top of `backend/main.py`
  to match your institution's actual academic calendar.

---

## Extending this for a full research submission

- Swap the synthetic CSV for a real historical entry-log export if your
  library has one (same column names will work with minimal changes).
- Try additional models (XGBoost, LSTM for sequential/time-series patterns)
  and compare against the RandomForest baseline in your report.
- Add authentication (Supabase Auth) if multiple staff members will use the
  dashboard.
- Deploy the backend (Render/Railway/Fly.io) and frontend (Vercel/Netlify) so
  it's publicly accessible for your demo.

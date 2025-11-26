# 🎣 False Bay FisherAI  
### AI-Powered Fishing Planner for South Africa  

False Bay FisherAI supports region/area selection (Western/Eastern Cape, KZN, False Bay, Overberg, East London, etc.), multi-species planning, and a React frontend. It uses real weather + marine data and a lightweight AI/heuristic scorer to rank the best days and time windows.

---

# 🌟 Features

### ✔ Real-time forecast (future-only)  
Pulls wind, swell, sea temperature, tide trend via Open-Meteo (free, no key).

### ✔ AI + heuristics  
- Existing RandomForest per-species models (`/predict`)  
- New multi-species scorer over time windows (`/plan`)

### ✔ Regions & areas  
Metadata in `src/region_data.py` (Western Cape → False Bay/Overberg/West Coast; Eastern Cape → East London/Port Elizabeth/Wild Coast; KZN coast splits). Easy to extend.

### ✔ Multi-species planner  
Users select region → area → multiple species → date range (future). API ranks best day + window (dawn/morning/afternoon/evening) with legal notes per species/area.

### ✔ React frontend  
Vite + React (TypeScript) app in `/frontend` with bold, mobile-friendly UI.

### ✔ Presets + feedback  
Optional user ID (header) lets you save/load presets (`/user/presets`) and send quick thumbs feedback (`/feedback`) on ranking quality.

---

# 🧠 How It Works

## 1. Dataset generation  
`collect_data.py` fetches ~365 days of real weather/ocean data  
and applies CSV rules to label each day as Ideal/Good/Poor per species.

## 2. Model training  
`train_model.py` trains a RandomForest model for **each species**  
and saves them in `/models/`.

## 3. Prediction API  
`app.py` loads all models and exposes the `/predict` endpoint.

## 4. Front-end  
React app in `/frontend` calls `/meta/regions` and `/plan` (new UI replaces old static page).

---

# 📁 Project Structure

```
FalseBayFisherAI/
│
├── data/
│   ├── species_rules.csv
│   └── fisherai_dataset.csv
│
├── models/                # trained RF models (optional for /predict)
│   ├── galjoen_rf_model.pkl
│   └── ... (all species)
│
├── src/
│   ├── species_rules.py
│   ├── collect_data.py
│   ├── train_model.py
│   ├── region_data.py      # regions/areas + legal notes
│   ├── planner_service.py  # multi-species planner logic + Open-Meteo/OWM/Stormglass merge
│   ├── species_metadata.py # species time-of-day preferences
│   ├── app.py              # Flask API: /predict, /meta/regions, /plan, /user/presets, /feedback
│   └── requirements.txt
│
├── frontend/               # Vite React app (planner UI)
│
├── Procfile
├── .env (not committed)
└── README.md
```

---

# 🚀 Backend (Flask API)

1) Create virtual environment  
```
python3 -m venv venv
source venv/bin/activate
```

2) Install dependencies  
```
pip install -r src/requirements.txt
```

3) Optional keys  
- `.env`: `OWM_API_KEY` (historic backfill + wind), `STORMGLASS_API_KEY` (marine fallback), `WORLDTIDES_API_KEY` (tides), `SUPABASE_JWT_SECRET` (if you enable JWT auth).  
- `/plan` works with Open-Meteo even without keys.

4) Run the API  
```
python src/app.py
```
Endpoints:  
- `GET /predict?species=kob&date=2025-12-01` (uses trained RF models)  
- `GET /meta/regions` (regions + species list + defaults)  
- `POST /plan` → JSON `{region_id, area_id, species[], start_date, end_date}` (future-only)  
- `GET/POST /user/presets` (Bearer JWT if secret set, otherwise `X-User-Id` for dev)  
- `POST /feedback` (thumbs up/down on ranking)  
- Responses include source flags and window explanations; charts use `day_windows`.

---

# 🖥 Frontend (React + Vite)
```
cd frontend
npm install
npm run dev   # http://localhost:5173
```
`frontend/.env`: set `VITE_API_BASE=http://localhost:5000` (or your deployed API).  
Build: `npm run build` → deploy `frontend/dist` to Vercel/Netlify. CORS on backend should allow your frontend origin.

---

# 🌎 Deployment (suggested)
- Backend: Render/Fly/Railway with `python src/app.py` (Procfile included). Add env vars you need.
- Frontend: Vercel/Netlify from `/frontend` build output. Set `VITE_API_BASE=https://your-api-domain`.
- Auth: Supabase/Auth0 can be added later; for now presets/feedback work with `X-User-Id`.

---

# 🐟 Future Improvements
- Persist presets/history in a DB (Supabase/Postgres)
- Feedback-driven weight tuning or small model training
- Add more secondary APIs (Stormglass/WorldTides) with stronger merge logic
- Expand legal rules and add charts per result (wind/tide) — charts already enabled via Recharts

---

# 👤 Author  
**Your Name**  
False Bay, Cape Town  
Github: @YOUR_USERNAME

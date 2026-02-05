# Database trigger with websocket (WS) and server side event (SSE)


## Backend
Backend uses `FastApi`. It handles count increment requests from clients to update database, retrieves and returns the latests count value, sets up a listener for a PostgreSQL trigger on table change and broadcasts the latest count value to all WS and SSE clients.

Backend server runs on http://localhost:8000/.

### Backend prequisitions
* PostgreSQL >= 18.1
* Python >= 3.12

### 🚀 Quick Start
1. With optional [Anaconda](https://www.anaconda.com/) installed, run `backend/setup.sh`. If not, run `pip3 install -r backend/requirements.txt`.
2. Run `backend/database/setup.sh` to create required database and table.
3. To start up backend, `python backend/main.py`.
4. To teardown `conda` environment, run `backend/teardown.sh`.

## Frontend
Upon loading, it retrieves the latest count value. It has a button to increment the count in a database table and receives a push from backend. The only difference between SSE and WS is that SSE uses a `EventSource` to receive the latest count value, while WS uses a `Websocket`.

SSE frontend runs on http://localhost:4000/.<br>
WS frontend runs on http://localhost:3000/.

### Frontend prequisitions
* node >= 24.13

### 🚀 Quick Start
1. `npm install` inside `frontend_sse` and `frontend_ws` folder.
2. `npm run start` inside `frontend_sse` and `frontend_ws` folder.

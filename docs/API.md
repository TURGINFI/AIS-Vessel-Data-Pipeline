# API Reference

FastAPI publishes the interactive OpenAPI documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## REST Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health and version. |
| `GET` | `/api/vessels` | Latest known position for every active vessel. |
| `GET` | `/api/vessels/{mmsi}` | Latest vessel details and history count. |
| `GET` | `/api/vessels/{mmsi}/history` | Recent stored AIS trajectory for one vessel. |
| `GET` | `/api/vessels/{mmsi}/prediction` | On-demand future trajectory for one vessel. |
| `GET` | `/api/system/status` | Ingestion, storage, and WebSocket status. |

## WebSocket

`/ws/vessels` streams live vessel updates from the backend.

Example message:

```json
{
  "type": "vessel_update",
  "data": {
    "mmsi": "230123456",
    "latitude": 60.0515,
    "longitude": 24.7425,
    "timestamp": "2026-08-10T12:00:00Z",
    "speed": 17.8,
    "course": 96.0,
    "heading": 96.0,
    "vessel_name": "Baltic Aurora",
    "vessel_type": "Cargo",
    "source": "replay"
  }
}
```


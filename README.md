# Travel Companion

AI-powered travel itinerary generator using Azure OpenAI and Google APIs.

## Features

- 🤖 **AI-Powered Planning**: Intelligent itinerary generation based on your interests
- 🗺️ **Smart Routing**: Optimized visit order using TSP algorithms to minimize walking
- ⏰ **Real-Time Data**: Actual opening hours, ratings, and travel times from Google APIs
- 📍 **Interactive Maps**: Visualize your itinerary with route polylines
- 🎯 **Personalized**: Match your preferred pace (relaxed/moderate/packed)

## Architecture

This project uses a **hybrid AI + deterministic** approach:

- **AI Layer (Azure OpenAI)**: Selection, theming, creative tips
- **Deterministic Layer**: Route optimization, schedule building, time calculations

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI**: Azure OpenAI GPT-4
- **APIs**: Google Places API (New), Google Routes API
- **Validation**: Pydantic v2

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS
- **Maps**: Google Maps JavaScript API

## Prerequisites

- Python 3.11+
- Node.js 18+
- Azure OpenAI API access
- Google Cloud account with Places and Routes APIs enabled

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd travel-companion
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API keys
```

### 4. Run Development Servers

**Backend** (from `/backend`):
```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend** (from `/frontend`):
```bash
npm run dev
```

Open http://localhost:5173 in your browser.

## Configuration

### Backend Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., "gpt-4") |
| `GOOGLE_PLACES_API_KEY` | Google Places API key |
| `GOOGLE_ROUTES_API_KEY` | Google Routes API key |

### Frontend Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key |

## API Endpoints

### POST /api/itinerary
Generate a travel itinerary.

**Request:**
```json
{
  "destination": "Paris, France",
  "start_date": "2026-03-15",
  "end_date": "2026-03-18",
  "interests": ["art", "food", "history"],
  "pace": "moderate"
}
```

### GET /health
Health check endpoint.

## Project Structure

```
travel-companion/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic
│   │   └── routers/             # API endpoints
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/            # API client
│   │   └── types/               # TypeScript types
│   └── package.json
├── ARCHITECTURE.md              # Design documentation
└── README.md
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (when added)
cd frontend
npm test
```

### Code Formatting

```bash
# Backend
cd backend
black .
isort .

# Frontend
cd frontend
npm run lint
```

## License

MIT

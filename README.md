# Advanced AI Trading Journal

An intelligent trading journal specifically designed for Indian Equity & F&O traders. This full-stack application helps you log, analyze, and improve your trading performance with realized P&L tracking, AI-powered insights, and analytics.

See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for verified behavior, fixes, validation results, and remaining limitations. Tax and brokerage calculations have been removed.

## 🚀 Features

### Core Functionality
- **Multi-Format Trade Ingestion**: Upload Zerodha Console Tradebook CSV files
- **Manual Trade Logging**: Log trades with strategy tags, emotion tracking, and notes
- **Trade Coach**: Local evidence-based reviews, book-inspired practice plans, and optional Gemini/Groq/OpenRouter commentary
- **Performance Analytics**: Win rates, PnL tracking, segment filtering
- **Multi-Segment Support**: Equity, Futures, CE/PE Options

### Smart Features
- **Realized P&L**: Matched execution profits and losses without tax or brokerage calculations
- **Strategy Tracking**: Tag trades by strategy and analyze performance
- **Emotion Logging**: Track emotional state during trades for psychological analysis
- **Advanced Filtering**: Filter by segment, emotion, strategy tags
- **Refresh**: Clear all previous trades, filters, and analysis results to start fresh

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (local) + Firebase (cloud)
- **AI Integration**: Google Gemini API
- **Data Processing**: Pandas
- **Testing**: Pytest

### Frontend
- **Framework**: Next.js 16 with React 19
- **Styling**: Tailwind CSS 4
- **UI Components**: Lucide React icons
- **Charts**: Recharts
- **State Management**: React hooks

## 📋 Prerequisites

- Python 3.10+
- Node.js 20.9+
- npm or yarn
- (Optional) Google Gemini API key for AI features
- (Optional) Firebase service account for cloud sync

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/chinmaykalokhe80-ui/ai-trading-journal.git
cd ai-trading-journal
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.local.example .env.local
# Edit .env.local with your API URL
```

## 🚀 Quick Start

### Using the Start Script (Recommended)

```bash
# From project root
./start.sh
```

This will:
- Start the FastAPI backend on `http://localhost:8000`
- Start the Next.js frontend on `http://localhost:3000`

### Manual Start

```bash
# Terminal 1: Start Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Frontend
cd frontend
npm run dev
```

### Stop the Application

```bash
./stop.sh
```

## ⚙️ Configuration

### Backend Environment Variables (.env)

```env
# Application
ENVIRONMENT=development
SQLITE_DB_PATH=trading_journal.db

# Firebase (Optional - for cloud sync)
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/service-account.json

# Zerodha API (Optional - for future API integration)
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret

# Google Gemini AI (Optional - for AI insights)
GEMINI_API_KEY=your_gemini_api_key
```

### Frontend Environment Variables (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## 📖 Usage

### 1. Upload Zerodha Tradebook CSV

1. Navigate to the web interface at `http://localhost:3000`
2. Click "Upload Zerodha CSV"
3. Select your Zerodha Console Tradebook CSV file
4. The system will automatically:
   - Parse the CSV
   - Calculate realized P&L
   - Group fills into legs and trades
   - Save to database
   - Display in the trade table

### 2. Log Manual Trades

1. Click "Log Manual Trade"
2. Enter trade details:
   - Strategy tag
   - Emotion tag
   - Notes
   - Planned stop loss and target
   - Trade legs (instrument, segment, side, price, quantity)
3. The system calculates realized P&L without fee deductions

### 3. Review trades and improve

Click **Analyze saved trades** for an assessment of all closed journal records, or upload a P&L CSV/Excel report for read-only analysis. Reviews show strengths, weaknesses, supporting numbers, and measurable practice goals. Local rules are the default; optional external reviewers are selected explicitly.

See [TRADE_COACH.md](TRADE_COACH.md) for methodology, book principles, free-tier providers, privacy, and setup. See [YOUR_TRADE_REVIEW.md](YOUR_TRADE_REVIEW.md) for the assessment of the saved records at implementation time.

### 4. View and Filter Trades

- Use the filter toolbar to filter by:
  - Segment (Equity, CE, PE, Futures)
  - Emotion (Neutral, FOMO, Revenge, Confident, etc.)
- View aggregated metrics:
  - Realized P&L
  - Win rate
  - Total trades

## 🔌 API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Key Endpoints

- `POST /api/ingest/csv` - Upload and ingest Zerodha CSV
- `GET /api/trades` - List all trades with filtering
- `POST /api/trades` - Create manual trade
- `PATCH /api/trades/{trade_id}` - Update trade details
- `DELETE /api/trades` - Clear all trades
- `POST /api/ai-coach/analyze-csv` - Analyze a report (local rules by default)
- `POST /api/ai-coach/analyze-journal` - Review closed saved records
- `GET /api/ai-coach/providers` - List optional reviewer availability

## 🧪 Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build -- --webpack
```

## 📁 Project Structure

```
ai-trading-journal/
├── backend/
│   ├── app/
│   │   ├── core/              # Business logic
│   │   │   ├── ai_analyzer.py    # AI insights
│   │   │   ├── pnl.py            # Realized P&L
│   │   │   └── kite_stub.py       # Zerodha stub
│   │   ├── database/          # Data layer
│   │   │   ├── sqlite_db.py      # Local SQLite
│   │   │   └── firestore.py      # Firebase sync
│   │   ├── parsers/           # CSV parsers
│   │   │   ├── base.py           # Base parser
│   │   │   └── zerodha.py        # Zerodha parser
│   │   ├── routers/           # API endpoints
│   │   │   ├── ingest.py         # Trade ingestion
│   │   │   ├── trades.py         # Trade CRUD
│   │   │   └── ai_coach.py       # AI analysis
│   │   ├── config.py          # Configuration
│   │   └── main.py            # FastAPI app
│   ├── tests/                 # Backend tests
│   └── .venv/                 # Python virtual environment
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js app
│   │   ├── components/       # React components
│   │   └── lib/             # Utilities and API client
│   ├── public/               # Static assets
│   └── package.json
├── start.sh                  # Start script
├── stop.sh                   # Stop script
└── README.md                 # This file
```

## 🔒 Security Notes

- **Never commit API keys** to the repository
- Use environment variables for sensitive configuration
- The `.gitignore` file excludes sensitive files
- For production, use proper secret management
- Consider implementing authentication for multi-user scenarios

## 🚧 Roadmap

### Phase 1: Multi-Broker Integration
- [ ] Zerodha API integration
- [ ] Upstox API integration
- [ ] Angel One API integration
- [ ] Unified broker dashboard

### Phase 2: Advanced Features
- [ ] Real-time position tracking
- [ ] Live market data integration
- [ ] Advanced performance analytics
- [ ] Strategy backtesting
- [ ] Risk management tools

### Phase 3: User Experience
- [ ] Mobile-responsive design improvements
- [ ] Mobile app (React Native)
- [ ] Enhanced visualizations
- [ ] Export functionality
- [ ] Tax reporting

### Phase 4: Enterprise Features
- [ ] Multi-user authentication
- [ ] Team collaboration
- [ ] Advanced permissions
- [ ] Audit logging
- [ ] API rate limiting

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is private and proprietary. All rights reserved.

## 🙏 Acknowledgments

- AI insights powered by Google Gemini
- Built with FastAPI, Next.js, and modern web technologies

## 📞 Support

For issues, questions, or suggestions, please open an issue in the repository.

---

**Note**: This trading journal is designed for educational and analytical purposes. Tax and brokerage calculations are not included.

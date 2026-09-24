# Advanced AI Trading Journal

An intelligent trading journal specifically designed for Indian Equity & F&O traders. This full-stack application helps you log, analyze, and improve your trading performance with automated charge calculation, AI-powered insights, and comprehensive analytics.

## 🚀 Features

### Core Functionality
- **Multi-Format Trade Ingestion**: Upload Zerodha Console Tradebook CSV files
- **Manual Trade Logging**: Log trades with strategy tags, emotion tracking, and notes
- **Automated Charges Calculation**: Indian market-specific tax calculation including:
  - STT (Securities Transaction Tax)
  - GST (Goods and Services Tax)
  - SEBI Charges
  - Stamp Duty
  - DP Charges
  - Exchange Transaction Charges
- **AI Trading Coach**: Google Gemini-powered behavioral analysis and insights
- **Performance Analytics**: Win rates, PnL tracking, segment filtering
- **Multi-Segment Support**: Equity, Futures, CE/PE Options

### Smart Features
- **Real-time PnL Calculation**: Gross and net PnL with accurate tax deductions
- **Strategy Tracking**: Tag trades by strategy and analyze performance
- **Emotion Logging**: Track emotional state during trades for psychological analysis
- **Advanced Filtering**: Filter by segment, emotion, strategy tags
- **Tax-Ready Outputs**: Detailed breakdown of all charges and taxes

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

- Python 3.8+
- Node.js 18+
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
pip install fastapi uvicorn sqlalchemy pandas firebase-admin google-generativeai python-multipart python-dotenv pydantic-settings requests pytest

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
   - Calculate all Indian market charges
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
3. The system calculates charges and PnL automatically

### 3. Analyze with AI Coach

1. Upload a PnL CSV or Excel file
2. The AI coach analyzes:
   - Win rates and profit distribution
   - Risk-reward patterns
   - Behavioral insights
   - CE vs PE performance
   - Day-of-week patterns
3. Get actionable recommendations

### 4. View and Filter Trades

- Use the filter toolbar to filter by:
  - Segment (Equity, CE, PE, Futures)
  - Emotion (Neutral, FOMO, Revenge, Confident, etc.)
- View aggregated metrics:
  - Net PnL (post-charges)
  - Gross PnL (pre-charges)
  - Total charges and taxes
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
- `POST /api/ai-coach/analyze-csv` - Analyze PnL with AI
- `GET /api/charges-config` - Get current charges configuration

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
npm test
```

## 📁 Project Structure

```
ai-trading-journal/
├── backend/
│   ├── app/
│   │   ├── core/              # Business logic
│   │   │   ├── ai_analyzer.py    # AI insights
│   │   │   ├── charges_engine.py # Tax calculation
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

- Indian tax rates based on official NSE/BSE regulations
- AI insights powered by Google Gemini
- Built with FastAPI, Next.js, and modern web technologies

## 📞 Support

For issues, questions, or suggestions, please open an issue in the repository.

---

**Note**: This trading journal is designed for educational and analytical purposes. Always verify tax calculations with official broker statements before using for tax filing.

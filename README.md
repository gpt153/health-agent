# AI Health Coach - Telegram Bot

Adaptive AI fitness and nutrition coach via Telegram that learns your preferences and helps you track your health goals.

## 🚀 Quick Start

### 1. Get Your Telegram User ID

1. Open Telegram
2. Message [@userinfobot](https://t.me/userinfobot)
3. Copy your user ID (it's a number like `123456789`)

### 2. Configure the Bot

Edit `.env` file and add your Telegram user ID:

```bash
ALLOWED_TELEGRAM_IDS=YOUR_USER_ID_HERE
```

### 3. Start the Bot

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure PostgreSQL is running (already started)
docker compose ps

# Run the bot
python -m src.main
```

### 4. Test in Telegram

1. Find your bot in Telegram (search for the bot username)
2. Send `/start` to begin
3. Try sending a message or photo!

## 🛠️ Development

For detailed development setup, architecture explanation, and SCAR integration:

**[📖 See DEVELOPMENT.md](DEVELOPMENT.md)**

This covers:
- Production vs Development modes
- Native API setup for fast iteration
- SCAR testing workflow
- Troubleshooting common issues

## 📋 Current Features (MVP)

✅ **Working:**
- `/start` command - Initialize bot and create your account
- User authentication via whitelist
- Database storage for users
- Memory file system (markdown files for your data)
- Message handling (echo mode)
- Photo handling (acknowledgment mode)

🚧 **Coming Soon:**
- AI-powered conversations with PydanticAI
- Food photo analysis with vision AI
- Dynamic tracking categories
- Scheduled reminders
- Adaptive personality based on your preferences

## 🛠️ Development

### Database Already Setup

PostgreSQL is running in Docker with the schema created.

To verify:

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d health_agent -c "\dt"
```

### Project Structure

```
src/
├── config.py           # Configuration management
├── main.py            # Application entry point
├── bot.py             # Telegram bot setup
├── models/            # Pydantic models
├── db/                # Database layer
├── memory/            # User memory system
└── utils/             # Utilities (auth, nutrition, vision)
```

## 🔐 Environment Variables

See `.env.example` for all available configuration options.

**Required:**
- `TELEGRAM_BOT_TOKEN` - ✅ Already configured
- `ALLOWED_TELEGRAM_IDS` - ⚠️ **ADD YOUR USER ID HERE**
- `DATABASE_URL` - ✅ Already configured

## 🐛 Troubleshooting

**Bot not responding?**
- Check your user ID is in `ALLOWED_TELEGRAM_IDS`
- Make sure PostgreSQL is running: `docker compose ps`

**Database connection error?**
- PostgreSQL is running on localhost:5432
- Check with: `docker compose logs postgres`

# AI Diet Coach

An AI-powered diet coaching application that provides personalized nutrition advice and diet plans.

## Features

- Bilingual support (English/French)
- Personalized diet plan generation
- Progress tracking and plan adjustments
- WhatsApp integration for easy communication
- Secure data storage with Supabase

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/aicoach.git
cd aicoach
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:
```env
DEEPSEEK_API_KEY=your_deepseek_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
WHATSAPP_VERIFY_TOKEN=your_whatsapp_verify_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
```

5. Initialize the database:
```bash
psql -U your_username -d your_database -a -f schema.sql
```

## Usage

1. Start the application:
```bash
python run.py
```

2. The API will be available at `http://localhost:8000`

3. Available endpoints:
- `POST /conversation`: Send a message to the AI coach
- `GET /webhook/whatsapp`: WhatsApp webhook verification
- `POST /webhook/whatsapp`: WhatsApp message handling

## Project Structure

```
aicoach/
├── README.md
├── .env                 (create this, not versioned)
├── requirements.txt
├── run.py
├── main.py
├── schema.sql
├── data/
│   ├── __init__.py
│   ├── database.py     (database operations)
│   ├── models.py       (data models)
│   └── validators.py   (data validation)
├── managers/
│   ├── __init__.py
│   ├── flow_manager.py (conversation flow)
│   ├── prompt_manager.py (prompt templates)
│   └── state_manager.py (state management)
├── prompts/
│   ├── __init__.py
│   ├── diet_plan.py    (diet plan prompts)
│   ├── follow_up.py    (follow-up prompts)
│   └── introduction.py (introduction prompts)
├── services/
│   ├── __init__.py
│   ├── whatsapp_service.py (WhatsApp integration)
│   ├── ai_service.py    (AI model interaction)
│   ├── chat_service.py  (chat processing)
│   └── conversation_service.py (conversation management)
└── api/
    ├── __init__.py
    └── routes.py       (API routes)
```

## Development

- Use Python 3.8 or higher
- Follow PEP 8 style guide
- Write docstrings for all functions and classes
- Add type hints
- Handle errors gracefully
- Log important events

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.


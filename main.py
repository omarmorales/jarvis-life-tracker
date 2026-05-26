import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# FastAPI Imports
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Telegram Imports
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# OpenAI Import
from openai import AsyncOpenAI

# Database Integration
import database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory dictionary to store conversation history per chat_id
user_sessions = {}

# Security: Only allow this user
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
if ALLOWED_USER_ID:
    try:
        ALLOWED_USER_ID = int(ALLOWED_USER_ID)
    except ValueError:
        logger.error("ALLOWED_USER_ID must be a number. Setting to None to block unauthorized access.")
        ALLOWED_USER_ID = None

# Define the tools for OpenAI (Expenses + Workouts)
tools = [
    {
        "type": "function",
        "function": {
            "name": "save_expense",
            "description": "Save an expense to the database. Use this when the user mentions buying something, spending money, or tracking an expense.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The monetary amount of the expense."
                    },
                    "category": {
                        "type": "string",
                        "description": "The category of the expense (e.g., Food, Transport, Utilities, Entertainment, Housing, Shopping)."
                    },
                    "payment_method": {
                        "type": "string",
                        "description": "The method of payment (e.g., cash, card, transfer). Default is 'unknown' if not specified."
                    },
                    "currency": {
                        "type": "string",
                        "description": "The currency code of the expense (e.g. 'MXN', 'USD', 'EUR'). Default to 'MXN' if not specified or implied."
                    },
                    "description": {
                        "type": "string",
                        "description": "A short description of the item bought."
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional date of the expense in YYYY-MM-DD format if mentioned (e.g., yesterday). Defaults to today if null."
                    }
                },
                "required": ["amount", "category", "payment_method", "description"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses",
            "description": "Query the database to get past expenses. Use this when the user asks how much they spent, or wants to see their expenses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category to filter by (e.g., 'Food'). Leave null if not specified."
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days back to search. Default is 30. Use larger numbers (e.g. 365) if they ask for this year."
                    }
                }
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_expense",
            "description": "Delete an expense from the database by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {
                        "type": "integer",
                        "description": "The unique ID of the expense to delete."
                    }
                },
                "required": ["expense_id"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_expense",
            "description": "Edit an existing expense in the database by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {
                        "type": "integer",
                        "description": "The unique ID of the expense to edit."
                    },
                    "amount": { "type": "number", "description": "New amount." },
                    "category": { "type": "string", "description": "New category." },
                    "description": { "type": "string", "description": "New description." },
                    "payment_method": { "type": "string", "description": "New payment method." },
                    "currency": { "type": "string", "description": "New currency code (e.g. 'MXN', 'USD')." },
                    "date": { "type": "string", "description": "New date in YYYY-MM-DD format." }
                },
                "required": ["expense_id"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_workout",
            "description": "Save an exercise or workout log to the database. Use this when the user mentions running, lifting weights, gym sessions, swimming, or doing any physical activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_type": {
                        "type": "string",
                        "description": "The type of workout (e.g., Running, Weightlifting, Cycling, Swimming, Yoga, Walking)."
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "The duration of the workout in minutes if mentioned."
                    },
                    "intensity": {
                        "type": "string",
                        "description": "The intensity of the workout (low, medium, high) if mentioned."
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description or notes about the workout (e.g., 'Leg day', 'Ran 5k in 25 mins')."
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional date of the workout in YYYY-MM-DD format if mentioned (e.g., yesterday). Defaults to today if null."
                    }
                },
                "required": ["workout_type"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_workout_logs",
            "description": "Query the database to get past workout or exercise logs. Use this when the user asks how much they worked out, or wants to see their workouts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_type": {
                        "type": "string",
                        "description": "Optional workout type to filter by (e.g., 'Running'). Leave null if not specified."
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days back to search. Default is 30."
                    }
                }
            },
        }
    }
]

# ==========================================
# MESSAGE CHUNKING & UTILITY FUNCTIONS
# ==========================================

def split_message(text: str, max_length: int = 4000) -> list[str]:
    """Splits a text into chunks of maximum max_length, trying to split on newlines."""
    if not text:
        return []
    if len(text) <= max_length:
        return [text]
        
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Split by lines
    lines = text.split('\n')
    for line in lines:
        # If a single line is longer than max_length, split it by characters
        if len(line) > max_length:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split line into chunks
            for i in range(0, len(line), max_length):
                chunks.append(line[i:i+max_length])
            continue
            
        if current_length + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
            
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
        
    return chunks

async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, edit_message_id: int = None):
    """Sends a long message by splitting it into chunks.
    
    If edit_message_id is provided, the first chunk will edit that message.
    Subsequent chunks are sent as new messages.
    """
    chunks = split_message(text)
    if not chunks:
        chunks = ["I couldn't understand that."]
        
    first_chunk = chunks[0]
    if edit_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=first_chunk
            )
        except Exception as e:
            logger.error(f"Failed to edit message {edit_message_id}: {e}. Sending as new message instead.")
            await context.bot.send_message(chat_id=chat_id, text=first_chunk)
    else:
        await context.bot.send_message(chat_id=chat_id, text=first_chunk)
        
    for chunk in chunks[1:]:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


# ==========================================
# TELEGRAM COMMAND & MESSAGE HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    if not ALLOWED_USER_ID:
        logger.error("Access denied: ALLOWED_USER_ID is not configured.")
        await update.message.reply_text("Security Error: Bot is not configured. Please set ALLOWED_USER_ID in .env.")
        return
        
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access attempt by user {user.id} ({user.username or 'No Username'}).")
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return
        
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am **JARVIS**, your unified AI personal life assistant. "
        "Send me your expenses (e.g., 'Spent $5 on a coffee') or workouts (e.g., 'Ran 5k in 25 minutes') and I will track them! "
        "You can also ask me questions like 'How much did I spend this week?' or 'What workouts did I do recently?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user message using OpenAI and trigger actions if needed."""
    user = update.effective_user
    
    if not ALLOWED_USER_ID:
        logger.error("Access denied: ALLOWED_USER_ID is not configured.")
        await update.message.reply_text("Security Error: Bot is not configured. Please set ALLOWED_USER_ID in .env.")
        return
        
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access attempt by user {user.id} ({user.username or 'No Username'}).")
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Let the user know we are processing
    processing_msg = await update.message.reply_text("Processing...")
    
    try:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Initialize session for this user if it doesn't exist
        if chat_id not in user_sessions:
            user_sessions[chat_id] = [
                {
                    "role": "system",
                    "content": ""
                }
            ]
        
        # Always update system prompt with latest date and rules
        user_sessions[chat_id][0]["content"] = (
            f"You are JARVIS, a unified personal tracking assistant. Current date and time is {current_date}. "
            "You help the user log their physical workouts and their financial expenses in a single chat. "
            "If the user is tracking an expense, use the save_expense tool. "
            "IMPORTANT: The save_expense tool requires a payment_method (e.g., cash, card, transfer). "
            "If the user DOES NOT specify how they paid, politely ask them before calling the tool. "
            "If the user mentions an expense with a specific currency (e.g. pesos, MXN, dollars, USD, EUR), extract it and supply it to the tool. "
            "Otherwise, default to 'MXN'. When reporting expenses, always accompany amounts with their currency code (e.g. 115 MXN or $50 USD). "
            "If the user is tracking a workout or exercise, use the save_workout tool. "
            "If the user asks about past expenses, use the get_expenses tool. "
            "If the user asks about past workouts, use the get_workout_logs tool. "
            "If they ask for a general summary of their life or logs, you can call both get_expenses and get_workout_logs. "
            "If the user asks to edit or delete an expense, use get_expenses first to find its ID. "
            "BEFORE deleting an expense, ALWAYS ask the user for confirmation (e.g., 'Are you sure you want to delete the coffee?'). "
            "Only call delete_expense after they say yes. Otherwise, reply conversationally."
        )
        
        # Add the new user message to history
        user_sessions[chat_id].append({"role": "user", "content": user_text})
        
        # Keep history from growing too large (keep system prompt + last 12 messages)
        if len(user_sessions[chat_id]) > 13:
            user_sessions[chat_id] = [user_sessions[chat_id][0]] + user_sessions[chat_id][-12:]
            
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=user_sessions[chat_id],
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            # Add the assistant's tool call message to the context
            user_sessions[chat_id].append(message)
            
            for tool_call in message.tool_calls:
                if tool_call.function.name == "save_expense":
                    args = json.loads(tool_call.function.arguments)
                    
                    # Save to DB
                    expense = database.add_expense(
                        amount=args["amount"],
                        category=args["category"],
                        description=args["description"],
                        payment_method=args.get("payment_method", "unknown"),
                        currency=args.get("currency", "MXN"),
                        date_str=args.get("date")
                    )
                    
                    tool_response = f"Successfully saved expense: id={expense.id}, amount={expense.amount}, currency={expense.currency}, category={expense.category}, description={expense.description}, payment_method={expense.payment_method}, date={expense.date.strftime('%Y-%m-%d')}"
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "save_expense", "content": tool_response})
                    
                elif tool_call.function.name == "get_expenses":
                    args = json.loads(tool_call.function.arguments)
                    category = args.get("category")
                    days_back = args.get("days_back", 30)
                    
                    # Query DB
                    expenses = database.get_expenses(category=category, days_back=days_back)
                    
                    if not expenses:
                        tool_response = "No expenses found for the given criteria."
                    else:
                        lines = [f"- [ID: {e.id}] {e.date.strftime('%Y-%m-%d')}: {e.amount:.2f} {e.currency} for {e.description} ({e.category}) paid via {e.payment_method}" for e in expenses]
                        
                        # Build currency sum dictionary
                        curr_totals = {}
                        for e in expenses:
                            curr_totals[e.currency] = curr_totals.get(e.currency, 0.0) + e.amount
                        totals_str = ", ".join([f"{amt:.2f} {curr}" for curr, amt in curr_totals.items()])
                        
                        tool_response = f"Found {len(expenses)} expenses totaling {totals_str}:\n" + "\n".join(lines)
                        
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "get_expenses", "content": tool_response})
                    
                elif tool_call.function.name == "delete_expense":
                    args = json.loads(tool_call.function.arguments)
                    success = database.delete_expense(args["expense_id"])
                    tool_response = "Expense deleted successfully." if success else "Expense not found."
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "delete_expense", "content": tool_response})
                    
                elif tool_call.function.name == "edit_expense":
                    args = json.loads(tool_call.function.arguments)
                    expense = database.edit_expense(
                        expense_id=args["expense_id"],
                        amount=args.get("amount"),
                        category=args.get("category"),
                        description=args.get("description"),
                        payment_method=args.get("payment_method"),
                        currency=args.get("currency"),
                        date_str=args.get("date")
                    )
                    if expense:
                        tool_response = f"Successfully updated expense: id={expense.id}, amount={expense.amount}, currency={expense.currency}, category={expense.category}, description={expense.description}, payment_method={expense.payment_method}, date={expense.date.strftime('%Y-%m-%d')}"
                    else:
                        tool_response = "Expense not found."
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "edit_expense", "content": tool_response})

                elif tool_call.function.name == "save_workout":
                    args = json.loads(tool_call.function.arguments)
                    
                    # Save to DB
                    workout = database.add_workout_log(
                        workout_type=args["workout_type"],
                        duration_minutes=args.get("duration_minutes"),
                        intensity=args.get("intensity"),
                        description=args.get("description"),
                        date_str=args.get("date")
                    )
                    
                    tool_response = f"Successfully saved workout log: id={workout.id}, type={workout.workout_type}, duration={workout.duration_minutes or 'unknown'} mins, intensity={workout.intensity or 'unknown'}, date={workout.date.strftime('%Y-%m-%d')}"
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "save_workout", "content": tool_response})

                elif tool_call.function.name == "get_workout_logs":
                    args = json.loads(tool_call.function.arguments)
                    workout_type = args.get("workout_type")
                    days_back = args.get("days_back", 30)
                    
                    # Query DB
                    workouts = database.get_workout_logs(workout_type=workout_type, days_back=days_back)
                    
                    if not workouts:
                        tool_response = "No workout logs found for the given criteria."
                    else:
                        lines = [f"- [ID: {w.id}] {w.date.strftime('%Y-%m-%d')}: {w.workout_type} ({w.duration_minutes or 0} mins, {w.intensity or 'normal'} intensity) - {w.description or 'No notes'}" for w in workouts]
                        tool_response = f"Found {len(workouts)} workout logs:\n" + "\n".join(lines)
                        
                    user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "get_workout_logs", "content": tool_response})

            # Call OpenAI again with the tool response so it can generate a natural language reply
            final_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=user_sessions[chat_id]
            )
            
            # Save final response to history
            user_sessions[chat_id].append(final_response.choices[0].message)
            
            await send_long_message(
                context=context,
                chat_id=update.effective_chat.id,
                text=final_response.choices[0].message.content,
                edit_message_id=processing_msg.message_id
            )

        else:
            # If no tool was called, just reply with the AI's text
            user_sessions[chat_id].append(message)
            
            await send_long_message(
                context=context,
                chat_id=update.effective_chat.id,
                text=message.content or "I couldn't understand that.",
                edit_message_id=processing_msg.message_id
            )
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text="Sorry, an error occurred while processing your message."
        )


# ==========================================
# FASTAPI APPLICATION SETUP & LIFECYCLE
# ==========================================

# Global Telegram Application instance
tg_app = None
bot_task = None

async def start_telegram_bot():
    """Asynchronously initializes and starts the Telegram Bot in the background."""
    global tg_app
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token or token == "your_telegram_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN is not set or is placeholder. Telegram Bot will be inactive.")
        return
        
    try:
        # Build the application
        tg_app = ApplicationBuilder().token(token).build()
        
        # Security checking
        if not ALLOWED_USER_ID or str(ALLOWED_USER_ID) == "your_telegram_user_id_here":
            logger.error("CRITICAL SECURITY WARNING: ALLOWED_USER_ID is not configured. Bot will refuse messages.")
            
        # Add Handlers
        tg_app.add_handler(CommandHandler("start", start))
        tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Initialize and start polling
        await tg_app.initialize()
        await tg_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await tg_app.start()
        
        logger.info("JARVIS Telegram Bot successfully started in the background.")
        
    except Exception as e:
        logger.error(f"Failed to start Telegram Bot in background task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown lifecycle of the co-hosted Telegram Bot."""
    global tg_app, bot_task
    
    # Spawn Telegram Bot startup as a background task to prevent blocking FastAPI/Uvicorn boot
    bot_task = asyncio.create_task(start_telegram_bot())
    
    yield
    
    # Shutdown bot gracefully
    logger.info("Stopping Telegram Bot...")
    if tg_app:
        try:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()
            logger.info("Telegram Bot shut down gracefully.")
        except Exception as e:
            logger.error(f"Error during Telegram Bot shutdown: {e}")

# Initialize FastAPI App
app = FastAPI(
    title="JARVIS Life Tracker API",
    description="Unified REST API & Bot backend to log financial expenses and physical workouts.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for personal dashboard web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins in production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/")
def read_root():
    """Service status checking endpoint."""
    return {
        "status": "online",
        "service": "JARVIS Life Tracker Backend",
        "bot_active": tg_app is not None
    }

@app.get("/api/expenses")
def read_expenses(category: str = None, days_back: int = 30):
    """Retrieve expense logs, optionally filtered by category and days."""
    try:
        expenses = database.get_expenses(category=category, days_back=days_back)
        return [
            {
                "id": e.id,
                "amount": e.amount,
                "category": e.category,
                "description": e.description,
                "payment_method": e.payment_method,
                "currency": e.currency,
                "date": e.date.strftime("%Y-%m-%d %H:%M:%S")
            }
            for e in expenses
        ]
    except Exception as e:
        logger.error(f"API Error fetching expenses: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/api/workouts")
def read_workouts(workout_type: str = None, days_back: int = 30):
    """Retrieve workout logs, optionally filtered by type and days."""
    try:
        workouts = database.get_workout_logs(workout_type=workout_type, days_back=days_back)
        return [
            {
                "id": w.id,
                "workout_type": w.workout_type,
                "duration_minutes": w.duration_minutes,
                "intensity": w.intensity,
                "description": w.description,
                "date": w.date.strftime("%Y-%m-%d %H:%M:%S")
            }
            for w in workouts
        ]
    except Exception as e:
        logger.error(f"API Error fetching workouts: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/api/summary")
def read_summary():
    """Retrieve aggregate stats over the past 7 days for the personal web dashboard."""
    try:
        expenses = database.get_expenses(days_back=7)
        workouts = database.get_workout_logs(days_back=7)
        
        # Calculate spending totals grouped by currency
        total_spent = {}
        for e in expenses:
            total_spent[e.currency] = round(total_spent.get(e.currency, 0.0) + e.amount, 2)
            
        total_workouts = len(workouts)
        total_workout_minutes = sum(w.duration_minutes or 0 for w in workouts)
        
        # Categorized breakdown
        category_breakdown = {}
        for e in expenses:
            category_breakdown[e.category] = round(category_breakdown.get(e.category, 0.0) + e.amount, 2)
            
        return {
            "last_7_days": {
                "total_spending": total_spent,  # Breakdown dict by currency, e.g. {"MXN": 115.00}
                "spending_breakdown": category_breakdown,
                "workout_count": total_workouts,
                "workout_duration_minutes": total_workout_minutes
            },
            "recent_expenses": [
                {
                    "id": e.id,
                    "amount": e.amount,
                    "category": e.category,
                    "description": e.description,
                    "currency": e.currency,
                    "date": e.date.strftime("%Y-%m-%d")
                }
                for e in expenses[:5]
            ],
            "recent_workouts": [
                {
                    "id": w.id,
                    "workout_type": w.workout_type,
                    "duration_minutes": w.duration_minutes,
                    "intensity": w.intensity,
                    "date": w.date.strftime("%Y-%m-%d")
                }
                for w in workouts[:5]
            ]
        }
    except Exception as e:
        logger.error(f"API Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")


# ==========================================
# MAIN EXECUTION ENTRYPOINT
# ==========================================

if __name__ == '__main__':
    import uvicorn
    # Start uvicorn server locally on port 8000
    logger.info("Starting JARVIS FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

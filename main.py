import os
import io
import json
import logging
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# FastAPI Imports
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    chat_id: int = 1

# Pydantic Schemas for Expenses
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: str
    payment_method: str = "unknown"
    currency: str = "MXN"
    date: str = None

class ExpenseUpdate(BaseModel):
    amount: float = None
    category: str = None
    description: str = None
    payment_method: str = None
    currency: str = None
    date: str = None

# Pydantic Schemas for Workouts
class WorkoutCreate(BaseModel):
    workout_type: str
    duration_minutes: int = None
    intensity: str = None
    description: str = None
    metrics: dict = None
    date: str = None

class WorkoutUpdate(BaseModel):
    workout_type: str = None
    duration_minutes: int = None
    intensity: str = None
    description: str = None
    metrics: dict = None
    date: str = None

# Pydantic Schemas for Hobbies Catalog
class HobbyCreate(BaseModel):
    name: str
    category: str = None
    description: str = None
    icon: str = None

class HobbyUpdate(BaseModel):
    name: str = None
    category: str = None
    description: str = None
    icon: str = None

# Telegram Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
                        "description": "ONLY supply if the user EXPLICITLY specified a past or specific date (e.g., 'yesterday', '2026-08-05'). Leave null/omitted for today's expenses so exact Mexico City date and time is automatically recorded."
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
                    "metrics": {
                        "type": "object",
                        "description": "Dynamic metrics based on the type of workout. For Running/Walking: include 'distance' (float in km) and 'pace' (string e.g. '5:30 min/km') if mentioned. For Basketball: include 'shots_made' (int) and 'shots_attempted' (int) if mentioned. For Gym (weightlifting): include 'exercises' which is an array of objects, where each object contains: 'name' (string e.g. 'press de pecho'), 'weight' (float), 'unit' ('lbs' or 'kg'), 'sets' (int), and 'reps' (int)."
                    },
                    "date": {
                        "type": "string",
                        "description": "ONLY supply if the user EXPLICITLY specified a past or specific date (e.g., 'yesterday', '2026-08-05'). Leave null/omitted for today's workouts so exact Mexico City date and time is automatically recorded."
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
    },
    {
        "type": "function",
        "function": {
            "name": "edit_workout",
            "description": "Edit an existing workout or exercise log in the database by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {
                        "type": "integer",
                        "description": "The unique ID of the workout log to edit."
                    },
                    "workout_type": { "type": "string", "description": "New workout type." },
                    "duration_minutes": { "type": "integer", "description": "New duration in minutes." },
                    "intensity": { "type": "string", "description": "New intensity (low, medium, high)." },
                    "description": { "type": "string", "description": "New description or notes." },
                    "metrics": { "type": "object", "description": "New dynamic metrics dictionary." },
                    "date": { "type": "string", "description": "New date in YYYY-MM-DD format." }
                },
                "required": ["workout_id"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_workout",
            "description": "Delete a workout or exercise log from the database by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {
                        "type": "integer",
                        "description": "The unique ID of the workout log to delete."
                    }
                },
                "required": ["workout_id"],
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

async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, edit_message_id: int = None, reply_markup = None):
    """Sends a long message by splitting it into chunks.
    
    If edit_message_id is provided, the first chunk will edit that message.
    Subsequent chunks are sent as new messages.
    reply_markup can be passed to attach InlineKeyboardButtons to the message.
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
                text=first_chunk,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to edit message {edit_message_id}: {e}. Sending as new message instead.")
            await context.bot.send_message(chat_id=chat_id, text=first_chunk, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=first_chunk, reply_markup=reply_markup)
        
    for chunk in chunks[1:]:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


def format_workout_metrics(metrics: dict) -> str:
    """Formats dynamic workout metrics into a user-friendly Spanish string."""
    if not metrics:
        return ""
    
    parts = []
    
    # Running/Walking
    if "distance" in metrics:
        dist = metrics["distance"]
        parts.append(f"{dist} km")
    if "pace" in metrics:
        pace = metrics["pace"]
        parts.append(f"a ritmo de {pace}")
        
    # Basketball
    if "shots_made" in metrics or "shots_attempted" in metrics:
        made = metrics.get("shots_made", "?")
        att = metrics.get("shots_attempted", "?")
        parts.append(f"tiros anotados: {made}/{att}")
        
    # Gym / Weightlifting
    if "exercises" in metrics and isinstance(metrics["exercises"], list):
        ex_parts = []
        for ex in metrics["exercises"]:
            name = ex.get("name", "ejercicio")
            weight = ex.get("weight")
            unit = ex.get("unit", "kg")
            sets = ex.get("sets")
            reps = ex.get("reps")
            
            ex_str = name
            if weight is not None:
                ex_str += f" con {weight} {unit}"
            if sets is not None and reps is not None:
                ex_str += f" ({sets}x{reps})"
            elif sets is not None:
                ex_str += f" ({sets} series)"
            elif reps is not None:
                ex_str += f" ({reps} reps)"
            ex_parts.append(ex_str)
        if ex_parts:
            parts.append("ejercicios: " + ", ".join(ex_parts))
            
    # Generic fields that might have been stored as key-value pairs
    for k, v in metrics.items():
        if k not in ["distance", "pace", "shots_made", "shots_attempted", "exercises"]:
            parts.append(f"{k}: {v}")
            
    return ", ".join(parts)


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

async def run_jarvis_ai(chat_id: int, user_text: str) -> tuple[str, dict | None]:
    """Core AI processing function returning JARVIS string response and created item details if any."""
    mexico_tz = ZoneInfo("America/Mexico_City")
    current_date = datetime.now(mexico_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": ""}]
    
    user_sessions[chat_id][0]["content"] = (
        f"You are JARVIS, a unified personal tracking assistant. Current date and time in Mexico City (America/Mexico_City) is {current_date}. "
        "If the user asks what time or date it is, respond using this Mexico City time. "
        "CRITICAL TIMEZONE & DATE RULE: All timestamps must correspond to Mexico City timezone. "
        "When calling save_expense or save_workout for an entry happening today, DO NOT supply the 'date' parameter (leave it null/omitted). "
        "The backend automatically records the exact current Mexico City timestamp when 'date' is omitted. "
        "ONLY supply a string 'date' parameter if the user EXPLICITLY mentions a past/different date (e.g. 'ayer', 'el lunes pasado', 'el 5 de agosto'). "
        "You help the user log their physical workouts and their financial expenses in a single chat. "
        "If the user is tracking an expense, use the save_expense tool. "
        "IMPORTANT: The save_expense tool requires a payment_method (e.g., cash, card, transfer). "
        "If the user DOES NOT specify how they paid, politely ask them before calling the tool. "
        "If the user mentions an expense with a specific currency (e.g. pesos, MXN, dollars, USD, EUR), extract it and supply it to the tool. "
        "Otherwise, default to 'MXN'. When reporting expenses, always accompany amounts with their currency code (e.g. 115 MXN or $50 USD). "
        "If the user is tracking a workout or exercise, use the save_workout tool. "
        "IMPORTANT: The save_workout tool has a dynamic 'metrics' parameter to store specific statistics based on the sport/workout type. "
        "For Running or Walking: extract 'distance' (float in km, e.g. 5.0) and 'pace' (string, e.g. '5:30 min/km') if mentioned. "
        "For Basketball: extract shooting statistics like 'shots_made' (integer) and 'shots_attempted' (integer) if mentioned. "
        "For Gym/Weightlifting: extract 'exercises' as a list of objects, each containing 'name' (e.g. 'press de pecho'), 'weight' (float), 'unit' ('lbs' or 'kg'), 'sets' (int), and 'reps' (int). "
        "For other sports (like Yoga), duration is enough, or extract other relevant numeric/text key-values. "
        "Extract these details precisely and feed them to the 'metrics' parameter when calling 'save_workout'. "
        "If the user asks about past expenses, use the get_expenses tool. "
        "If the user asks about past workouts, use the get_workout_logs tool. "
        "If they ask for a general summary of their life or logs, you can call both get_expenses and get_workout_logs. "
        "If the user asks to edit or delete an expense or workout without providing an ID, use get_expenses or get_workout_logs first to find the ID of the most recent log. "
        "If the user asks to edit an expense, use edit_expense. "
        "If the user asks to delete an expense, BEFORE deleting, ask for confirmation or call delete_expense if explicitly confirmed. "
        "If the user asks to edit a workout/exercise, use edit_workout. "
        "If the user asks to delete a workout/exercise, BEFORE deleting, ask for confirmation or call delete_workout if explicitly confirmed."
    )
    
    user_sessions[chat_id].append({"role": "user", "content": user_text})
    if len(user_sessions[chat_id]) > 13:
        user_sessions[chat_id] = [user_sessions[chat_id][0]] + user_sessions[chat_id][-12:]
        
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=user_sessions[chat_id],
        tools=tools,
        tool_choice="auto"
    )
    
    last_created_item = None
    message = response.choices[0].message
    if message.tool_calls:
        user_sessions[chat_id].append(message)
        for tool_call in message.tool_calls:
            if tool_call.function.name == "save_expense":
                args = json.loads(tool_call.function.arguments)
                expense = database.add_expense(
                    amount=args["amount"],
                    category=args["category"],
                    description=args["description"],
                    payment_method=args.get("payment_method", "unknown"),
                    currency=args.get("currency", "MXN"),
                    date_str=args.get("date")
                )
                last_created_item = {"type": "expense", "id": expense.id}
                tool_response = f"Successfully saved expense: id={expense.id}, amount={expense.amount}, currency={expense.currency}, category={expense.category}, description={expense.description}, payment_method={expense.payment_method}, date={expense.date.strftime('%Y-%m-%d')}"
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "save_expense", "content": tool_response})
            elif tool_call.function.name == "get_expenses":
                args = json.loads(tool_call.function.arguments)
                expenses = database.get_expenses(category=args.get("category"), days_back=args.get("days_back", 30))
                if not expenses:
                    tool_response = "No expenses found for the given criteria."
                else:
                    lines = [f"- [ID: {e.id}] {e.date.strftime('%Y-%m-%d')}: {e.amount:.2f} {e.currency} for {e.description} ({e.category}) paid via {e.payment_method}" for e in expenses]
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
                tool_response = f"Successfully updated expense: id={expense.id}, amount={expense.amount}, currency={expense.currency}, category={expense.category}, description={expense.description}, payment_method={expense.payment_method}, date={expense.date.strftime('%Y-%m-%d')}" if expense else "Expense not found."
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "edit_expense", "content": tool_response})
            elif tool_call.function.name == "save_workout":
                args = json.loads(tool_call.function.arguments)
                workout = database.add_workout_log(
                    workout_type=args["workout_type"],
                    duration_minutes=args.get("duration_minutes"),
                    intensity=args.get("intensity"),
                    description=args.get("description"),
                    metrics=args.get("metrics"),
                    date_str=args.get("date")
                )
                last_created_item = {"type": "workout", "id": workout.id}
                met_str = format_workout_metrics(workout.metrics)
                met_part = f", metrics={met_str}" if met_str else ""
                tool_response = f"Successfully saved workout log: id={workout.id}, type={workout.workout_type}, duration={workout.duration_minutes or 'unknown'} mins, intensity={workout.intensity or 'unknown'}{met_part}, date={workout.date.strftime('%Y-%m-%d')}"
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "save_workout", "content": tool_response})
            elif tool_call.function.name == "get_workout_logs":
                args = json.loads(tool_call.function.arguments)
                workouts = database.get_workout_logs(workout_type=args.get("workout_type"), days_back=args.get("days_back", 30))
                if not workouts:
                    tool_response = "No workout logs found for the given criteria."
                else:
                    lines = []
                    for w in workouts:
                        met_str = format_workout_metrics(w.metrics)
                        desc_part = f" - {w.description}" if w.description else ""
                        metric_part = f" [{met_str}]" if met_str else ""
                        duration_part = f" ({w.duration_minutes} mins)" if w.duration_minutes else ""
                        lines.append(f"- [ID: {w.id}] {w.date.strftime('%Y-%m-%d')}: {w.workout_type}{duration_part}{metric_part}{desc_part}")
                    tool_response = f"Found {len(workouts)} workout logs:\n" + "\n".join(lines)
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "get_workout_logs", "content": tool_response})
            elif tool_call.function.name == "edit_workout":
                args = json.loads(tool_call.function.arguments)
                workout = database.edit_workout_log(
                    workout_id=args["workout_id"],
                    workout_type=args.get("workout_type"),
                    duration_minutes=args.get("duration_minutes"),
                    intensity=args.get("intensity"),
                    description=args.get("description"),
                    metrics=args.get("metrics"),
                    date_str=args.get("date")
                )
                tool_response = f"Successfully updated workout log: id={workout.id}, type={workout.workout_type}" if workout else "Workout log not found."
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "edit_workout", "content": tool_response})
            elif tool_call.function.name == "delete_workout":
                args = json.loads(tool_call.function.arguments)
                success = database.delete_workout_log(args["workout_id"])
                tool_response = "Workout log deleted successfully." if success else "Workout log not found."
                user_sessions[chat_id].append({"role": "tool", "tool_call_id": tool_call.id, "name": "delete_workout", "content": tool_response})

        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=user_sessions[chat_id]
        )
        reply_text = final_response.choices[0].message.content
        user_sessions[chat_id].append(final_response.choices[0].message)
        return reply_text, last_created_item
    else:
        user_sessions[chat_id].append(message)
        return (message.content or "I couldn't understand that."), None

async def process_jarvis_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, processing_msg):
    """Core logic to send user_text to OpenAI GPT-4o-mini and handle tool calls."""
    chat_id = update.effective_chat.id
    try:
        reply_text, created_item = await run_jarvis_ai(chat_id, user_text)
        
        reply_markup = None
        if created_item:
            item_type = created_item["type"]
            item_id = created_item["id"]
            if item_type == "expense":
                keyboard = [
                    [
                        InlineKeyboardButton("✏️ Modificar", callback_data=f"edit_exp:{item_id}"),
                        InlineKeyboardButton("❌ Eliminar", callback_data=f"del_exp:{item_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            elif item_type == "workout":
                keyboard = [
                    [
                        InlineKeyboardButton("✏️ Modificar", callback_data=f"edit_wo:{item_id}"),
                        InlineKeyboardButton("❌ Eliminar", callback_data=f"del_wo:{item_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

        await send_long_message(
            context=context,
            chat_id=chat_id,
            text=reply_text,
            edit_message_id=processing_msg.message_id,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            text="Sorry, an error occurred while processing your message."
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive inline keyboard button callbacks for editing/deleting items."""
    query = update.callback_query
    user = update.effective_user
    
    if not ALLOWED_USER_ID or user.id != ALLOWED_USER_ID:
        await query.answer("Acceso no autorizado.", show_alert=True)
        return

    data = query.data
    try:
        if data.startswith("del_exp:"):
            expense_id = int(data.split(":")[1])
            success = database.delete_expense(expense_id)
            await query.answer("Gasto eliminado exitosamente.")
            if success:
                await query.edit_message_text(f"❌ Gasto #{expense_id} eliminado exitosamente.")
            else:
                await query.edit_message_text(f"⚠️ El gasto #{expense_id} ya no existe o fue eliminado previamente.")
                
        elif data.startswith("del_wo:"):
            workout_id = int(data.split(":")[1])
            success = database.delete_workout_log(workout_id)
            await query.answer("Ejercicio eliminado exitosamente.")
            if success:
                await query.edit_message_text(f"❌ Ejercicio #{workout_id} eliminado exitosamente.")
            else:
                await query.edit_message_text(f"⚠️ El ejercicio #{workout_id} ya no existe o fue eliminado previamente.")
                
        elif data.startswith("edit_exp:"):
            expense_id = int(data.split(":")[1])
            await query.answer()
            await query.message.reply_text(
                f"✏️ Para modificar este gasto (ID: {expense_id}), simplemente dime o envíame una nota de voz con el cambio, por ejemplo:\n"
                f"• 'Modifica el gasto {expense_id} a $150 pesitos'\n"
                f"• 'Cambia la categoría del gasto {expense_id} a Transporte'"
            )
            
        elif data.startswith("edit_wo:"):
            workout_id = int(data.split(":")[1])
            await query.answer()
            await query.message.reply_text(
                f"✏️ Para modificar este ejercicio (ID: {workout_id}), simplemente dime o envíame una nota de voz con el cambio, por ejemplo:\n"
                f"• 'Modifica el ejercicio {workout_id} a 45 minutos'\n"
                f"• 'Cambia el ejercicio {workout_id} a correr 5k en 25 mins'"
            )
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.answer("Ocurrió un error al procesar la acción.", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming text message from Telegram."""
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
    processing_msg = await update.message.reply_text("Processing...")
    await process_jarvis_text(update, context, user_text, processing_msg)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming voice notes or audio messages using OpenAI Whisper API."""
    user = update.effective_user
    
    if not ALLOWED_USER_ID:
        logger.error("Access denied: ALLOWED_USER_ID is not configured.")
        await update.message.reply_text("Security Error: Bot is not configured. Please set ALLOWED_USER_ID in .env.")
        return
        
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access attempt by user {user.id} ({user.username or 'No Username'}).")
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    voice_obj = update.message.voice or update.message.audio
    if not voice_obj:
        await update.message.reply_text("Could not read voice message payload.")
        return

    status_msg = await update.message.reply_text("🎙 Transcribing voice note...")

    try:
        # Download voice note file from Telegram
        tg_file = await voice_obj.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        # Wrap in BytesIO for OpenAI Whisper API
        audio_stream = io.BytesIO(file_bytes)
        audio_stream.name = "voice.ogg"

        # Transcribe audio using Whisper
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_stream
        )

        user_text = transcription.text.strip()
        if not user_text:
            await status_msg.edit_text("🎙 No se detectó ninguna voz comprensible en la nota de audio.")
            return

        # Show transcription to user and continue processing
        try:
            await status_msg.edit_text(f"🎙 *Transcription:* \"{user_text}\"\n\nProcessing...", parse_mode="Markdown")
        except Exception:
            await status_msg.edit_text(f"🎙 Transcription: \"{user_text}\"\n\nProcessing...")

        await process_jarvis_text(update, context, user_text, status_msg)

    except Exception as e:
        logger.error(f"Error transcribing voice note: {e}")
        await status_msg.edit_text("⚠️ Ocurrió un error al transcribir tu nota de voz. Por favor intenta de nuevo.")


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
        tg_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))
        tg_app.add_handler(CallbackQueryHandler(handle_callback_query))
        
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
# API TOKEN SECURITY CONFIGURATION
# ==========================================

API_TOKEN = os.getenv("API_TOKEN")
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)

async def verify_api_token(api_key: str = Security(api_key_header)):
    """Verifies the incoming X-API-Token header against the configured environment variable.
    
    Telegram Bot bypasses this check naturally because it calls the database functions
    directly in-process rather than making HTTP network requests.
    """
    if not API_TOKEN or API_TOKEN == "your_secure_api_token_here":
        logger.error("API Security Configuration Error: API_TOKEN environment variable is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security configuration error: API_TOKEN is not configured on the backend."
        )
    if api_key != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Token. Please provide a valid token in the X-API-Token header."
        )
    return api_key


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/")
def read_root():
    """Service status checking endpoint (Unprotected for hosted health checks)."""
    return {
        "status": "online",
        "service": "JARVIS Life Tracker Backend",
        "bot_active": tg_app is not None
    }

@app.post("/api/chat", dependencies=[Depends(verify_api_token)])
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint for Siri Shortcuts, web frontends, or HTTP clients."""
    try:
        reply, created_item = await run_jarvis_ai(request.chat_id, request.message)
        return {
            "status": "success",
            "reply": reply,
            "created_item": created_item,
            "user_text": request.message
        }
    except Exception as e:
        logger.error(f"API Error in /api/chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing chat message.")

@app.get("/api/expenses", dependencies=[Depends(verify_api_token)])
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

@app.post("/api/expenses", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_token)])
def create_expense(expense: ExpenseCreate):
    """Create a new expense log in the database."""
    try:
        new_exp = database.add_expense(
            amount=expense.amount,
            category=expense.category,
            description=expense.description,
            payment_method=expense.payment_method,
            currency=expense.currency,
            date_str=expense.date
        )
        return {
            "id": new_exp.id,
            "amount": new_exp.amount,
            "category": new_exp.category,
            "description": new_exp.description,
            "payment_method": new_exp.payment_method,
            "currency": new_exp.currency,
            "date": new_exp.date.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"API Error creating expense: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.put("/api/expenses/{expense_id}", dependencies=[Depends(verify_api_token)])
def update_expense_endpoint(expense_id: int, expense: ExpenseUpdate):
    """Update an existing expense by its ID."""
    try:
        updated = database.edit_expense(
            expense_id=expense_id,
            amount=expense.amount,
            category=expense.category,
            description=expense.description,
            payment_method=expense.payment_method,
            currency=expense.currency,
            date_str=expense.date
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Expense not found.")
        return {
            "id": updated.id,
            "amount": updated.amount,
            "category": updated.category,
            "description": updated.description,
            "payment_method": updated.payment_method,
            "currency": updated.currency,
            "date": updated.date.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error updating expense: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.delete("/api/expenses/{expense_id}", dependencies=[Depends(verify_api_token)])
def delete_expense_endpoint(expense_id: int):
    """Delete an expense by its ID."""
    try:
        success = database.delete_expense(expense_id)
        if not success:
            raise HTTPException(status_code=404, detail="Expense not found.")
        return {"status": "success", "message": "Expense deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error deleting expense: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/api/workouts", dependencies=[Depends(verify_api_token)])
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
                "metrics": w.metrics,
                "date": w.date.strftime("%Y-%m-%d %H:%M:%S")
            }
            for w in workouts
        ]
    except Exception as e:
        logger.error(f"API Error fetching workouts: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.post("/api/workouts", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_token)])
def create_workout(workout: WorkoutCreate):
    """Create a new workout log in the database."""
    try:
        new_w = database.add_workout_log(
            workout_type=workout.workout_type,
            duration_minutes=workout.duration_minutes,
            intensity=workout.intensity,
            description=workout.description,
            metrics=workout.metrics,
            date_str=workout.date
        )
        return {
            "id": new_w.id,
            "workout_type": new_w.workout_type,
            "duration_minutes": new_w.duration_minutes,
            "intensity": new_w.intensity,
            "description": new_w.description,
            "metrics": new_w.metrics,
            "date": new_w.date.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"API Error creating workout: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.put("/api/workouts/{workout_id}", dependencies=[Depends(verify_api_token)])
def update_workout_endpoint(workout_id: int, workout: WorkoutUpdate):
    """Update an existing workout by its ID."""
    try:
        updated = database.edit_workout_log(
            workout_id=workout_id,
            workout_type=workout.workout_type,
            duration_minutes=workout.duration_minutes,
            intensity=workout.intensity,
            description=workout.description,
            metrics=workout.metrics,
            date_str=workout.date
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Workout not found.")
        return {
            "id": updated.id,
            "workout_type": updated.workout_type,
            "duration_minutes": updated.duration_minutes,
            "intensity": updated.intensity,
            "description": updated.description,
            "metrics": updated.metrics,
            "date": updated.date.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error updating workout: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.delete("/api/workouts/{workout_id}", dependencies=[Depends(verify_api_token)])
def delete_workout_endpoint(workout_id: int):
    """Delete a workout by its ID."""
    try:
        success = database.delete_workout_log(workout_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workout not found.")
        return {"status": "success", "message": "Workout deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error deleting workout: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/api/summary", dependencies=[Depends(verify_api_token)])
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
                    "metrics": w.metrics,
                    "date": w.date.strftime("%Y-%m-%d")
                }
                for w in workouts[:5]
            ]
        }
    except Exception as e:
        logger.error(f"API Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")


# ==========================================
# HOBBY ENDPOINTS
# ==========================================

@app.get("/api/hobbies", dependencies=[Depends(verify_api_token)])
def read_hobbies(category: str = None):
    """Retrieve hobbies, optionally filtered by category."""
    try:
        hobbies = database.get_hobbies(category=category)
        return [
            {
                "id": h.id,
                "name": h.name,
                "category": h.category,
                "description": h.description,
                "icon": h.icon,
                "date_added": h.date_added.strftime("%Y-%m-%d %H:%M:%S")
            }
            for h in hobbies
        ]
    except Exception as e:
        logger.error(f"API Error fetching hobbies: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.post("/api/hobbies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_token)])
def create_hobby(hobby: HobbyCreate):
    """Create a new hobby log in the database."""
    try:
        new_hobby = database.add_hobby(
            name=hobby.name,
            category=hobby.category,
            description=hobby.description,
            icon=hobby.icon
        )
        return {
            "id": new_hobby.id,
            "name": new_hobby.name,
            "category": new_hobby.category,
            "description": new_hobby.description,
            "icon": new_hobby.icon,
            "date_added": new_hobby.date_added.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"API Error creating hobby: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.put("/api/hobbies/{hobby_id}", dependencies=[Depends(verify_api_token)])
def update_hobby(hobby_id: int, hobby: HobbyUpdate):
    """Update an existing hobby by its ID."""
    try:
        updated_hobby = database.edit_hobby(
            hobby_id=hobby_id,
            name=hobby.name,
            category=hobby.category,
            description=hobby.description,
            icon=hobby.icon
        )
        if not updated_hobby:
            raise HTTPException(status_code=404, detail="Hobby not found.")
        return {
            "id": updated_hobby.id,
            "name": updated_hobby.name,
            "category": updated_hobby.category,
            "description": updated_hobby.description,
            "icon": updated_hobby.icon,
            "date_added": updated_hobby.date_added.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error updating hobby: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.delete("/api/hobbies/{hobby_id}", dependencies=[Depends(verify_api_token)])
def delete_hobby(hobby_id: int):
    """Delete a hobby by its ID."""
    try:
        success = database.delete_hobby(hobby_id)
        if not success:
            raise HTTPException(status_code=404, detail="Hobby not found.")
        return {"status": "success", "message": "Hobby deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error deleting hobby: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")


# ==========================================
# MAIN EXECUTION ENTRYPOINT
# ==========================================

if __name__ == '__main__':
    import uvicorn
    # Start uvicorn server locally on port 8000
    logger.info("Starting JARVIS FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

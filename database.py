import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables
load_dotenv()

# Database Connection Logic: PostgreSQL with auto SQLite fallback
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL or DB_URL == "your_postgres_database_url_here":
    # Fallback to local SQLite file for development
    DB_URL = 'sqlite:///life_tracker.db'
else:
    # Standardize heroku/render postgres URLs to postgresql://
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# Create the SQLAlchemy engine
engine = create_engine(DB_URL, echo=False)

# Create a declarative base class
Base = declarative_base()

# Define the Expense model
class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    payment_method = Column(String, default='unknown')
    currency = Column(String, default='MXN')  # Added currency support
    date = Column(DateTime, default=lambda: datetime.now())

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, currency='{self.currency}', category='{self.category}', payment='{self.payment_method}', date='{self.date.strftime('%Y-%m-%d')}')>"

# Define the WorkoutLog model
class WorkoutLog(Base):
    __tablename__ = 'workout_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_type = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    intensity = Column(String, nullable=True)  # e.g., low, medium, high
    description = Column(String, nullable=True)  # e.g., "Ran 5k", "Leg Day"
    date = Column(DateTime, default=lambda: datetime.now())

    def __repr__(self):
        return f"<WorkoutLog(id={self.id}, type='{self.workout_type}', duration={self.duration_minutes}, intensity='{self.intensity}', date='{self.date.strftime('%Y-%m-%d')}')>"

# Create all tables in the engine (equivalent to "CREATE TABLE IF NOT EXISTS")
Base.metadata.create_all(engine)

# Dynamic schema migration: add currency column to expenses table if it doesn't exist
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE expenses ADD COLUMN currency VARCHAR DEFAULT 'MXN'"))
        conn.commit()
    except Exception:
        pass  # Column already exists or database dialect handles it differently

# Create a configured "Session" class
SessionLocal = sessionmaker(bind=engine)

def get_session():
    """Returns a new database session."""
    return SessionLocal()


# ==========================================
# EXPENSE DATABASE HELPER METHODS
# ==========================================

def add_expense(amount: float, category: str, description: str, payment_method: str = "unknown", currency: str = "MXN", date_str: str = None):
    """Utility function to add a new expense."""
    session = get_session()
    try:
        dt = datetime.now()
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass  # Fallback to now
                
        new_expense = Expense(
            amount=amount, 
            category=category, 
            description=description,
            payment_method=payment_method,
            currency=currency,
            date=dt
        )
        session.add(new_expense)
        session.commit()
        session.refresh(new_expense)
        return new_expense
    finally:
        session.close()

def get_recent_expenses(limit: int = 10):
    """Utility function to get the most recent expenses."""
    session = get_session()
    try:
        return session.query(Expense).order_by(Expense.date.desc()).limit(limit).all()
    finally:
        session.close()

def get_expenses(category: str = None, days_back: int = 30):
    """Utility function to get expenses, optionally filtered by category and time."""
    session = get_session()
    try:
        query = session.query(Expense)
        
        if category:
            # Case-insensitive category match
            query = query.filter(Expense.category.ilike(f"%{category}%"))
            
        if days_back:
            start_date = datetime.now() - timedelta(days=days_back)
            query = query.filter(Expense.date >= start_date)
            
        return query.order_by(Expense.date.desc()).all()
    finally:
        session.close()

def delete_expense(expense_id: int):
    """Utility function to delete an expense by ID."""
    session = get_session()
    try:
        expense = session.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            session.delete(expense)
            session.commit()
            return True
        return False
    finally:
        session.close()

def edit_expense(expense_id: int, amount: float = None, category: str = None, description: str = None, payment_method: str = None, currency: str = None, date_str: str = None):
    """Utility function to edit an existing expense."""
    session = get_session()
    try:
        expense = session.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return None
            
        if amount is not None:
            expense.amount = amount
        if category is not None:
            expense.category = category
        if description is not None:
            expense.description = description
        if payment_method is not None:
            expense.payment_method = payment_method
        if currency is not None:
            expense.currency = currency
        if date_str is not None:
            try:
                expense.date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass
                
        session.commit()
        session.refresh(expense)
        return expense
    finally:
        session.close()


# ==========================================
# WORKOUT DATABASE HELPER METHODS
# ==========================================

def add_workout_log(workout_type: str, duration_minutes: int = None, intensity: str = None, description: str = None, date_str: str = None):
    """Utility function to add a new workout log."""
    session = get_session()
    try:
        dt = datetime.now()
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass  # Fallback to now
                
        new_workout = WorkoutLog(
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            intensity=intensity,
            description=description,
            date=dt
        )
        session.add(new_workout)
        session.commit()
        session.refresh(new_workout)
        return new_workout
    finally:
        session.close()

def get_workout_logs(workout_type: str = None, days_back: int = 30):
    """Utility function to get workout logs, optionally filtered by type and time."""
    session = get_session()
    try:
        query = session.query(WorkoutLog)
        
        if workout_type:
            # Case-insensitive match
            query = query.filter(WorkoutLog.workout_type.ilike(f"%{workout_type}%"))
            
        if days_back:
            start_date = datetime.now() - timedelta(days=days_back)
            query = query.filter(WorkoutLog.date >= start_date)
            
        return query.order_by(WorkoutLog.date.desc()).all()
    finally:
        session.close()

def delete_workout_log(workout_id: int):
    """Utility function to delete a workout log by ID."""
    session = get_session()
    try:
        workout = session.query(WorkoutLog).filter(WorkoutLog.id == workout_id).first()
        if workout:
            session.delete(workout)
            session.commit()
            return True
        return False
    finally:
        session.close()


if __name__ == '__main__':
    # Test script for the database
    print("Testing DB connection...")
    expense = add_expense(10.50, "Food", "Lunch at cafe", currency="USD")
    print(f"Added expense: {expense}")
    workout = add_workout_log("Running", 30, "medium", "Evening jog")
    print(f"Added workout: {workout}")
    print("Recent workouts:")
    for w in get_workout_logs():
        print(w)

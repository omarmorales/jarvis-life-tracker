import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# Timezone Configuration (CDMX)
MEXICO_TZ = ZoneInfo("America/Mexico_City")

def get_now_cdmx():
    """Returns the current naive datetime in Mexico City timezone."""
    return datetime.now(MEXICO_TZ).replace(tzinfo=None)

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
    date = Column(DateTime, default=get_now_cdmx)

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
    metrics = Column(JSON, nullable=True)  # Dynamic JSON metrics for dynamic sports
    date = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<WorkoutLog(id={self.id}, type='{self.workout_type}', duration={self.duration_minutes}, intensity='{self.intensity}', metrics={self.metrics}, date='{self.date.strftime('%Y-%m-%d')}')>"


# Define the Hobby model
class Hobby(Base):
    __tablename__ = 'hobbies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    date_added = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<Hobby(id={self.id}, name='{self.name}', category='{self.category}', icon='{self.icon}')>"


# ==========================================
# BASKETBALL MANAGEMENT MODELS
# ==========================================

class Player(Base):
    __tablename__ = 'basket_players'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    nickname = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    jersey_number = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)  # 1 active, 0 inactive
    created_at = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.name}', nickname='{self.nickname}', jersey={self.jersey_number})>"


class Tournament(Base):
    __tablename__ = 'basket_tournaments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    team_name = Column(String, default="Mi Equipo")
    total_cost = Column(Float, nullable=False, default=0.0)
    registration_fee = Column(Float, default=0.0)
    referee_fee_total = Column(Float, default=0.0)
    status = Column(String, default='active')  # 'active', 'completed', 'archived'
    playoff_seed = Column(Integer, nullable=True)  # e.g., 1, 2, 3
    final_result = Column(String, nullable=True)  # e.g., 'Campeón', 'Subcampeón', 'Semifinales', 'Fase Regular'
    created_at = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<Tournament(id={self.id}, name='{self.name}', team='{self.team_name}', cost={self.total_cost}, status='{self.status}')>"


class TournamentPlayer(Base):
    __tablename__ = 'basket_tournament_players'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, nullable=False)
    player_id = Column(Integer, nullable=False)
    jersey_number = Column(Integer, nullable=True)
    assigned_quota = Column(Float, default=0.0)
    has_custom_quota = Column(Integer, default=0)  # 1 if manually fixed, 0 if calculated
    status = Column(String, default='active')  # 'active', 'injured', 'dropped_out'
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<TournamentPlayer(tourn_id={self.tournament_id}, player_id={self.player_id}, jersey={self.jersey_number}, quota={self.assigned_quota}, status='{self.status}')>"


class TournamentPayment(Base):
    __tablename__ = 'basket_tournament_payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, nullable=False)
    player_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, default='efectivo')  # 'transferencia', 'efectivo', 'otro'
    notes = Column(String, nullable=True)
    date = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<TournamentPayment(id={self.id}, tourn_id={self.tournament_id}, player_id={self.player_id}, amount={self.amount}, date='{self.date.strftime('%Y-%m-%d')}')>"


class TournamentMatch(Base):
    __tablename__ = 'basket_tournament_matches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, nullable=False)
    opponent = Column(String, default='Rival no especificado', nullable=True)
    team_score = Column(Integer, nullable=True)
    opponent_score = Column(Integer, nullable=True)
    is_win = Column(Integer, nullable=False)  # 1 win, 0 loss
    match_type = Column(String, default='jornada')  # 'jornada', 'cuartos', 'semifinal', 'final', 'amistoso'
    notes = Column(String, nullable=True)
    date = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        score_str = f"{self.team_score}-{self.opponent_score}" if self.team_score is not None and self.opponent_score is not None else ("Win" if self.is_win else "Loss")
        return f"<TournamentMatch(id={self.id}, vs='{self.opponent}', score={score_str}, win={self.is_win})>"


# Create all tables in the engine (equivalent to "CREATE TABLE IF NOT EXISTS")
Base.metadata.create_all(engine)

# Dynamic schema migration: add columns to tables if they don't exist
from sqlalchemy import text

# Update expenses table for currency (runs in isolated transaction)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE expenses ADD COLUMN currency VARCHAR DEFAULT 'MXN'"))
except Exception:
    pass  # Column already exists or dialect handles it differently
    
# Update workout_logs table for metrics (runs in isolated transaction)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE workout_logs ADD COLUMN metrics JSON"))
except Exception:
    pass  # Column already exists or dialect handles it differently

# Update basket tables for jersey numbers (runs in isolated transaction)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE basket_players ADD COLUMN jersey_number INTEGER"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE basket_tournament_players ADD COLUMN jersey_number INTEGER"))
except Exception:
    pass

# Make opponent and scores nullable in basket_tournament_matches (flexible match tracking)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE basket_tournament_matches ALTER COLUMN opponent DROP NOT NULL"))
        conn.execute(text("ALTER TABLE basket_tournament_matches ALTER COLUMN opponent SET DEFAULT 'Rival no especificado'"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE basket_tournament_matches ALTER COLUMN team_score DROP NOT NULL"))
        conn.execute(text("ALTER TABLE basket_tournament_matches ALTER COLUMN opponent_score DROP NOT NULL"))
except Exception:
    pass

# Create a configured "Session" class
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

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
        dt = get_now_cdmx()
        if date_str:
            try:
                parsed_dt = datetime.strptime(date_str, '%Y-%m-%d')
                # If date_str equals today's date in CDMX, preserve current exact time
                if parsed_dt.date() == dt.date():
                    pass
                else:
                    dt = parsed_dt
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
            start_date = get_now_cdmx() - timedelta(days=days_back)
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

def add_workout_log(workout_type: str, duration_minutes: int = None, intensity: str = None, description: str = None, metrics: dict = None, date_str: str = None):
    """Utility function to add a new workout log."""
    session = get_session()
    try:
        dt = get_now_cdmx()
        if date_str:
            try:
                parsed_dt = datetime.strptime(date_str, '%Y-%m-%d')
                if parsed_dt.date() == dt.date():
                    pass
                else:
                    dt = parsed_dt
            except ValueError:
                pass  # Fallback to now
                
        new_workout = WorkoutLog(
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            intensity=intensity,
            description=description,
            metrics=metrics,
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
            start_date = get_now_cdmx() - timedelta(days=days_back)
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

def edit_workout_log(workout_id: int, workout_type: str = None, duration_minutes: int = None, intensity: str = None, description: str = None, metrics: dict = None, date_str: str = None):
    """Utility function to edit an existing workout log."""
    session = get_session()
    try:
        workout = session.query(WorkoutLog).filter(WorkoutLog.id == workout_id).first()
        if not workout:
            return None
            
        if workout_type is not None:
            workout.workout_type = workout_type
        if duration_minutes is not None:
            workout.duration_minutes = duration_minutes
        if intensity is not None:
            workout.intensity = intensity
        if description is not None:
            workout.description = description
        if metrics is not None:
            workout.metrics = metrics
        if date_str is not None:
            try:
                workout.date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass
                
        session.commit()
        session.refresh(workout)
        return workout
    finally:
        session.close()



# ==========================================
# HOBBY DATABASE HELPER METHODS
# ==========================================

def add_hobby(name: str, category: str = None, description: str = None, icon: str = None):
    """Utility function to add a new hobby."""
    session = get_session()
    try:
        new_hobby = Hobby(
            name=name,
            category=category,
            description=description,
            icon=icon
        )
        session.add(new_hobby)
        session.commit()
        session.refresh(new_hobby)
        return new_hobby
    finally:
        session.close()

def get_hobbies(category: str = None):
    """Utility function to get all hobbies, optionally filtered by category."""
    session = get_session()
    try:
        query = session.query(Hobby)
        if category:
            query = query.filter(Hobby.category.ilike(f"%{category}%"))
        return query.order_by(Hobby.name.asc()).all()
    finally:
        session.close()

def get_hobby(hobby_id: int):
    """Utility function to get a single hobby by ID."""
    session = get_session()
    try:
        return session.query(Hobby).filter(Hobby.id == hobby_id).first()
    finally:
        session.close()

def delete_hobby(hobby_id: int):
    """Utility function to delete a hobby by ID."""
    session = get_session()
    try:
        hobby = session.query(Hobby).filter(Hobby.id == hobby_id).first()
        if hobby:
            session.delete(hobby)
            session.commit()
            return True
        return False
    finally:
        session.close()

def edit_hobby(hobby_id: int, name: str = None, category: str = None, description: str = None, icon: str = None):
    """Utility function to edit an existing hobby."""
    session = get_session()
    try:
        hobby = session.query(Hobby).filter(Hobby.id == hobby_id).first()
        if not hobby:
            return None
            
        if name is not None:
            hobby.name = name
        if category is not None:
            hobby.category = category
        if description is not None:
            hobby.description = description
        if icon is not None:
            hobby.icon = icon
            
        session.commit()
        session.refresh(hobby)
        return hobby
    finally:
        session.close()


# ==========================================
# BASKETBALL DATABASE HELPER METHODS
# ==========================================

import unicodedata

def normalize_text(text: str) -> str:
    """Removes accents, lowercases and strips whitespace."""
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


def get_effective_player_jersey(player: Player, tournament_id: int = None, session = None) -> int | None:
    """Returns effective jersey number for a player, checking TournamentPlayer first, then Player."""
    if tournament_id and session:
        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tournament_id,
            TournamentPlayer.player_id == player.id
        ).first()
        if tp and tp.jersey_number is not None:
            return tp.jersey_number
    return player.jersey_number


def find_matching_players(name_query: str, tournament_id: int = None, session = None) -> list[Player]:
    """Finds players by exact, token, or partial name match, prioritizing tournament roster and handling jersey numbers."""
    import re
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        # Extract jersey number if specified like '#15', 'jersey 15', 'numero 15', or pure digits
        jersey_match = re.search(r'(?:#|jersey|numero|número|no\.?|num\.?)\s*(\d+)', name_query, re.IGNORECASE)
        extracted_jersey = int(jersey_match.group(1)) if jersey_match else None
        if extracted_jersey is None and name_query.strip().isdigit():
            extracted_jersey = int(name_query.strip())

        cleaned_query = re.sub(r'(?:#|jersey|numero|número|no\.?|num\.?)\s*\d+', '', name_query, flags=re.IGNORECASE).strip()
        q_norm = normalize_text(cleaned_query)

        if not q_norm and extracted_jersey is None:
            return []

        tournament_players = []
        if tournament_id:
            tournament_players = (
                session.query(Player)
                .join(TournamentPlayer, TournamentPlayer.player_id == Player.id)
                .filter(TournamentPlayer.tournament_id == tournament_id)
                .all()
            )

        all_players = session.query(Player).all()

        def match_score(p: Player, is_in_tourn: bool) -> int | None:
            p_name_norm = normalize_text(p.name)
            p_nick_norm = normalize_text(p.nickname) if p.nickname else ""
            p_tokens = set(p_name_norm.split())
            if p_nick_norm:
                p_tokens.update(p_nick_norm.split())
            eff_jersey = get_effective_player_jersey(p, tournament_id, session)

            # Query is just jersey number (e.g. '#15')
            if not q_norm and extracted_jersey is not None:
                if eff_jersey == extracted_jersey:
                    return 1 if is_in_tourn else 2
                return None

            # Exact name or nickname match
            if q_norm == p_name_norm or (p_nick_norm and q_norm == p_nick_norm):
                if extracted_jersey is not None:
                    if eff_jersey == extracted_jersey:
                        return 1 if is_in_tourn else 2
                    return None  # conflicting jersey specified
                return 1 if is_in_tourn else 2

            q_tokens = set(q_norm.split())

            # Tokens exactly equal
            if q_tokens == p_tokens:
                if extracted_jersey is not None:
                    if eff_jersey == extracted_jersey:
                        return 1 if is_in_tourn else 2
                    return None
                return 3 if is_in_tourn else 4

            # One is subset of the other (e.g. 'Saul' matches 'Saul Morales')
            if q_tokens.issubset(p_tokens) or p_tokens.issubset(q_tokens):
                if extracted_jersey is not None:
                    if eff_jersey == extracted_jersey:
                        return 2 if is_in_tourn else 3
                    return None
                return 5 if is_in_tourn else 6

            # If jersey matches and tokens intersect
            if extracted_jersey is not None and eff_jersey == extracted_jersey and q_tokens.intersection(p_tokens):
                return 3 if is_in_tourn else 4

            # Partial token intersection (e.g. shares only last name like 'Morales')
            if q_tokens.intersection(p_tokens):
                return 15 if is_in_tourn else 16

            if q_norm in p_name_norm or p_name_norm in q_norm or (p_nick_norm and q_norm in p_nick_norm):
                return 20 if is_in_tourn else 21

            return None

        tourn_player_ids = {p.id for p in tournament_players}
        scored = []

        for p in tournament_players:
            sc = match_score(p, is_in_tourn=True)
            if sc is not None:
                scored.append((sc, p))

        # If no tournament player matched, search general catalog
        if not scored:
            for p in all_players:
                if p.id in tourn_player_ids:
                    continue
                sc = match_score(p, is_in_tourn=False)
                if sc is not None:
                    scored.append((sc, p))

        scored.sort(key=lambda x: x[0])

        # If we have strong matches (score <= 6: exact, equal tokens, or subsets), discard weak partial overlaps (score >= 15)
        if scored:
            best_score = scored[0][0]
            if best_score <= 6:
                scored = [item for item in scored if item[0] <= 6]

        seen = set()
        results = []
        for _, p in scored:
            if p.id not in seen:
                seen.add(p.id)
                results.append(p)
        return results
    finally:
        if close_sess:
            session.close()


def resolve_player_for_tournament(name_query: str, tournament_id: int = None, session = None) -> tuple[str, Player | None, list[Player]]:
    """Resolves a player query into:
    - ('EXACT', player, [player]): Exact match.
    - ('SIMILAR_ONE', candidate, [candidate]): Found exactly 1 similar player.
    - ('AMBIGUOUS', None, [p1, p2, ...]): Found 2 or more similar candidates.
    - ('NOT_FOUND', None, []): No matching candidate found.
    """
    import re
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        jersey_match = re.search(r'(?:#|jersey|numero|número|no\.?|num\.?)\s*(\d+)', name_query, re.IGNORECASE)
        extracted_jersey = int(jersey_match.group(1)) if jersey_match else None
        if extracted_jersey is None and name_query.strip().isdigit():
            extracted_jersey = int(name_query.strip())

        cleaned_query = re.sub(r'(?:#|jersey|numero|número|no\.?|num\.?)\s*\d+', '', name_query, flags=re.IGNORECASE).strip()
        q_norm = normalize_text(cleaned_query)

        candidates = find_matching_players(name_query, tournament_id=tournament_id, session=session)
        if not candidates:
            return "NOT_FOUND", None, []

        # If query was solely jersey number
        if not q_norm and extracted_jersey is not None:
            if len(candidates) == 1:
                return "EXACT", candidates[0], candidates
            return "AMBIGUOUS", None, candidates

        # Check exact match on cleaned name or nickname
        for p in candidates:
            eff_jersey = get_effective_player_jersey(p, tournament_id, session)
            p_name_norm = normalize_text(p.name)
            p_nick_norm = normalize_text(p.nickname) if p.nickname else ""
            if p_name_norm == q_norm or (p_nick_norm and p_nick_norm == q_norm):
                if extracted_jersey is not None and eff_jersey is not None and eff_jersey != extracted_jersey:
                    continue
                return "EXACT", p, [p]

        # Check if extracted jersey uniquely confirms one candidate
        if extracted_jersey is not None:
            j_matches = [p for p in candidates if get_effective_player_jersey(p, tournament_id, session) == extracted_jersey]
            if len(j_matches) == 1:
                return "EXACT", j_matches[0], [j_matches[0]]

        if len(candidates) == 1:
            return "SIMILAR_ONE", candidates[0], candidates

        return "AMBIGUOUS", None, candidates
    finally:
        if close_sess:
            session.close()


def get_or_create_player(name: str, nickname: str = None, phone: str = None, session = None) -> Player:
    """Gets an existing player by name (case-insensitive) or creates a new one."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        clean_name = name.strip()
        player = session.query(Player).filter(Player.name.ilike(clean_name)).first()
        if not player and nickname:
            player = session.query(Player).filter(Player.nickname.ilike(nickname.strip())).first()
            
        if not player:
            player = Player(
                name=clean_name,
                nickname=nickname.strip() if nickname else None,
                phone=phone.strip() if phone else None,
                is_active=1
            )
            session.add(player)
            session.commit()
            session.refresh(player)
        else:
            updated = False
            if nickname and not player.nickname:
                player.nickname = nickname.strip()
                updated = True
            if phone and not player.phone:
                player.phone = phone.strip()
                updated = True
            if updated:
                session.commit()
                session.refresh(player)
        return player
    finally:
        if close_sess:
            session.close()

def get_player(player_name_or_id, session = None) -> Player | None:
    """Finds a player by ID or case-insensitive exact/normalized name."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        if isinstance(player_name_or_id, int) or (isinstance(player_name_or_id, str) and str(player_name_or_id).isdigit()):
            p = session.query(Player).filter(Player.id == int(player_name_or_id)).first()
            if p:
                return p
        clean = str(player_name_or_id).strip()
        p = session.query(Player).filter(Player.name.ilike(clean)).first()
        if not p:
            q_norm = normalize_text(clean)
            all_p = session.query(Player).all()
            for cand in all_p:
                if normalize_text(cand.name) == q_norm or (cand.nickname and normalize_text(cand.nickname) == q_norm):
                    return cand
        return p
    finally:
        if close_sess:
            session.close()

def get_all_players():
    """Retrieve all players from the catalog."""
    session = get_session()
    try:
        return session.query(Player).order_by(Player.name.asc()).all()
    finally:
        session.close()

def edit_player(player_id: int, name: str = None, nickname: str = None, phone: str = None, jersey_number: int = None):
    """Edit a player's profile info."""
    session = get_session()
    try:
        player = session.query(Player).filter(Player.id == player_id).first()
        if not player:
            return None
        if name is not None:
            player.name = name.strip()
        if nickname is not None:
            player.nickname = nickname.strip()
        if phone is not None:
            player.phone = phone.strip()
        if jersey_number is not None:
            player.jersey_number = jersey_number
        session.commit()
        session.refresh(player)
        return player
    finally:
        session.close()

def find_similar_tournaments(name_query: str, session = None) -> list[Tournament]:
    """Finds tournaments that have similar names, keywords, or bidirectional substring matches."""
    import re
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        query_str = str(name_query).strip().lower()
        if not query_str:
            return []
        
        all_tournaments = session.query(Tournament).all()
        matches = []
        
        stopwords = {"torneo", "liga", "copa", "de", "del", "el", "la", "los", "las", "basket", "basketball"}
        query_words = [w for w in re.findall(r'\b\w+\b', query_str) if w not in stopwords]
        
        for t in all_tournaments:
            t_name_lower = t.name.lower()
            # 1. Exact match
            if t_name_lower == query_str:
                matches.append(t)
                continue
            # 2. Bidirectional substring match
            if query_str in t_name_lower or t_name_lower in query_str:
                matches.append(t)
                continue
            # 3. Meaningful keyword overlap
            t_words = [w for w in re.findall(r'\b\w+\b', t_name_lower) if w not in stopwords]
            common_words = set(query_words).intersection(set(t_words))
            if common_words:
                matches.append(t)
                
        seen = set()
        unique_matches = []
        for m in matches:
            if m.id not in seen:
                seen.add(m.id)
                unique_matches.append(m)
        return unique_matches
    finally:
        if close_sess:
            session.close()


def add_tournament(name: str, team_name: str = "Mi Equipo", total_cost: float = 0.0, 
                   registration_fee: float = 0.0, referee_fee_total: float = 0.0,
                   force_create: bool = False) -> Tournament:
    """Creates a new basketball tournament or updates existing if a matching/similar one exists."""
    session = get_session()
    try:
        clean_name = name.strip()
        calculated_total = total_cost
        if calculated_total == 0.0 and (registration_fee > 0 or referee_fee_total > 0):
            calculated_total = registration_fee + referee_fee_total

        # 1. Check exact match
        existing = session.query(Tournament).filter(Tournament.name.ilike(clean_name)).first()
        
        # 2. If not found and not forcing creation, check similar existing tournament
        if not existing and not force_create:
            similar = find_similar_tournaments(clean_name, session=session)
            if similar:
                existing = similar[0]

        if existing:
            if calculated_total > 0:
                existing.total_cost = calculated_total
            if registration_fee > 0:
                existing.registration_fee = registration_fee
            if referee_fee_total > 0:
                existing.referee_fee_total = referee_fee_total
            if team_name and team_name != "Mi Equipo":
                existing.team_name = team_name.strip()
            session.commit()
            session.refresh(existing)
            recalculate_tournament_quotas(existing.id, session=session)
            return existing

        tournament = Tournament(
            name=clean_name,
            team_name=team_name.strip() if team_name else "Mi Equipo",
            total_cost=calculated_total,
            registration_fee=registration_fee,
            referee_fee_total=referee_fee_total,
            status='active'
        )
        session.add(tournament)
        session.commit()
        session.refresh(tournament)
        return tournament
    finally:
        session.close()


def update_tournament_cost(tournament_id_or_name, total_cost: float = None, 
                           registration_fee: float = None, referee_fee_total: float = None, 
                           team_name: str = None) -> tuple[bool, str, Tournament | None]:
    """Updates tournament total costs, fees, or team name and automatically recalculates active player quotas."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, f"No se encontró ningún torneo que coincida con '{tournament_id_or_name}'.", None

        changes = []
        if total_cost is not None and total_cost > 0:
            tourn.total_cost = total_cost
            changes.append(f"Costo Total=${total_cost:.2f}")
        if registration_fee is not None and registration_fee >= 0:
            tourn.registration_fee = registration_fee
            changes.append(f"Inscripción=${registration_fee:.2f}")
        if referee_fee_total is not None and referee_fee_total >= 0:
            tourn.referee_fee_total = referee_fee_total
            changes.append(f"Arbitrajes=${referee_fee_total:.2f}")
        if team_name and team_name.strip():
            tourn.team_name = team_name.strip()
            changes.append(f"Equipo='{tourn.team_name}'")

        if not changes:
            return False, "No se proporcionaron nuevos montos ni datos para actualizar.", tourn

        session.commit()
        session.refresh(tourn)
        recalculate_tournament_quotas(tourn.id, session=session)
        
        rep = get_tournament_financial_report(tourn.id, session=session)
        new_quota = rep["active_players"][0]["assigned_quota"] if rep and rep["active_players"] else 0.0
        msg = (
            f"✅ Costos del torneo '{tourn.name}' actualizados ({', '.join(changes)}). "
            f"Nueva cuota por jugador activo: ${new_quota:.2f} MXN."
        )
        return True, msg, tourn
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating tournament cost: {e}")
        return False, f"Error al actualizar costo: {str(e)}", None
    finally:
        session.close()


def get_tournament(tournament_id_or_name, session = None) -> Tournament | None:
    """Finds a tournament by ID, exact name, forward substring, or fuzzy similarity."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        if tournament_id_or_name is None or str(tournament_id_or_name).strip().lower() in ("", "none", "null", "actual", "activo", "default"):
            active = session.query(Tournament).filter(Tournament.status == 'active').order_by(Tournament.created_at.desc()).all()
            if active:
                return active[0]
            all_t = session.query(Tournament).order_by(Tournament.created_at.desc()).all()
            return all_t[0] if all_t else None

        if isinstance(tournament_id_or_name, int) or (isinstance(tournament_id_or_name, str) and str(tournament_id_or_name).strip().isdigit()):
            t_id = int(tournament_id_or_name)
            return session.query(Tournament).filter(Tournament.id == t_id).first()
            
        name_str = str(tournament_id_or_name).strip()
        # 1. Exact match
        t = session.query(Tournament).filter(Tournament.name.ilike(name_str)).first()
        if t:
            return t
        # 2. Forward substring
        t = session.query(Tournament).filter(Tournament.name.ilike(f"%{name_str}%")).order_by(Tournament.created_at.desc()).first()
        if t:
            return t
        # 3. Bidirectional substring or keyword similarity
        similar = find_similar_tournaments(name_str, session=session)
        if similar:
            return similar[0]
        return None
    finally:
        if close_sess:
            session.close()

def get_active_tournaments():
    """Returns all active tournaments."""
    session = get_session()
    try:
        return session.query(Tournament).filter(Tournament.status == 'active').order_by(Tournament.created_at.desc()).all()
    finally:
        session.close()

def get_all_tournaments():
    """Returns all tournaments."""
    session = get_session()
    try:
        return session.query(Tournament).order_by(Tournament.created_at.desc()).all()
    finally:
        session.close()

def recalculate_tournament_quotas(tournament_id: int, session = None):
    """Core mathematical engine to dynamically calculate and balance tournament quotas."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        tourn = session.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tourn:
            return False

        roster = session.query(TournamentPlayer).filter(TournamentPlayer.tournament_id == tournament_id).all()
        if not roster:
            return True

        payments = session.query(TournamentPayment).filter(TournamentPayment.tournament_id == tournament_id).all()
        player_paid = {}
        for p in payments:
            player_paid[p.player_id] = player_paid.get(p.player_id, 0.0) + p.amount

        dropped_paid_total = 0.0
        custom_quota_total = 0.0
        active_regular = []

        for tp in roster:
            paid = player_paid.get(tp.player_id, 0.0)
            if tp.status in ['injured', 'dropped_out']:
                tp.assigned_quota = paid
                dropped_paid_total += paid
            elif tp.has_custom_quota == 1:
                custom_quota_total += tp.assigned_quota
            else:
                active_regular.append(tp)

        remaining_balance = tourn.total_cost - dropped_paid_total - custom_quota_total
        if remaining_balance < 0:
            remaining_balance = 0.0

        if active_regular:
            base_quota = round(remaining_balance / len(active_regular), 2)
            for tp in active_regular:
                tp.assigned_quota = base_quota

        session.commit()
        return True
    finally:
        if close_sess:
            session.close()

def parse_player_name_and_number(raw_entry) -> tuple[str, int | None]:
    """Extracts player name and jersey number from string like 'Omar #23' or dict."""
    import re
    if isinstance(raw_entry, dict):
        name = str(raw_entry.get("name") or raw_entry.get("nombre") or "").strip()
        num = raw_entry.get("jersey_number") or raw_entry.get("numero")
        try:
            num = int(num) if num is not None else None
        except (ValueError, TypeError):
            num = None
        return name, num

    text = str(raw_entry).strip()
    match = re.search(r'^(.*?)\s*(?:[#\-]|(?:\())\s*(\d+)(?:\))?$', text)
    if match:
        name = match.group(1).strip()
        try:
            num = int(match.group(2))
            return name, num
        except ValueError:
            pass
    return text, None


def add_players_to_tournament(tournament_id_or_name, player_names: list) -> tuple[bool, str, Tournament | None]:
    """Adds a list of player names (or names with numbers) to a tournament and recalculates quotas."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        added_count = 0
        existing_count = 0
        for entry in player_names:
            clean_name, jersey_num = parse_player_name_and_number(entry)
            if not clean_name:
                continue
            
            # Check if a matching player exists in catalog before blindly inserting
            existing_players = find_matching_players(clean_name, session=session)
            player = None
            if existing_players and (normalize_text(existing_players[0].name) == normalize_text(clean_name) or normalize_text(clean_name) in normalize_text(existing_players[0].name)):
                player = existing_players[0]
            else:
                player = get_or_create_player(clean_name, session=session)

            if jersey_num is not None and player.jersey_number is None:
                player.jersey_number = jersey_num
            
            tp = session.query(TournamentPlayer).filter(
                TournamentPlayer.tournament_id == tourn.id,
                TournamentPlayer.player_id == player.id
            ).first()
            
            if not tp:
                new_tp = TournamentPlayer(
                    tournament_id=tourn.id,
                    player_id=player.id,
                    jersey_number=jersey_num if jersey_num is not None else player.jersey_number,
                    status='active',
                    has_custom_quota=0,
                    assigned_quota=0.0
                )
                session.add(new_tp)
                added_count += 1
            else:
                if jersey_num is not None:
                    tp.jersey_number = jersey_num
                if tp.status != 'active':
                    tp.status = 'active'
                    tp.notes = None
                    added_count += 1
                else:
                    existing_count += 1
                    
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        return True, f"Se agregaron {added_count} jugador(es) al torneo.", tourn
    finally:
        session.close()


def set_player_jersey_number(player_name: str, jersey_number: int, tournament_id_or_name = None, force: bool = False) -> tuple[bool, str]:
    """Assigns or updates a player's jersey number globally and/or in a tournament, checking for teammate conflicts."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session) if tournament_id_or_name else None
        tourn_id = tourn.id if tourn else None
        
        status, player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn_id, session=session)
        if status in ("EXACT", "SIMILAR_ONE") and candidates:
            player = candidates[0]
        elif status == "AMBIGUOUS":
            names_str = ", ".join([f"'{c.name}'" for c in candidates])
            return False, f"⚠️ Hay varios jugadores con nombre similar: {names_str}. Por favor especifica el nombre completo."
        else:
            return False, f"⚠️ No se encontró al jugador '{player_name}'."

        if tourn and not force:
            active_tps = session.query(TournamentPlayer).filter(
                TournamentPlayer.tournament_id == tourn.id,
                TournamentPlayer.player_id != player.id,
                TournamentPlayer.status == 'active'
            ).all()
            for atp in active_tps:
                p_cat = session.query(Player).filter(Player.id == atp.player_id).first()
                eff_num = atp.jersey_number if atp.jersey_number is not None else (p_cat.jersey_number if p_cat else None)
                if eff_num == jersey_number:
                    conflict_name = p_cat.name if p_cat else f"Jugador #{atp.player_id}"
                    return False, f"⚠️ El número #{jersey_number} ya está asignado a '{conflict_name}' en el equipo del torneo '{tourn.name}'. Si deseas reasignarlo de todas formas, confirma que deseas forzar el cambio."

        player.jersey_number = jersey_number
        if tourn:
            tp = session.query(TournamentPlayer).filter(
                TournamentPlayer.tournament_id == tourn.id,
                TournamentPlayer.player_id == player.id
            ).first()
            if tp:
                tp.jersey_number = jersey_number
        session.commit()
        return True, f"Número #{jersey_number} asignado a {player.name} exitosamente."
    except Exception as e:
        session.rollback()
        return False, f"Error al asignar número: {str(e)}"
    finally:
        session.close()

def set_player_custom_quota(tournament_id_or_name, player_name: str, custom_quota: float) -> tuple[bool, str]:
    """Sets a specific fixed quota for a player and re-balances the rest of the team."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado."
            
        status, player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
        if status in ("EXACT", "SIMILAR_ONE") and candidates:
            player = candidates[0]
        elif status == "AMBIGUOUS":
            names_str = ", ".join([f"'{c.name}'" for c in candidates])
            return False, f"⚠️ Hay varios jugadores con nombre similar en {tourn.name}: {names_str}. Por favor especifica el nombre completo."
        else:
            return False, f"⚠️ No se encontró al jugador '{player_name}' en el torneo {tourn.name}."
        
        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()
        
        if not tp:
            return False, f"El jugador {player.name} no está inscrito en el torneo {tourn.name}."
            
        tp.has_custom_quota = 1
        tp.assigned_quota = custom_quota
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        return True, f"Cuota personalizada de ${custom_quota:.2f} asignada a {player.name}."
    finally:
        session.close()

def reset_player_custom_quota(tournament_id_or_name, player_name: str) -> tuple[bool, str, dict | None]:
    """Resets a player's quota from manual/custom back to the automatic equitative team calculation."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        status, player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
        if status in ("EXACT", "SIMILAR_ONE") and candidates:
            player = candidates[0]
        elif status == "AMBIGUOUS":
            names_str = ", ".join([f"'{c.name}'" for c in candidates])
            return False, f"⚠️ Hay varios jugadores con nombre similar en {tourn.name}: {names_str}.", None
        else:
            return False, f"⚠️ No se encontró al jugador '{player_name}' en el torneo {tourn.name}.", None

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()

        if not tp:
            return False, f"El jugador {player.name} no está inscrito en el torneo {tourn.name}.", None

        tp.has_custom_quota = 0
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        session.refresh(tp)

        return True, f"✅ Cuota personalizada removida para {player.name}. Ahora participa en el recálculo equitativo del equipo con una cuota de ${tp.assigned_quota:.2f} MXN.", {
            "player_name": player.name,
            "tournament_name": tourn.name,
            "new_quota": tp.assigned_quota
        }
    finally:
        session.close()

def drop_player_from_tournament(tournament_id_or_name, player_name: str, reason: str = "lesion") -> tuple[bool, str, float]:
    """Marks a player as injured or dropped out, freezes their quota to their paid amount, and recalculates quotas."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", 0.0
            
        status, player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
        if status in ("EXACT", "SIMILAR_ONE") and candidates:
            player = candidates[0]
        elif status == "AMBIGUOUS":
            names_str = ", ".join([f"'{c.name}'" for c in candidates])
            return False, f"⚠️ Hay varios jugadores similares en {tourn.name}: {names_str}. Por favor indica el nombre completo.", 0.0
        else:
            return False, f"⚠️ No se encontró al jugador '{player_name}' en este torneo.", 0.0
        
        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()
        
        if not tp:
            return False, f"El jugador {player.name} no está en este torneo.", 0.0
            
        r_lower = reason.lower()
        tp.status = 'injured' if ('lesion' in r_lower or 'lesión' in r_lower) else 'dropped_out'
        tp.notes = reason
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        
        active_tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.status == 'active',
            TournamentPlayer.has_custom_quota == 0
        ).first()
        new_quota = active_tp.assigned_quota if active_tp else 0.0
            
        return True, f"Jugador {player.name} dado de baja ({tp.status}).", new_quota
    finally:
        session.close()

def reactivate_player_in_tournament(tournament_id_or_name, player_name: str, 
                                    confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Reactivates an injured or dropped out player in a tournament, setting status back to 'active' 
    and recalculating quotas equitably among all active players.
    """
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()

        if not player:
            status, matched_player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
            if status == "EXACT":
                player = matched_player
            elif status == "SIMILAR_ONE":
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{player_name}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en el torneo '{tourn.name}'. "
                    f"¿Te refieres a él para reactivarlo?\n"
                    f"Confírmamelo diciendo 'Sí, a {sug.name}'."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            elif status == "AMBIGUOUS":
                names_str = ", ".join([f"'{c.name}'" + (f" (#{c.jersey_number})" if c.jersey_number else "") for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en el torneo '{tourn.name}': {names_str}.\n"
                    f"¿A cuál de ellos deseas reactivar?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}
            else:
                return False, f"⚠️ No encontré al jugador '{player_name}' en el torneo '{tourn.name}'.", {"status": "NOT_FOUND"}

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()

        if not tp:
            return False, f"El jugador '{player.name}' no está inscrito en el torneo '{tourn.name}'.", None

        if tp.status == 'active':
            return False, f"El jugador '{player.name}' ya se encuentra como activo en el torneo '{tourn.name}'.", None

        prev_status = tp.status
        tp.status = 'active'
        tp.notes = None
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)

        # Retrieve newly recalculated quota for regular active players
        active_tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.status == 'active',
            TournamentPlayer.has_custom_quota == 0
        ).first()
        new_quota = active_tp.assigned_quota if active_tp else 0.0

        all_active = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.status == 'active'
        ).all()

        rdata = {
            "player_id": player.id,
            "player_name": player.name,
            "tournament_id": tourn.id,
            "tournament_name": tourn.name,
            "previous_status": prev_status,
            "new_status": "active",
            "new_quota_per_active_player": new_quota,
            "total_active_players": len(all_active)
        }
        return True, (
            f"✅ ¡Jugador {player.name} reactivado exitosamente en '{tourn.name}'! "
            f"Vuelve a estar activo en el equipo y la nueva cuota recalculada para los jugadores activos es de ${new_quota:.2f} MXN."
        ), rdata
    finally:
        session.close()

def remove_player_from_tournament(tournament_id_or_name, player_name: str, 
                                  confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Removes a player from a tournament roster completely (e.g. if enrolled by mistake), 
    deleting their tournament membership and associated tournament payments, and recalculating active quotas.
    Crucially keeps the player in the global database Player catalog so they can join other tournaments/teams.
    """
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()

        if not player:
            status, matched_player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
            if status == "EXACT":
                player = matched_player
            elif status == "SIMILAR_ONE":
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{player_name}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en el torneo '{tourn.name}'. "
                    f"¿Te refieres a él para removerlo de este torneo?\n"
                    f"Confírmamelo diciendo 'Sí, a {sug.name}'."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            elif status == "AMBIGUOUS":
                names_str = ", ".join([f"'{c.name}'" + (f" (#{c.jersey_number})" if c.jersey_number else "") for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en el torneo '{tourn.name}': {names_str}.\n"
                    f"¿A cuál de ellos deseas remover del torneo?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}
            else:
                return False, f"⚠️ No encontré al jugador '{player_name}' en el torneo '{tourn.name}'.", {"status": "NOT_FOUND"}

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()

        if not tp:
            return False, f"El jugador '{player.name}' no está inscrito en el torneo '{tourn.name}'.", None

        # Clean up any payments recorded for this player in this tournament (since enrolled by mistake)
        payments = session.query(TournamentPayment).filter(
            TournamentPayment.tournament_id == tourn.id,
            TournamentPayment.player_id == player.id
        ).all()
        total_payments_deleted = sum(p.amount for p in payments)
        for p in payments:
            session.delete(p)

        session.delete(tp)
        session.commit()

        # Recalculate remaining active players' quotas
        recalculate_tournament_quotas(tourn.id, session=session)

        active_tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.status == 'active',
            TournamentPlayer.has_custom_quota == 0
        ).first()
        new_quota = active_tp.assigned_quota if active_tp else 0.0

        result_data = {
            "player_id": player.id,
            "player_name": player.name,
            "tournament_id": tourn.id,
            "tournament_name": tourn.name,
            "new_quota_per_active_player": new_quota,
            "removed_payments_total": total_payments_deleted,
            "still_in_database": True
        }
        return True, (
            f"✅ Jugador '{player.name}' removido exitosamente del torneo '{tourn.name}'. "
            f"El jugador se mantiene en la base de datos para agregarlo a otro equipo o torneo. "
            f"Nueva cuota recalculada por jugador activo: ${new_quota:.2f} MXN."
        ), result_data
    finally:
        session.close()

def delete_player_completely(player_name_or_id, confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Permanently deletes a player from the entire database (Player table, all tournament rosters, and payments)."""
    session = get_session()
    try:
        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()

        if not player:
            if isinstance(player_name_or_id, int) or (isinstance(player_name_or_id, str) and str(player_name_or_id).isdigit()):
                player = session.query(Player).filter(Player.id == int(player_name_or_id)).first()

        if not player:
            name_str = str(player_name_or_id).strip()
            candidates = find_matching_players(name_str, session=session)
            if not candidates:
                return False, f"⚠️ No se encontró al jugador '{name_str}' en la base de datos.", None

            q_norm = normalize_text(name_str)
            exact = [c for c in candidates if normalize_text(c.name) == q_norm or (c.nickname and normalize_text(c.nickname) == q_norm)]
            if exact:
                player = exact[0]
            elif len(candidates) == 1:
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{name_str}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en la base de datos. "
                    f"¿Deseas eliminar completamente a '{sug.name}' de todo el sistema?\n"
                    f"Confírmamelo diciendo 'Sí, elimina a {sug.name}'."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            else:
                names_str = ", ".join([f"'{c.name}'" for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en la base de datos: {names_str}.\n"
                    f"¿A cuál de ellos deseas eliminar definitivamente?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}

        player_id = player.id
        player_name = player.name

        rosters = session.query(TournamentPlayer).filter(TournamentPlayer.player_id == player_id).all()
        affected_tourn_ids = list(set([r.tournament_id for r in rosters]))

        payments_deleted = session.query(TournamentPayment).filter(TournamentPayment.player_id == player_id).delete(synchronize_session=False)
        rosters_deleted = session.query(TournamentPlayer).filter(TournamentPlayer.player_id == player_id).delete(synchronize_session=False)

        session.delete(player)
        session.commit()

        for t_id in affected_tourn_ids:
            recalculate_tournament_quotas(t_id, session=session)

        result_data = {
            "player_id": player_id,
            "player_name": player_name,
            "affected_tournaments_count": len(affected_tourn_ids),
            "payments_deleted": payments_deleted,
            "rosters_deleted": rosters_deleted,
            "completely_deleted": True
        }
        return True, (
            f"🗑️ Jugador '{player_name}' eliminado permanentemente de la base de datos "
            f"(removido de {len(affected_tourn_ids)} torneo(s) y {payments_deleted} pago(s) borrados)."
        ), result_data
    finally:
        session.close()

def record_tournament_payment(tournament_id_or_name, player_name: str, amount: float, 
                              payment_method: str = "efectivo", notes: str = None, 
                              date_str: str = None, force_create_player: bool = False,
                              confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Records a payment from a player for a tournament, ensuring disambiguation and similarity confirmation."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()
        
        if not player:
            status, matched_player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
            
            if status == "EXACT":
                player = matched_player
            elif status == "SIMILAR_ONE" and not force_create_player:
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{player_name}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en el torneo '{tourn.name}'. "
                    f"¿Te refieres a él para registrar el pago de ${amount:.2f} MXN?\n"
                    f"Confírmamelo diciendo 'Sí, a {sug.name}', o indícame si deseas inscribirlo como un jugador nuevo."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            elif status == "AMBIGUOUS" and not force_create_player:
                names_str = ", ".join([f"'{c.name}'" + (f" (#{c.jersey_number})" if c.jersey_number else "") for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en el torneo '{tourn.name}': {names_str}.\n"
                    f"¿A cuál de ellos corresponde el pago de ${amount:.2f} MXN?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}
            elif status == "NOT_FOUND" and not force_create_player:
                return False, (
                    f"⚠️ No encontré a ningún jugador llamado o similar a '{player_name}' en el torneo '{tourn.name}'.\n"
                    f"¿Deseas inscribir a '{player_name}' como un jugador nuevo en este torneo?"
                ), {"status": "NOT_FOUND"}
            else:
                player = get_or_create_player(player_name, session=session)

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()
        
        if not tp:
            tp = TournamentPlayer(
                tournament_id=tourn.id,
                player_id=player.id,
                status='active',
                has_custom_quota=0,
                assigned_quota=0.0
            )
            session.add(tp)
            session.commit()
            recalculate_tournament_quotas(tourn.id, session=session)

        dt = get_now_cdmx()
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass

        payment = TournamentPayment(
            tournament_id=tourn.id,
            player_id=player.id,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            date=dt
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
        
        all_payments = session.query(TournamentPayment).filter(
            TournamentPayment.tournament_id == tourn.id,
            TournamentPayment.player_id == player.id
        ).all()
        total_paid = sum(p.amount for p in all_payments)
        
        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()
        
        quota = tp.assigned_quota if tp else 0.0
        remaining = max(0.0, quota - total_paid)
        
        result_data = {
            "payment_id": payment.id,
            "player_name": player.name,
            "tournament_name": tourn.name,
            "amount_paid": amount,
            "total_paid": total_paid,
            "quota": quota,
            "remaining": remaining,
            "is_paid_off": remaining <= 0.0
        }
        return True, "Pago registrado exitosamente.", result_data
    finally:
        session.close()

def delete_tournament_payment(payment_id: int) -> bool:
    """Deletes a tournament payment by ID."""
    session = get_session()
    try:
        payment = session.query(TournamentPayment).filter(TournamentPayment.id == payment_id).first()
        if not payment:
            return False
        tourn_id = payment.tournament_id
        session.delete(payment)
        session.commit()
        recalculate_tournament_quotas(tourn_id, session=session)
        return True
    finally:
        session.close()

def adjust_player_total_paid(tournament_id_or_name, player_name: str, new_total_paid: float, 
                             notes: str = None, force_create_player: bool = False,
                             confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Adjusts/overrides the total amount paid by a player in a tournament, allowing seamless correction of mistakes."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()

        if not player:
            status, matched_player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
            if status == "EXACT":
                player = matched_player
            elif status == "SIMILAR_ONE" and not force_create_player:
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{player_name}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en el torneo '{tourn.name}'. "
                    f"¿Te refieres a él para ajustar su total pagado a ${new_total_paid:.2f} MXN?\n"
                    f"Confírmamelo diciendo 'Sí, a {sug.name}'."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            elif status == "AMBIGUOUS" and not force_create_player:
                names_str = ", ".join([f"'{c.name}'" + (f" (#{c.jersey_number})" if c.jersey_number else "") for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en el torneo '{tourn.name}': {names_str}.\n"
                    f"¿A cuál de ellos deseas modificarle el total pagado a ${new_total_paid:.2f} MXN?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}
            elif status == "NOT_FOUND" and not force_create_player:
                return False, (
                    f"⚠️ No encontré a ningún jugador llamado o similar a '{player_name}' en el torneo '{tourn.name}'."
                ), {"status": "NOT_FOUND"}
            else:
                player = get_or_create_player(player_name, session=session)

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()

        if not tp:
            return False, f"El jugador '{player.name}' no está inscrito en el torneo '{tourn.name}'.", None

        if new_total_paid < 0:
            return False, "El total pagado no puede ser un número negativo.", None

        existing_payments = session.query(TournamentPayment).filter(
            TournamentPayment.tournament_id == tourn.id,
            TournamentPayment.player_id == player.id
        ).order_by(TournamentPayment.date.asc(), TournamentPayment.id.asc()).all()

        prev_total = sum(p.amount for p in existing_payments)
        dt = get_now_cdmx()

        if new_total_paid == 0.0:
            for p in existing_payments:
                session.delete(p)
            session.commit()
        elif len(existing_payments) == 0:
            new_p = TournamentPayment(
                tournament_id=tourn.id,
                player_id=player.id,
                amount=new_total_paid,
                payment_method="ajuste",
                notes=notes or "Ajuste directo de total pagado",
                date=dt
            )
            session.add(new_p)
            session.commit()
        elif len(existing_payments) == 1:
            existing_payments[0].amount = new_total_paid
            note_suffix = f" [Total corregido de ${prev_total:.2f} a ${new_total_paid:.2f}]"
            existing_payments[0].notes = notes or ((existing_payments[0].notes or "") + note_suffix).strip()
            existing_payments[0].date = dt
            session.commit()
        else:
            for p in existing_payments:
                session.delete(p)
            new_p = TournamentPayment(
                tournament_id=tourn.id,
                player_id=player.id,
                amount=new_total_paid,
                payment_method="ajuste",
                notes=notes or f"Total corregido a ${new_total_paid:.2f} (previo acumulado en varios abonos: ${prev_total:.2f})",
                date=dt
            )
            session.add(new_p)
            session.commit()

        recalculate_tournament_quotas(tourn.id, session=session)
        session.refresh(tp)

        quota = tp.assigned_quota or 0.0
        remaining = max(0.0, quota - new_total_paid)
        is_paid_off = remaining <= 0.0 and quota > 0

        result_data = {
            "player_name": player.name,
            "tournament_name": tourn.name,
            "previous_total": prev_total,
            "new_total_paid": new_total_paid,
            "quota": quota,
            "remaining": remaining,
            "is_paid_off": is_paid_off
        }
        return True, f"Total pagado de {player.name} actualizado exitosamente de ${prev_total:.2f} a ${new_total_paid:.2f} MXN.", result_data
    finally:
        session.close()

def delete_last_player_payment(tournament_id_or_name, player_name: str, 
                               confirmed_player_id: int = None) -> tuple[bool, str, dict | None]:
    """Deletes the most recent payment made by a player in a tournament."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        player = None
        if confirmed_player_id:
            player = session.query(Player).filter(Player.id == confirmed_player_id).first()

        if not player:
            status, matched_player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn.id, session=session)
            if status == "EXACT":
                player = matched_player
            elif status == "SIMILAR_ONE":
                sug = candidates[0]
                jersey_str = f" (#{sug.jersey_number})" if sug.jersey_number else ""
                return False, (
                    f"⚠️ No encontré a '{player_name}' con nombre exacto, pero encontré a '{sug.name}'{jersey_str} en el torneo '{tourn.name}'. "
                    f"¿Te refieres a él para eliminar su último pago?\n"
                    f"Confírmamelo diciendo 'Sí, a {sug.name}'."
                ), {"status": "SIMILAR_ONE", "suggested_player": sug.name, "suggested_id": sug.id}
            elif status == "AMBIGUOUS":
                names_str = ", ".join([f"'{c.name}'" + (f" (#{c.jersey_number})" if c.jersey_number else "") for c in candidates])
                return False, (
                    f"⚠️ Encontré varios jugadores con nombre similar en el torneo '{tourn.name}': {names_str}.\n"
                    f"¿A cuál de ellos deseas eliminarle el último pago?"
                ), {"status": "AMBIGUOUS", "candidates": [c.name for c in candidates]}
            else:
                return False, f"⚠️ No encontré al jugador '{player_name}' en el torneo '{tourn.name}'.", {"status": "NOT_FOUND"}

        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()

        last_p = session.query(TournamentPayment).filter(
            TournamentPayment.tournament_id == tourn.id,
            TournamentPayment.player_id == player.id
        ).order_by(TournamentPayment.date.desc(), TournamentPayment.id.desc()).first()

        if not last_p:
            return False, f"El jugador '{player.name}' no tiene pagos registrados en '{tourn.name}'.", None

        deleted_amount = last_p.amount
        session.delete(last_p)
        session.commit()

        recalculate_tournament_quotas(tourn.id, session=session)
        if tp:
            session.refresh(tp)

        remaining_payments = session.query(TournamentPayment).filter(
            TournamentPayment.tournament_id == tourn.id,
            TournamentPayment.player_id == player.id
        ).all()
        new_total = sum(p.amount for p in remaining_payments)
        quota = tp.assigned_quota if tp else 0.0
        remaining = max(0.0, quota - new_total)
        is_paid_off = remaining <= 0.0 and quota > 0

        result_data = {
            "player_name": player.name,
            "tournament_name": tourn.name,
            "deleted_amount": deleted_amount,
            "new_total_paid": new_total,
            "quota": quota,
            "remaining": remaining,
            "is_paid_off": is_paid_off
        }
        return True, f"Se eliminó el último pago de ${deleted_amount:.2f} MXN de {player.name}. Su nuevo total pagado es ${new_total:.2f} MXN.", result_data
    finally:
        session.close()

def record_tournament_match(tournament_id_or_name, 
                            resultado: str = None, 
                            opponent: str = None, 
                            team_score: int = None, 
                            opponent_score: int = None, 
                            is_win: bool = None,
                            match_type: str = "jornada", 
                            notes: str = None, 
                            date_str: str = None) -> tuple[bool, str, dict | None]:
    """Records a game/match result for a tournament. Outcome (is_win/resultado) and date are mandatory; opponent and scores are optional."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        # Determine win/loss
        is_win_val = None
        if is_win is not None:
            is_win_val = 1 if is_win else 0
        elif resultado:
            res_clean = str(resultado).lower().strip()
            is_win_val = 1 if any(w in res_clean for w in ["vic", "gan", "win", "triunf", "w"]) else 0
        elif team_score is not None and opponent_score is not None:
            is_win_val = 1 if team_score > opponent_score else 0

        if is_win_val is None:
            return False, "Debes indicar si el partido se ganó o se perdió ('victoria' o 'derrota') o proporcionar el marcador de puntos.", None

        dt = get_now_cdmx()
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass

        clean_opponent = opponent.strip() if opponent and opponent.strip() else "Rival no especificado"

        match = TournamentMatch(
            tournament_id=tourn.id,
            opponent=clean_opponent,
            team_score=team_score,
            opponent_score=opponent_score,
            is_win=is_win_val,
            match_type=match_type or "jornada",
            notes=notes,
            date=dt
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        
        all_matches = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn.id).all()
        wins = sum(1 for m in all_matches if m.is_win == 1)
        losses = len(all_matches) - wins
        
        score_display = f"{team_score} - {opponent_score}" if team_score is not None and opponent_score is not None else ("Victoria" if is_win_val == 1 else "Derrota")
        res_str = "Victoria" if is_win_val == 1 else "Derrota"
        opp_str = f" vs {clean_opponent}" if clean_opponent != "Rival no especificado" else ""
        score_detail = f" ({team_score} - {opponent_score})" if team_score is not None and opponent_score is not None else ""

        match_data = {
            "match_id": match.id,
            "tournament_name": tourn.name,
            "opponent": match.opponent,
            "score": score_display,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "is_win": bool(is_win_val),
            "match_type": match.match_type,
            "record": f"{wins}G - {losses}P",
            "date": dt.strftime("%Y-%m-%d")
        }
        return True, f"Partido registrado: {res_str}{opp_str}{score_detail}. Récord del torneo '{tourn.name}': {wins}G - {losses}P.", match_data
    finally:
        session.close()

def modify_last_tournament_match(tournament_id_or_name, 
                                 resultado: str = None,
                                 opponent: str = None, 
                                 team_score: int = None, 
                                 opponent_score: int = None, 
                                 is_win: bool = None,
                                 match_type: str = None, 
                                 notes: str = None, 
                                 match_id: int = None) -> tuple[bool, str, dict | None]:
    """Modifies or corrects an existing tournament match record (score, opponent, notes, outcome)."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        match = None
        if match_id:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.id == match_id,
                TournamentMatch.tournament_id == tourn.id
            ).first()
        elif opponent:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.tournament_id == tourn.id,
                TournamentMatch.opponent.ilike(f"%{opponent.strip()}%")
            ).order_by(TournamentMatch.date.desc(), TournamentMatch.id.desc()).first()
        else:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.tournament_id == tourn.id
            ).order_by(TournamentMatch.date.desc(), TournamentMatch.id.desc()).first()

        if not match:
            return False, f"No se encontró ningún partido para corregir en '{tourn.name}'.", None

        prev_score = f"{match.team_score} - {match.opponent_score} vs {match.opponent}" if match.team_score is not None and match.opponent_score is not None else f"{'Victoria' if match.is_win else 'Derrota'} vs {match.opponent}"
        if opponent:
            match.opponent = opponent.strip()
        if team_score is not None:
            match.team_score = team_score
        if opponent_score is not None:
            match.opponent_score = opponent_score

        if is_win is not None:
            match.is_win = 1 if is_win else 0
        elif resultado:
            res_clean = str(resultado).lower().strip()
            match.is_win = 1 if any(w in res_clean for w in ["vic", "gan", "win", "triunf", "w"]) else 0
        elif team_score is not None and opponent_score is not None:
            match.is_win = 1 if match.team_score > match.opponent_score else 0

        if match_type:
            match.match_type = match_type
        if notes:
            match.notes = notes

        session.commit()
        session.refresh(match)

        all_matches = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn.id).all()
        wins = sum(1 for m in all_matches if m.is_win == 1)
        losses = len(all_matches) - wins

        score_display = f"{match.team_score} - {match.opponent_score}" if match.team_score is not None and match.opponent_score is not None else ("Victoria" if match.is_win else "Derrota")
        res_str = "Victoria" if match.is_win else "Derrota"
        opp_str = f" vs {match.opponent}" if match.opponent and match.opponent != "Rival no especificado" else ""
        score_detail = f" ({match.team_score} - {match.opponent_score})" if match.team_score is not None and match.opponent_score is not None else ""

        match_data = {
            "match_id": match.id,
            "tournament_name": tourn.name,
            "opponent": match.opponent,
            "score": score_display,
            "team_score": match.team_score,
            "opponent_score": match.opponent_score,
            "is_win": bool(match.is_win),
            "match_type": match.match_type,
            "record": f"{wins}G - {losses}P",
            "previous_summary": prev_score
        }
        return True, (
            f"✅ Partido corregido en '{tourn.name}': {res_str}{opp_str}{score_detail}. "
            f"Récord del torneo: {wins}G - {losses}P."
        ), match_data
    finally:
        session.close()

def delete_last_tournament_match(tournament_id_or_name, opponent: str = None, 
                                 match_id: int = None) -> tuple[bool, str, dict | None]:
    """Deletes the latest recorded match (or a specific match against an opponent) and updates the record."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        match = None
        if match_id:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.id == match_id,
                TournamentMatch.tournament_id == tourn.id
            ).first()
        elif opponent:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.tournament_id == tourn.id,
                TournamentMatch.opponent.ilike(f"%{opponent.strip()}%")
            ).order_by(TournamentMatch.date.desc(), TournamentMatch.id.desc()).first()
        else:
            match = session.query(TournamentMatch).filter(
                TournamentMatch.tournament_id == tourn.id
            ).order_by(TournamentMatch.date.desc(), TournamentMatch.id.desc()).first()

        if not match:
            return False, f"No se encontró ningún partido para eliminar en '{tourn.name}'.", None

        score_part = f"({match.team_score} - {match.opponent_score})" if match.team_score is not None and match.opponent_score is not None else ("(Victoria)" if match.is_win else "(Derrota)")
        opp_part = f"vs {match.opponent}" if match.opponent and match.opponent != "Rival no especificado" else ""
        deleted_summary = f"{opp_part} {score_part}".strip()
        session.delete(match)
        session.commit()

        all_matches = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn.id).all()
        wins = sum(1 for m in all_matches if m.is_win == 1)
        losses = len(all_matches) - wins

        return True, (
            f"🗑️ Se eliminó el partido {deleted_summary} de '{tourn.name}'. "
            f"Récord actualizado: {wins}G - {losses}P."
        ), {"deleted_match": deleted_summary, "record": f"{wins}G - {losses}P"}
    finally:
        session.close()

def get_player_payment_history(player_name: str, tournament_id_or_name = None) -> tuple[bool, str, dict | None]:
    """Returns chronological itemized payment receipts and balances for a player."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session) if tournament_id_or_name else None
        tourn_id = tourn.id if tourn else None
        status, player, candidates = resolve_player_for_tournament(player_name, tournament_id=tourn_id, session=session)
        if status in ("EXACT", "SIMILAR_ONE") and candidates:
            player = candidates[0]
        elif status == "AMBIGUOUS":
            names_str = ", ".join([f"'{c.name}'" for c in candidates])
            return False, f"⚠️ Hay varios jugadores con nombre similar: {names_str}.", None
        else:
            return False, f"⚠️ No se encontró al jugador '{player_name}'.", None

        query = session.query(TournamentPayment).filter(TournamentPayment.player_id == player.id)
        if tourn:
            query = query.filter(TournamentPayment.tournament_id == tourn.id)
        
        payments = query.order_by(TournamentPayment.date.asc(), TournamentPayment.id.asc()).all()
        tournaments_map = {t.id: t.name for t in session.query(Tournament).all()}
        
        history = []
        running_total = 0.0
        for p in payments:
            running_total += p.amount
            history.append({
                "payment_id": p.id,
                "tournament_name": tournaments_map.get(p.tournament_id, f"Torneo #{p.tournament_id}"),
                "amount": p.amount,
                "payment_method": p.payment_method,
                "notes": p.notes or "",
                "date": p.date.strftime("%Y-%m-%d %H:%M")
            })

        tp = None
        if tourn:
            tp = session.query(TournamentPlayer).filter(
                TournamentPlayer.tournament_id == tourn.id,
                TournamentPlayer.player_id == player.id
            ).first()

        quota = tp.assigned_quota if tp else 0.0
        remaining = max(0.0, quota - running_total) if quota > 0 else 0.0

        result_data = {
            "player_id": player.id,
            "player_name": player.name,
            "total_paid": running_total,
            "quota": quota,
            "remaining": remaining,
            "is_paid_off": remaining <= 0.0 and quota > 0,
            "payments_count": len(payments),
            "payments": history
        }

        if not history:
            return True, f"El jugador '{player.name}' no tiene ningún abono o pago registrado aún.", result_data

        lines = [f"• #{p['payment_id']}: ${p['amount']:.2f} ({p['payment_method']}) el {p['date']} [{p['tournament_name']}] {('- ' + p['notes']) if p['notes'] else ''}" for p in history]
        msg = (
            f"📋 Historial de pagos de {player.name} ({len(history)} abono(s)):\n" +
            "\n".join(lines) +
            f"\n\nTotal pagado: ${running_total:.2f} MXN." +
            (f" Cuota: ${quota:.2f} MXN. Resta pagar: ${remaining:.2f} MXN." if quota > 0 else "")
        )
        return True, msg, result_data
    finally:
        session.close()

def update_tournament_result(tournament_id_or_name, playoff_seed: int = None, final_result: str = None, status: str = None):
    """Updates tournament playoff seed, final championship result or status."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return None
        t = session.query(Tournament).filter(Tournament.id == tourn.id).first()
        if playoff_seed is not None:
            t.playoff_seed = playoff_seed
        if final_result is not None:
            t.final_result = final_result
        if status is not None:
            t.status = status
        session.commit()
        session.refresh(t)
        return t
    finally:
        session.close()


def delete_tournament(tournament_id_or_name, delete_orphan_players: bool = False) -> tuple[bool, str, dict | None]:
    """Permanently deletes a tournament and all its related records in cascade.
    
    Deletes:
    - TournamentMatch (all matches and record)
    - TournamentPayment (all payments recorded for this tournament)
    - TournamentPlayer (all roster allocations and quota assignments)
    - Tournament (the tournament record itself)
    - If delete_orphan_players is True, deletes Player records that have no other tournaments.
    """
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        tourn_id = tourn.id
        tourn_name = tourn.name

        # 1. Matches
        matches_deleted = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn_id).delete(synchronize_session=False)

        # 2. Payments
        payments_deleted = session.query(TournamentPayment).filter(TournamentPayment.tournament_id == tourn_id).delete(synchronize_session=False)

        # Find players in this tournament before deleting roster
        tp_player_ids = [tp.player_id for tp in session.query(TournamentPlayer).filter(TournamentPlayer.tournament_id == tourn_id).all()]

        # 3. Roster / Quotas
        roster_deleted = session.query(TournamentPlayer).filter(TournamentPlayer.tournament_id == tourn_id).delete(synchronize_session=False)

        # 4. Tournament
        session.delete(tourn)

        # 5. Optional orphan player cleanup
        orphans_deleted = 0
        if delete_orphan_players and tp_player_ids:
            for p_id in tp_player_ids:
                other_tp = session.query(TournamentPlayer).filter(TournamentPlayer.player_id == p_id).first()
                if not other_tp:
                    p = session.query(Player).filter(Player.id == p_id).first()
                    if p:
                        session.delete(p)
                        orphans_deleted += 1

        session.commit()
        
        summary = {
            "tournament_id": tourn_id,
            "tournament_name": tourn_name,
            "deleted_matches": matches_deleted,
            "deleted_payments": payments_deleted,
            "deleted_roster_entries": roster_deleted,
            "deleted_orphan_players": orphans_deleted
        }
        msg = (
            f"Torneo '{tourn_name}' eliminado exitosamente con todos sus datos asociados: "
            f"{matches_deleted} partido(s), {payments_deleted} pago(s) y {roster_deleted} registro(s) de jugadores."
        )
        return True, msg, summary
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting tournament: {e}")
        return False, f"Error al eliminar torneo: {str(e)}", None
    finally:
        session.close()

def get_tournament_financial_report(tournament_id_or_name, session = None) -> dict | None:
    """Returns a rich dictionary with complete financial metrics, player rosters, debts and match records."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return None

        roster = session.query(TournamentPlayer).filter(TournamentPlayer.tournament_id == tourn.id).all()
        all_payments = session.query(TournamentPayment).filter(TournamentPayment.tournament_id == tourn.id).order_by(TournamentPayment.date.desc()).all()
        all_matches = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn.id).order_by(TournamentMatch.date.asc()).all()
        all_players = session.query(Player).all()
        players_map = {p.id: p for p in all_players}

        player_payments_map = {}
        for p in all_payments:
            if p.player_id not in player_payments_map:
                player_payments_map[p.player_id] = []
            player_payments_map[p.player_id].append({
                "id": p.id,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "notes": p.notes,
                "date": p.date.strftime("%Y-%m-%d %H:%M:%S")
            })

        active_players = []
        inactive_players = []
        total_collected = 0.0

        for tp in roster:
            p_obj = players_map.get(tp.player_id)
            p_name = p_obj.name if p_obj else f"Jugador #{tp.player_id}"
            p_nick = p_obj.nickname if p_obj else ""
            
            p_pay_list = player_payments_map.get(tp.player_id, [])
            p_total_paid = sum(p["amount"] for p in p_pay_list)
            total_collected += p_total_paid
            
            balance_due = max(0.0, tp.assigned_quota - p_total_paid)
            is_paid = balance_due <= 0.0 and tp.assigned_quota > 0
            jersey_num = tp.jersey_number if tp.jersey_number is not None else (p_obj.jersey_number if p_obj else None)
            
            p_data = {
                "player_id": tp.player_id,
                "name": p_name,
                "nickname": p_nick,
                "jersey_number": jersey_num,
                "status": tp.status,
                "assigned_quota": tp.assigned_quota,
                "has_custom_quota": bool(tp.has_custom_quota),
                "total_paid": p_total_paid,
                "balance_due": round(balance_due, 2),
                "is_paid_off": is_paid,
                "payments": p_pay_list
            }
            
            if tp.status == 'active':
                active_players.append(p_data)
            else:
                inactive_players.append(p_data)

        active_players.sort(key=lambda x: (x["balance_due"] == 0, -x["balance_due"], x["name"]))

        wins = sum(1 for m in all_matches if m.is_win == 1)
        losses = len(all_matches) - wins
        pending_total = max(0.0, tourn.total_cost - total_collected)
        pct_collected = round((total_collected / tourn.total_cost * 100), 1) if tourn.total_cost > 0 else 100.0

        return {
            "tournament": {
                "id": tourn.id,
                "name": tourn.name,
                "team_name": tourn.team_name,
                "total_cost": tourn.total_cost,
                "registration_fee": tourn.registration_fee,
                "referee_fee_total": tourn.referee_fee_total,
                "status": tourn.status,
                "playoff_seed": tourn.playoff_seed,
                "final_result": tourn.final_result,
                "created_at": tourn.created_at.strftime("%Y-%m-%d %H:%M:%S")
            },
            "financials": {
                "total_cost": tourn.total_cost,
                "total_collected": total_collected,
                "total_pending": pending_total,
                "percentage_collected": pct_collected
            },
            "record": {
                "wins": wins,
                "losses": losses,
                "total_matches": len(all_matches),
                "formatted": f"{wins}G - {losses}P"
            },
            "active_players": active_players,
            "inactive_players": inactive_players,
            "matches": [
                {
                    "id": m.id,
                    "opponent": m.opponent,
                    "team_score": m.team_score,
                    "opponent_score": m.opponent_score,
                    "is_win": bool(m.is_win),
                    "match_type": m.match_type,
                    "notes": m.notes,
                    "date": m.date.strftime("%Y-%m-%d")
                }
                for m in all_matches
            ]
        }
    finally:
        if close_sess:
            session.close()

def get_player_summary(player_name: str, session = None) -> dict | None:
    """Returns a breakdown of all tournaments, quotas and payments for a single player."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        player = session.query(Player).filter(Player.name.ilike(player_name.strip())).first()
        if not player:
            candidates = find_matching_players(player_name, session=session)
            if candidates:
                player = candidates[0]
            else:
                return None

        roster_entries = session.query(TournamentPlayer).filter(TournamentPlayer.player_id == player.id).all()
        all_tournaments = {t.id: t for t in session.query(Tournament).all()}
        all_payments = session.query(TournamentPayment).filter(TournamentPayment.player_id == player.id).all()
        
        tourn_payments_map = {}
        for p in all_payments:
            tourn_payments_map[p.tournament_id] = tourn_payments_map.get(p.tournament_id, 0.0) + p.amount

        tournaments_data = []
        total_paid_global = 0.0
        total_debt_global = 0.0

        for tp in roster_entries:
            t = all_tournaments.get(tp.tournament_id)
            if not t:
                continue
            paid = tourn_payments_map.get(tp.tournament_id, 0.0)
            total_paid_global += paid
            balance_due = max(0.0, tp.assigned_quota - paid)
            total_debt_global += balance_due

            tournaments_data.append({
                "tournament_id": t.id,
                "tournament_name": t.name,
                "team_name": t.team_name,
                "tournament_status": t.status,
                "player_status": tp.status,
                "jersey_number": tp.jersey_number if tp.jersey_number is not None else player.jersey_number,
                "quota": tp.assigned_quota,
                "paid": paid,
                "balance_due": round(balance_due, 2),
                "is_paid_off": balance_due <= 0.0
            })

        return {
            "player": {
                "id": player.id,
                "name": player.name,
                "nickname": player.nickname,
                "jersey_number": player.jersey_number,
                "phone": player.phone
            },
            "total_paid_global": total_paid_global,
            "total_debt_global": total_debt_global,
            "tournaments": tournaments_data
        }
    finally:
        if close_sess:
            session.close()


if __name__ == '__main__':
    # Test script for the database
    print("Testing DB connection...")
    expense = add_expense(10.50, "Food", "Lunch at cafe", currency="USD")
    print(f"Added expense: {expense}")
    workout = add_workout_log("Running", 30, "medium", "Evening jog", metrics={"distance": 5.0, "pace": "6:00 min/km"})
    print(f"Added workout: {workout}")
    print("Recent workouts:")
    for w in get_workout_logs():
        print(w)

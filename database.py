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
    opponent = Column(String, nullable=False)
    team_score = Column(Integer, nullable=False)
    opponent_score = Column(Integer, nullable=False)
    is_win = Column(Integer, nullable=False)  # 1 win, 0 loss
    match_type = Column(String, default='jornada')  # 'jornada', 'cuartos', 'semifinal', 'final', 'amistoso'
    notes = Column(String, nullable=True)
    date = Column(DateTime, default=get_now_cdmx)

    def __repr__(self):
        return f"<TournamentMatch(id={self.id}, vs='{self.opponent}', score={self.team_score}-{self.opponent_score}, win={self.is_win})>"


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

def add_tournament(name: str, team_name: str = "Mi Equipo", total_cost: float = 0.0, 
                   registration_fee: float = 0.0, referee_fee_total: float = 0.0) -> Tournament:
    """Creates a new basketball tournament or updates/returns existing one."""
    session = get_session()
    try:
        clean_name = name.strip()
        calculated_total = total_cost
        if calculated_total == 0.0 and (registration_fee > 0 or referee_fee_total > 0):
            calculated_total = registration_fee + referee_fee_total

        existing = session.query(Tournament).filter(Tournament.name.ilike(clean_name)).first()
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

def get_tournament(tournament_id_or_name, session = None) -> Tournament | None:
    """Finds a tournament by ID or by fuzzy name match."""
    close_sess = False
    if session is None:
        session = get_session()
        close_sess = True
    try:
        if isinstance(tournament_id_or_name, int) or (isinstance(tournament_id_or_name, str) and tournament_id_or_name.isdigit()):
            t_id = int(tournament_id_or_name)
            return session.query(Tournament).filter(Tournament.id == t_id).first()
            
        name_str = str(tournament_id_or_name).strip()
        t = session.query(Tournament).filter(Tournament.name.ilike(f"%{name_str}%")).order_by(Tournament.created_at.desc()).first()
        return t
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
                    added_count += 1
                else:
                    existing_count += 1
                    
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        return True, f"Se agregaron {added_count} jugador(es) al torneo.", tourn
    finally:
        session.close()


def set_player_jersey_number(player_name: str, jersey_number: int, tournament_id_or_name = None) -> tuple[bool, str]:
    """Assigns or updates a player's jersey number globally and/or in a tournament."""
    session = get_session()
    try:
        player = get_or_create_player(player_name, session=session)
        player.jersey_number = jersey_number
        
        if tournament_id_or_name:
            tourn = get_tournament(tournament_id_or_name, session=session)
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
        player = get_or_create_player(player_name, session=session)
        
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

def drop_player_from_tournament(tournament_id_or_name, player_name: str, reason: str = "lesion") -> tuple[bool, str, float]:
    """Marks a player as injured or dropped out, freezes their quota to their paid amount, and recalculates quotas."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", 0.0
        player = get_or_create_player(player_name, session=session)
        
        tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.player_id == player.id
        ).first()
        
        if not tp:
            return False, f"El jugador {player.name} no está en este torneo.", 0.0
            
        tp.status = 'injured' if 'lesion' in reason.lower() else 'dropped_out'
        tp.notes = reason
        session.commit()
        recalculate_tournament_quotas(tourn.id, session=session)
        
        # Get new quota for active players
        active_tp = session.query(TournamentPlayer).filter(
            TournamentPlayer.tournament_id == tourn.id,
            TournamentPlayer.status == 'active',
            TournamentPlayer.has_custom_quota == 0
        ).first()
        new_quota = active_tp.assigned_quota if active_tp else 0.0
            
        return True, f"Jugador {player.name} dado de baja ({tp.status}).", new_quota
    finally:
        session.close()

def record_tournament_payment(tournament_id_or_name, player_name: str, amount: float, 
                              payment_method: str = "efectivo", notes: str = None, date_str: str = None) -> tuple[bool, str, dict | None]:
    """Records a payment from a player for a tournament."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None
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

def record_tournament_match(tournament_id_or_name, opponent: str, team_score: int, opponent_score: int, 
                            match_type: str = "jornada", notes: str = None, date_str: str = None) -> tuple[bool, str, dict | None]:
    """Records a game/match result for a tournament."""
    session = get_session()
    try:
        tourn = get_tournament(tournament_id_or_name, session=session)
        if not tourn:
            return False, "Torneo no encontrado.", None

        dt = get_now_cdmx()
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass

        is_win = 1 if team_score > opponent_score else 0
        match = TournamentMatch(
            tournament_id=tourn.id,
            opponent=opponent.strip(),
            team_score=team_score,
            opponent_score=opponent_score,
            is_win=is_win,
            match_type=match_type,
            notes=notes,
            date=dt
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        
        all_matches = session.query(TournamentMatch).filter(TournamentMatch.tournament_id == tourn.id).all()
        wins = sum(1 for m in all_matches if m.is_win == 1)
        losses = len(all_matches) - wins
        
        match_data = {
            "match_id": match.id,
            "tournament_name": tourn.name,
            "opponent": match.opponent,
            "score": f"{team_score} - {opponent_score}",
            "is_win": bool(is_win),
            "match_type": match_type,
            "record": f"{wins}G - {losses}P"
        }
        return True, "Partido registrado exitosamente.", match_data
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

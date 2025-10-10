"""SQLAlchemy database models for storing Statcast pitch data"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class StatcastPitch(Base):
    """Model for storing individual pitch data from Statcast"""

    __tablename__ = "statcast_pitches"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Game identification
    game_pk = Column(Integer, nullable=False, index=True)
    game_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD

    # Player information
    pitcher = Column(Integer, nullable=False, index=True)  # Player ID
    player_name = Column(String(100), nullable=False)
    batter = Column(Integer, nullable=False)

    # Team information
    home_team = Column(String(3), nullable=False)
    away_team = Column(String(3), nullable=False)
    inning_topbot = Column(String(3), nullable=False)
    inning = Column(Integer, nullable=False)

    # Pitch details
    pitch_type = Column(String(5), nullable=True)
    pitch_type_simplified = Column(String(20), nullable=True)
    pitch_name = Column(String(50), nullable=True)
    release_speed = Column(Float, nullable=True)
    release_spin_rate = Column(Integer, nullable=True)

    # Pitch location
    plate_x = Column(Float, nullable=True)
    plate_z = Column(Float, nullable=True)

    # Count
    balls = Column(Integer, nullable=True)
    strikes = Column(Integer, nullable=True)
    outs_when_up = Column(Integer, nullable=True)

    # Pitch number in game
    pitch_number = Column(Integer, nullable=False)
    at_bat_number = Column(Integer, nullable=False)

    # Result
    events = Column(String(50), nullable=True)
    description = Column(String(50), nullable=True)
    type = Column(String(1), nullable=True)  # B, S, X (ball, strike, in play)

    # Score
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Composite unique constraint: one pitch per game+pitcher+pitch_number
    __table_args__ = (
        UniqueConstraint('game_pk', 'pitcher', 'pitch_number', name='uix_game_pitcher_pitch'),
        Index('ix_pitcher_date', 'pitcher', 'game_date'),
    )

    def __repr__(self):
        return f"<StatcastPitch(game_pk={self.game_pk}, pitcher={self.pitcher}, pitch_number={self.pitch_number}, type={self.pitch_type})>"


class PitcherGameCache(Base):
    """Model for tracking which pitcher games have been fully cached"""

    __tablename__ = "pitcher_game_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pitcher_id = Column(Integer, nullable=False, index=True)
    game_date = Column(String(10), nullable=False, index=True)
    game_pk = Column(Integer, nullable=False)
    total_pitches = Column(Integer, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('pitcher_id', 'game_date', name='uix_pitcher_game'),
    )

    def __repr__(self):
        return f"<PitcherGameCache(pitcher_id={self.pitcher_id}, game_date={self.game_date}, pitches={self.total_pitches})>"

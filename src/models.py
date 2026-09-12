from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---------- Справочники ----------

class User(Base):
    __tablename__ = "users"

    # Это обезличенный идентификатор пользователя в sales layer / stitching layer.
    # Telegram user_id и student_id не смешиваются автоматически.
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    source: Mapped[str | None] = mapped_column(String(64))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Channel(Base):
    __tablename__ = "channels"

    channel_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    type: Mapped[str] = mapped_column(String(32))
    url: Mapped[str | None] = mapped_column(String(512))


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("channels.channel_id"))
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime)
    goal: Mapped[str | None] = mapped_column(String(255))


class Placement(Base):
    __tablename__ = "placements"

    placement_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.campaign_id"))
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("channels.channel_id"))
    publication_time: Mapped[datetime | None] = mapped_column(DateTime)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    url: Mapped[str | None] = mapped_column(String(512))


class Creative(Base):
    __tablename__ = "creatives"

    creative_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    placement_id: Mapped[str | None] = mapped_column(ForeignKey("placements.placement_id"))
    type: Mapped[str | None] = mapped_column(String(64))
    text: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(512))


class Course(Base):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)


# ---------- Факты ----------

class Order(Base):
    __tablename__ = "orders"

    # Canonical sales-layer order_id, e.g. ord_<sha256-prefix>.
    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.order_id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.course_id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    event_type: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str | None] = mapped_column(String(64))
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("channels.channel_id"))
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.campaign_id"))
    placement_id: Mapped[str | None] = mapped_column(ForeignKey("placements.placement_id"))
    creative_id: Mapped[str | None] = mapped_column(ForeignKey("creatives.creative_id"))
    meta: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('click', 'bot_start', 'lead', "
            "'conversation_started', 'post_view', 'bot_command')",
            name="ck_event_type",
        ),
        Index("idx_events_user", "user_id"),
        Index("idx_events_ts", "timestamp"),
        Index("idx_events_campaign", "campaign_id"),
    )

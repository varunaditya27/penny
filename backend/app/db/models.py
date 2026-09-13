from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class UserDB(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)
    home_currency = Column(String(8), nullable=False)
    current_available_balance = Column(Float, nullable=False)
    minimum_balance_to_keep = Column(Float, nullable=False)
    financial_priorities = Column(Text, default="")
    expense_categories_to_protect = Column(Text, default="")
    expense_categories_to_reduce = Column(Text, default="")
    expense_categories_to_stop = Column(Text, default="")
    payment_methods_user_will_consider = Column(Text, default="")
    max_installment_months = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    events = relationship("FinancialEventDB", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("DecisionRecordDB", back_populates="user", cascade="all, delete-orphan")


class FinancialEventDB(Base):
    __tablename__ = "financial_events"

    event_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    direction = Column(String(16), nullable=False)
    amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False)
    event_date = Column(String(16), nullable=False)
    settlement_date = Column(String(16), nullable=True)
    status = Column(String(32), nullable=False)
    linked_event_id = Column(String(64), nullable=True)
    flexibility = Column(String(32), default="fixed")
    minimum_allowed_amount = Column(Float, nullable=True)

    user = relationship("UserDB", back_populates="events")


class PaymentOptionDB(Base):
    __tablename__ = "payment_options"

    payment_option_id = Column(String(64), primary_key=True, index=True)
    request_id = Column(String(64), index=True, nullable=False)
    payment_method = Column(String(32), nullable=False)
    payment_amount = Column(Float, nullable=False)
    number_of_payments = Column(Integer, nullable=False)
    first_payment_date = Column(String(16), nullable=False)
    payment_frequency_days = Column(Integer, nullable=False)
    financing_fee = Column(Float, default=0.0)
    total_payable_amount = Column(Float, nullable=False)


class DecisionRecordDB(Base):
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    amount_safe_to_pay = Column(Float, nullable=False)
    affordability_status = Column(String(32), nullable=False)
    recommended_payment_method = Column(String(32), nullable=False)
    payment_plan = Column(Text, nullable=False)
    earliest_date_for_full_payment = Column(String(16), nullable=True)
    spending_changes_needed = Column(Text, nullable=False)
    decision_explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserDB", back_populates="decisions")

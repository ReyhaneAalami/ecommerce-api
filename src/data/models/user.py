
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="customer",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    vendor: Mapped["Vendor | None"] = relationship(
        back_populates="user",
        uselist=False,
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer",
    )

    cart: Mapped["Cart | None"] = relationship(
        back_populates="customer",
        uselist=False,
        cascade="all, delete-orphan",
    )

    wallet: Mapped["Wallet | None"] = relationship(
        back_populates="user",
        uselist=False,
    )

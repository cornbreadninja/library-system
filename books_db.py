from datetime import datetime
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


# Base class
class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    year_of_publication: Mapped[int] = mapped_column(Integer, nullable=True)
    genre: Mapped[str] = mapped_column(String(100), nullable=True)
    barcode_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Relationship to checkout history
    checkout_events = relationship(
        "CheckoutEvent",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="CheckoutEvent.timestamp"
    )

    def __repr__(self):
        return f"<Book(title={self.title}, author={self.author})>"


class CheckoutEvent(Base):
    __tablename__ = "checkout_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)

    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # event_type should be: "checkout" or "checkin"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    book = relationship("Book", back_populates="checkout_events")

    def __repr__(self):
        return f"<CheckoutEvent(book_id={self.book_id}, type={self.event_type}, time={self.timestamp})>"


# Database setup
engine = create_engine("sqlite:///books.db", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

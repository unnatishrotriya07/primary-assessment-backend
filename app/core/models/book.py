from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    class_ = Column("class", String, nullable=False)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    language = Column(String, default="English", nullable=False)
    edition = Column(String, default="2026-27", nullable=False)
    source = Column(String, default="NCERT", nullable=False)

    chapters = relationship("BookChapter", back_populates="book", cascade="all, delete-orphan")


class BookChapter(Base):
    __tablename__ = "book_chapters"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    summary = Column(String, nullable=True)

    book = relationship("Book", back_populates="chapters")
    sections = relationship("ChapterSection", back_populates="chapter", cascade="all, delete-orphan")
    tenant_chapters = relationship("Chapter", back_populates="book_chapter")


class ChapterSection(Base):
    __tablename__ = "chapter_sections"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("book_chapters.id", ondelete="CASCADE"), nullable=False)
    heading = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    html_content = Column(String, nullable=False)
    plain_text = Column(String, nullable=False)

    chapter = relationship("BookChapter", back_populates="sections")
    assets = relationship("ChapterAsset", back_populates="section", cascade="all, delete-orphan")


class ChapterAsset(Base):
    __tablename__ = "chapter_assets"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("chapter_sections.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, nullable=False)
    image = Column(String, nullable=False)
    caption = Column(String, nullable=True)

    section = relationship("ChapterSection", back_populates="assets")

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)  # nested comments
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    author = relationship("User", back_populates="comments")
    post = relationship(
        "Post",
        foreign_keys=[post_id],
        back_populates="all_comments",
        overlaps="comments",
    )
    replies = relationship(
        "Comment",
        back_populates="parent",
        foreign_keys=[parent_id],
        primaryjoin="Comment.parent_id == Comment.id",
        lazy="selectin",
    )
    parent = relationship(
        "Comment",
        back_populates="replies",
        remote_side="Comment.id",
        foreign_keys=[parent_id],
        primaryjoin="Comment.parent_id == Comment.id",
    )

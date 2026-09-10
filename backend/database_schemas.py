from extensions import db
import boto3
import os
from dotenv import load_dotenv
from botocore.client import Config
from pgvector.sqlalchemy import Vector
from threading import Lock

load_dotenv()

FILEBASE_ENDPOINT = "https://s3.filebase.com"

_s3_client = None
_s3_lock = Lock()


def get_s3_client():
    """One shared client. Building one per book made a 50-book listing build 50."""
    global _s3_client
    with _s3_lock:
        if _s3_client is None:
            _s3_client = boto3.client(
                "s3",
                endpoint_url=FILEBASE_ENDPOINT,
                aws_access_key_id=os.getenv("FILEBASE_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("FILEBASE_SECRET_KEY"),
                config=Config(signature_version="s3v4"),
            )
    return _s3_client
# ============================
# Association Tables
# ============================

authors_to_books = db.Table(
    "authors_to_books",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("author_id", db.Integer, db.ForeignKey("authors.id")),
    db.Column("book_id", db.Integer, db.ForeignKey("books.id")),
)

genre_to_books = db.Table(
    "genre_to_books",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id")),
    db.Column("book_id", db.Integer, db.ForeignKey("books.id")),
)

# ============================
# User Model
# ============================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    netid = db.Column(db.String(64), unique=True, nullable=False)
    reputation = db.Column(db.Integer, default=0)
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    bio = db.Column(db.String(), default="")
    embedding = db.Column(Vector(384))

    reviews = db.relationship("Review", back_populates="user")

    following = db.relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )

    followers = db.relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        back_populates="followee",
        cascade="all, delete-orphan"
    )

    # convert to dict for simple api calls
    def to_dict(self):
        return {
            "id": self.id,
            "netid": self.netid,
            "bio": self.bio,
            "reputation": self.reputation,
            "followers": self.followers_count,
            "following": self.following_count
        }
    
    def get_netid(self):
        return self.netid

# ============================
# Author Model
# ============================

class Author(db.Model):
    __tablename__ = "authors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    books = db.relationship(
        "Books",
        secondary=authors_to_books,
        back_populates="authors"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }

# ============================
# Genre Model
# ============================

class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(100), nullable=False, unique=True)

    books = db.relationship(
        "Books",
        secondary=genre_to_books,
        back_populates="genres"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "genre": self.genre
        }

# ============================
# Book Model
# ============================

class Books(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date_published = db.Column(db.String(50))
    blurb = db.Column(db.Text)

    embedding = db.Column(Vector(384)) #embedding = db.Column(db.ARRAY(db.Float))

    length = db.Column(db.Integer)
    cover_url = db.Column(db.String)  # Firebase URL
    link = db.Column(db.String)       # Amazon or external link

    average_rating = db.Column(db.Float, default=0)
    num_ratings = db.Column(db.Integer, default=0)
    num_reviews = db.Column(db.Integer, default=0)

    authors = db.relationship(
        "Author",
        secondary=authors_to_books,
        back_populates="books"
    )

    genres = db.relationship(
        "Genre",
        secondary=genre_to_books,
        back_populates="books"
    )

    reviews = db.relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan"
    )

    def generate_presigned_url(self, object_name, bucket_name = "yalebookcovers", expires_in=3600):
        # A book with no cover, or missing Filebase credentials, must not take
        # down every endpoint that lists books.
        if not object_name:
            return None
        try:
            return get_s3_client().generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expires_in,
            )
        except Exception:
            return None

    # convert to dict for simple api calls
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "date_published": self.date_published,
            "blurb": self.blurb,
            "length": self.length,
            "cover_url": self.generate_presigned_url(self.cover_url), 
            "link": self.link,
            "average_rating": self.average_rating,
            "num_ratings": self.num_ratings,
            "num_reviews": self.num_reviews,
        }

    # abridged version of book dict for person page
    def review_to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "cover_url": self.generate_presigned_url(self.cover_url)
        }

# ============================
# Review Model
# ============================

class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),   # sets timestamp on INSERT
        onupdate=db.func.now()          # updates timestamp on UPDATE
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))

    user = db.relationship("User", back_populates="reviews")
    book = db.relationship("Books", back_populates="reviews")

    # convert to dict for simple api calls
    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "review": self.review,
            "user_id": self.user_id,
            "user_netid": self.user.get_netid(),
            "updated_at": self.updated_at.isoformat(), # convert to string
            "book": self.book.review_to_dict()
        }

# ============================
# Follow Model (User → User)
# ============================

class Follow(db.Model):
    __tablename__ = "follows"

    id = db.Column(db.Integer, primary_key=True)

    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    followee_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    follower = db.relationship(
        "User",
        foreign_keys=[follower_id],
        back_populates="following"
    )

    followee = db.relationship(
        "User",
        foreign_keys=[followee_id],
        back_populates="followers"
    )

# ============================
# Wishlist Model
# ============================

class Wishlist(db.Model):
    __tablename__ = "wishlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))

    __table_args__ = (db.UniqueConstraint("user_id", "book_id"),)

    def to_dict(self):
        # book_id is an Integer column, not a Books instance
        book = db.session.get(Books, self.book_id)
        return {
            "book": book.to_dict() if book else None
        }

# ============================
# Already Read Model
# ============================

class AlreadyRead(db.Model):
    __tablename__ = "already_read"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))

    __table_args__ = (db.UniqueConstraint("user_id", "book_id"),)

    def to_dict(self):
        # book_id is an Integer column, not a Books instance
        book = db.session.get(Books, self.book_id)
        return {
            "book": book.to_dict() if book else None
        }



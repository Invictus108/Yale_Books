from flask import Flask, redirect, request, session, send_from_directory
import requests
import xmltodict
import os
import re
from urllib.parse import urlencode
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db
from dotenv import load_dotenv
from embeddings import get_model
import uuid
import boto3
import mimetypes
from sqlalchemy import func, desc, case, text
import numpy as np



load_dotenv()



# The frontend build is served by this same Flask app, so the browser talks to one
# origin and there is no cross-site cookie or CORS problem to solve. Redirects below
# are relative ("/") on purpose - nothing here can silently point at a dev host.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)

def _frontend_dist_candidates():
    """Where the built frontend might live, most explicit first.

    The layout differs by how the image is built: a repo-root Docker build puts
    the backend in /app/backend and the build in /app/frontend/dist, while a
    build with base directory 'backend' drops app.py at /app/app.py and has no
    frontend at all. Checking a few places beats failing on one guess.
    """
    explicit = (os.getenv("FRONTEND_DIST") or "").strip()
    if explicit:
        return [explicit]
    return [
        os.path.join(_REPO_ROOT, "frontend", "dist"),   # repo checkout / root Docker build
        os.path.join(_BACKEND_DIR, "frontend", "dist"), # frontend copied beside the backend
        os.path.join(_BACKEND_DIR, "static"),           # build copied into backend/static
        os.path.join(os.getcwd(), "frontend", "dist"),
    ]

FRONTEND_DIST_CANDIDATES = _frontend_dist_candidates()
FRONTEND_DIST = next(
    (d for d in FRONTEND_DIST_CANDIDATES if os.path.isfile(os.path.join(d, "index.html"))),
    FRONTEND_DIST_CANDIDATES[0],
)

# Public origin of this service. Used for the CAS service URL and to decide whether
# the session cookie can be marked Secure.
def _public_origin():
    # ORIGIN wins; otherwise take whatever the platform injects. Coolify sets
    # COOLIFY_URL / COOLIFY_FQDN (FQDN may arrive without a scheme).
    for key in ("ORIGIN", "COOLIFY_URL", "COOLIFY_FQDN", "RENDER_EXTERNAL_URL"):
        value = (os.getenv(key) or "").strip()
        if value:
            if not value.startswith(("http://", "https://")):
                value = "https://" + value
            return value.rstrip("/")
    return "http://localhost:5000"

PUBLIC_ORIGIN = _public_origin()

# Only needed if a frontend is still hosted somewhere else (e.g. during a migration
# off Firebase). Same-origin deployments can leave this unset. Comma-separated.
_extra_origins = os.getenv("FRONTEND_URL", "")
ALLOWED_ORIGINS = [u.strip().rstrip("/") for u in _extra_origins.split(",") if u.strip()]

# demo login mode - when true CAS is bypassed and users log in with just a NetID.
# keep this false in production so the normal CAS flow is used.
DEMO_LOGIN = os.getenv("DEMO_LOGIN", "false").strip().lower() in ("1", "true", "yes", "on")

# init all api keys and connect database
def create_app():
    app = Flask(__name__, static_folder=None)
    # Behind Coolify's reverse proxy TLS is terminated upstream, so honour
    # X-Forwarded-* instead of trusting the container's own http scheme.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.secret_key = os.getenv("SESSION_SECRET") # for signing cookies
    if not app.secret_key:
        raise RuntimeError("SESSION_SECRET must be set")
    # First-party cookie now that the app and API share an origin: Lax is enough,
    # and it is not subject to third-party cookie blocking the way SameSite=None is.
    app.config.update(
        SESSION_COOKIE_SECURE=PUBLIC_ORIGIN.startswith("https://"),
        SESSION_COOKIE_SAMESITE="Lax",
    )

    # Same-origin requests need no CORS at all; this only covers a separately
    # hosted frontend, and is a no-op when FRONTEND_URL is unset.
    if ALLOWED_ORIGINS:
        CORS(app,
            supports_credentials=True,
            origins=ALLOWED_ORIGINS,
            methods=["GET", "POST"]
        )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set to a PostgreSQL connection URL")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    

    import database_schemas

    with app.app_context():
        if db.engine.dialect.name == "postgresql":
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.session.commit()
        db.create_all()
    
    return app

app = create_app()

# import models
from database_schemas import (
    User,
    Books,
    Author,
    Genre,
    Review,
    Follow,
    Wishlist,
    AlreadyRead,
    authors_to_books,
    genre_to_books
)

# validation urls
CAS_LOGIN_URL = "https://secure-tst.its.yale.edu/cas/login" # remove -tst fot production
CAS_VALIDATE_URL = "https://secure-tst.its.yale.edu/cas/p3/serviceValidate"

# callback URL 
SERVICE_URL = PUBLIC_ORIGIN + "/login_callback"

# helpers
def parse_cas_response(xml_text: str):
    return xmltodict.parse(xml_text, dict_constructor=dict)

# make sure they are actaully logged in
def validate_ticket(ticket: str) -> str:
    # make sure user actaully logged in
    params = {
        "ticket": ticket,
        "service": SERVICE_URL,
    }

    resp = requests.get(CAS_VALIDATE_URL, params=params)
    data = parse_cas_response(resp.text)

    sr = data.get("cas:serviceResponse", {})

    # authentication failed
    if "authenticationFailure" in sr:
        reason = sr["authenticationFailure"].get("@code", "UNKNOWN")
        raise Exception(f"CAS Authentication failed: {reason}")

    # authentication success
    success = sr.get("cas:authenticationSuccess")
    if not success:
        raise Exception("CAS returned no authenticationSuccess node")

    # return netID
    netid = success["cas:user"]

    return netid

# make sure user is in database
def add_new_user(netid: str):
    user = User.query.filter_by(netid=netid).first()

    if user:
        return  # Already in database
    
    # if not found create new user
    new_user = User(
        netid=netid,
        reputation=0, 
        embedding=np.zeros(384)
    )
    
    db.session.add(new_user)
    db.session.commit()


def cosine_distance(column, vector):
    return column.op("<=>")(vector)

# identity route to check if user is logged in
@app.route("/healthz")
def health():
    db.session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.route("/api/me")
def me():
    if "netid" in session:
        return {"netid": session["netid"]}
    return {"netid": None}

@app.route("/api/whoami")
def whoami():
    user_netid = request.args.get("user")
    user_id = User.query.filter_by(netid=user_netid).first().id
    return {"id": user_id}

# lets the frontend know which login screen to show
@app.route("/api/auth_mode")
def auth_mode():
    return {"demo": DEMO_LOGIN}

# backup login for when CAS is down - NetID only, no password, demo use only
@app.route("/demo_login", methods=["GET", "POST"])
def demo_login():
    if not DEMO_LOGIN:
        return {"error": "Demo login is disabled"}, 404

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        netid = data.get("netid") or ""
    else:
        netid = request.args.get("netid") or ""

    netid = netid.strip().lower()

    if not netid:
        return {"error": "NetID is required"}, 400
    if not re.fullmatch(r"[a-z0-9]{2,20}", netid):
        return {"error": "That does not look like a NetID (letters and numbers only)"}, 400

    add_new_user(netid)

    # Store NetID in session, exactly like the CAS callback does
    session["netid"] = netid

    if request.method == "GET":
        return redirect("/")
    return {"netid": netid}

# redirect to login
@app.route("/login")
def login():
    params = {
        "service": SERVICE_URL
    }
    cas_url = f"{CAS_LOGIN_URL}?{urlencode(params)}"
    return redirect(cas_url)

# callback
@app.route("/login_callback")
def login_callback():
    # get ticket
    ticket = request.args.get("ticket")
    if not ticket:
        return "Missing CAS ticket", 400

    # Validate with CAS server → get NetID
    netid = validate_ticket(ticket)

    add_new_user(netid)

    # Store NetID in session
    session["netid"] = netid

    return redirect("/")

# Serve the built React app. The explicit rules above (/api/*, /login, /logout,
# /login_callback, /demo_login, /healthz) still win because Werkzeug ranks static
# rules above the <path:> converter, so this only catches frontend routes.
@app.route("/")
@app.route("/<path:path>")
def serve_frontend(path=""):
    index = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.isfile(index):
        return {
            "error": "Frontend build not found",
            "checked": FRONTEND_DIST_CANDIDATES,
            "app_file": os.path.abspath(__file__),
            "cwd": os.getcwd(),
            "hint": (
                "The image has no built frontend. Build from the REPO ROOT (not "
                "backend/) so the Dockerfile's node stage can run, or set "
                "FRONTEND_DIST to where index.html actually is."
            ),
        }, 503

    # a real file (assets, vite.svg, ...) -> serve it; anything else -> SPA entry point
    if path and os.path.isfile(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")

# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/get_person")
def get_person():
    key = int(request.args.get("key"))

    user = User.query.filter_by(id=key).first()

    return {
        "user": user.to_dict()
    }

@app.route("/api/get_user_reviews")
def get_user_ratings():
    user_id = int(request.args.get("key"))

    reviews = Review.query.filter_by(user_id=user_id).order_by(Review.updated_at.desc()).all()

    return {
        "reviews": [r.to_dict() for r in reviews]
    }

# upload to filebase
def upload_to_filebase(fileobj, bucket_name="yalebookcovers"):
    """
    Uploads a file-like object received from Flask (request.files["cover_image"])
    to a Filebase bucket using a UUID filename.

    Returns:
        (object_name, content_type)
    """

    FILEBASE_ENDPOINT = "https://s3.filebase.com"

    # Preserve extension for correct MIME type
    original_filename = fileobj.filename
    ext = os.path.splitext(original_filename)[1]

    # UUID-based object key
    object_name = f"{uuid.uuid4()}{ext}"

    # Guess MIME type
    content_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

    # Create S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=FILEBASE_ENDPOINT,
        aws_access_key_id=os.getenv("FILEBASE_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("FILEBASE_SECRET_KEY"),
    )

    # Upload from in-memory fileobj
    s3.upload_fileobj(
        Fileobj=fileobj,
        Bucket=bucket_name,
        Key=object_name,
        ExtraArgs={"ContentType": content_type},
    )

    return object_name


@app.route("/api/add_book" , methods=["POST"])
def add_book():
    # get data
    title = request.form.get("title")
    date_published = request.form.get("date_published")
    blurb = request.form.get("blurb")
    length = request.form.get("length")
    link = request.form.get("link")
    authors_raw = request.form.get("authors")
    genres_raw = request.form.get("genres")

    # Basic validation (all required)
    if not all([title, date_published, blurb, length, link, authors_raw, genres_raw]):
        return {"error": "Missing required fields"}, 400

    # make sure books isnt already in database
    book = Books.query.filter_by(title=title).first()
    if book:
        return {"error": "Book already exists"}, 400

    authors_list = [a.strip() for a in authors_raw.split(",") if a.strip()]
    genres_list = [g.strip() for g in genres_raw.split(",") if g.strip()]

    file = request.files.get("cover_image")
    if not file:
        return {"error": "Cover image is required"}, 400

    cover_url = upload_to_filebase(file)
    
    # get embedding vector
    embedding = get_model().encode(blurb).astype(float).tolist()

    # add book to database
    book = Books(
        title=title,
        date_published=date_published,
        blurb=blurb,
        embedding=embedding,
        length=int(length),
        link=link,
        cover_url=cover_url,
    )

    db.session.add(book)
    db.session.commit()  # commit so book.id exists

    # authors
    for name in authors_list:
        author = Author.query.filter_by(name=name).first()
        if not author:
            author = Author(name=name)
            db.session.add(author)
            db.session.commit()
        book.authors.append(author)

    # genres
    for name in genres_list:
        name = name.lower()
        genre = Genre.query.filter_by(genre=name).first()
        if not genre:
            genre = Genre(genre=name)
            db.session.add(genre)
            db.session.commit()
        book.genres.append(genre)
    
    # increment user reputation by 10
    user = request.form.get("netid")
    user = User.query.filter_by(netid=user).first()
    user.reputation += 10

    db.session.commit()

    return {"success": True, "book_id": book.id}

@app.route("/api/get_book")
def get_book():
    key = int(request.args.get("key"))

    book = Books.query.filter_by(id=key).first()

    return {
        "book": book.to_dict()
    }

@app.route("/api/get_book_reviews")
def get_book_reviews():
    book_id = int(request.args.get("key"))

    reviews = Review.query.filter_by(book_id=book_id).order_by(Review.updated_at.desc()).all()

    return {
        "reviews": [r.to_dict() for r in reviews]
    }

@app.route("/api/get_authors")
def get_authors():
    book = int(request.args.get("key"))

    authors = Author.query.filter(Author.books.any(id=book)).all()
   
    return {
        "authors": [a.to_dict() for a in authors]
    }

@app.route("/api/get_genres")
def get_genres():
    book = int(request.args.get("key"))

    genres = Genre.query.filter(Genre.books.any(id=book)).all()

    return {
        "genres": [g.to_dict() for g in genres]
    }

@app.route("/api/is_friend")
def is_friend():
    user1 = int(request.args.get("user1"))
    user2_netid = request.args.get("user2")

    print(user1, user2_netid)

    # get user2 id
    user2 = User.query.filter_by(netid=user2_netid).first().id

    return {
        "is_friend": Follow.query.filter_by(follower_id=user2, followee_id=user1).first() is not None
    }

@app.route("/api/follow", methods=["POST"])
def follow():
    data = request.json
    user1 = int(data.get("followee"))
    user2_netid = data.get("follower")

    # get user2 id
    user2 = User.query.filter_by(netid=user2_netid).first().id

    # increments follower and followee count
    User.query.filter_by(id=user1).update({User.followers_count: User.followers_count + 1})
    User.query.filter_by(id=user2).update({User.following_count: User.following_count + 1})

    follow = Follow(follower_id=user2, followee_id=user1)
    db.session.add(follow)
    db.session.commit()

    return {"success": True}

@app.route("/api/unfollow", methods=["POST"])
def unfollow():    
    data = request.json
    user1 = int(data.get("followee"))
    user2_netid = data.get("follower")

    # get user2 id
    user2 = User.query.filter_by(netid=user2_netid).first().id

    # decrement follower count
    User.query.filter_by(id=user1).update({User.followers_count: User.followers_count - 1})
    User.query.filter_by(id=user2).update({User.following_count: User.following_count - 1})

    follow = Follow.query.filter_by(follower_id=user2, followee_id=user1).first()
    db.session.delete(follow)
    db.session.commit()

    return {"success": True}

@app.route("/api/get_followers")
def get_followers():
    user = request.args.get("key")

    user = User.query.filter_by(netid=user).first().id

    followers = Follow.query.filter_by(followee_id=user).all()

    return {
        "followers": [f.to_dict() for f in followers]
    }

@app.route("/api/get_following")
def get_following():
    user = request.args.get("key")

    user = User.query.filter_by(netid=user).first().id

    following = Follow.query.filter_by(follower_id=user).all()

    return {
        "following": [f.to_dict() for f in following]
    }

@app.route("/api/check_if_read")
def check_if_read():
    user = request.args.get("user")
    book = int(request.args.get("book"))

    print(user)

    user = User.query.filter_by(netid=user).first().id

    exists = AlreadyRead.query.filter_by(user_id=user, book_id=book).first() is not None

    return {
        "exists": exists
    }

@app.route("/api/add_to_read", methods=["POST"])
def add_to_read():
    data = request.json
    user = data.get("user")
    book = int(data.get("book"))
    

    user = User.query.filter_by(netid=user).first().id

    already_read = AlreadyRead(user_id=user, book_id=book)
    db.session.add(already_read)
    db.session.commit()

    return {"success": True}

@app.route("/api/remove_from_read", methods=["POST"])
def remove_from_read():
    data = request.json
    user = data.get("user")
    book = int(data.get("book"))

    user = User.query.filter_by(netid=user).first().id

    already_read = AlreadyRead.query.filter_by(user_id=user, book_id=book).first()
    db.session.delete(already_read)
    db.session.commit()

    return {"success": True}

@app.route("/api/check_if_wishlist")
def check_if_wishlist():
    user = request.args.get("user")
    book = int(request.args.get("book"))

    user = User.query.filter_by(netid=user).first().id

    exists = Wishlist.query.filter_by(user_id=user, book_id=book).first() is not None

    return {
        "exists": exists
    }

@app.route("/api/add_to_wishlist", methods=["POST"])
def add_to_wishlist():
    data = request.json
    user = data.get("user")
    book = int(data.get("book"))
    

    user = User.query.filter_by(netid=user).first().id

    already_read = Wishlist(user_id=user, book_id=book)
    db.session.add(already_read)
    db.session.commit()

    return {"success": True}

@app.route("/api/remove_from_wishlist", methods=["POST"])
def remove_from_wishlist():
    data = request.json
    user = data.get("user")
    book = int(data.get("book"))

    user = User.query.filter_by(netid=user).first().id

    already_read = Wishlist.query.filter_by(user_id=user, book_id=book).first()
    db.session.delete(already_read)
    db.session.commit()

    return {"success": True}

@app.route("/api/get_wishlist")
def get_wishlist():
    user = request.args.get("key")

    user = User.query.filter_by(netid=user).first().id

    wishlist = Wishlist.query.filter_by(user_id=user).all()

    books = []
    # collect all book info
    for book in wishlist:
        book = Books.query.filter_by(id=book.book_id).first()
        books.append(book.to_dict())

    return {
        "wishlist": books
    }

@app.route("/api/get_already_read")
def get_already_read():
    user = request.args.get("key")

    user = User.query.filter_by(netid=user).first().id

    already_read = AlreadyRead.query.filter_by(user_id=user).all()


    books = []
    # collect all book info
    for book in already_read:
        book = Books.query.filter_by(id=book.book_id).first()
        books.append(book.to_dict())

    return {
        "already_read": books
    }

@app.route("/api/check_already_reviewed")
def check_already_review():
    user_netid = request.args.get("user")
    book = int(request.args.get("book"))

    user_id = User.query.filter_by(netid=user_netid).first().id

    exists = Review.query.filter_by(user_id=user_id, book_id=book).first() is not None

    return {
        "exists": exists
    }

@app.route("/api/add_review", methods=["POST"])
def add_review():
    data = request.json
    user = data.get("user")
    book_id = int(data.get("book"))
    review = data.get("review")
    rating = int(data.get("rating"))

    user_id = User.query.filter_by(netid=user).first().id

    # increment reputation by 5
    user = User.query.filter_by(id=user_id).first()
    user.reputation += 5

    # update average rating and num of ratings and views of books
    book = Books.query.filter_by(id=book_id).first()
    book.average_rating = (book.average_rating * book.num_ratings + rating) / (book.num_ratings + 1)
    book.num_ratings += 1
    book.num_reviews += 1

    # update embedding vector (average of embedding vector most recent 5 review with rating over 4 stars)
    # Get last 5 books they reviewed as embedding anchors
    past_good = (
        db.session.query(Books.embedding)
        .join(Review, Review.book_id == Books.id)
        .filter(Review.user_id == user_id)
        .filter(Review.rating >= 4)
        .order_by(Review.updated_at.desc())
        .limit(4)                          # only take last 4 because we add new one = 5
        .all()
    )

    # Convert row objects → list of vectors
    past_vectors = [row.embedding for row in past_good]

    # Add the current book’s embedding if rating >= 4
    if rating >= 4:
        past_vectors.append(book.embedding)

    # If no good reviews at all, fall back to zero vector
    if len(past_vectors) == 0:
        book_vec = None
    else:
        book_vec = np.mean(np.array(past_vectors), axis=0)
    
    # weighing
    n = len(past_vectors)
    w_books = min(0.1 * n, 0.7)   # grows from 0 → 0.7 as user gets more history
    w_bio = 1 - w_books    

    # get bio vector
    if user.bio is not None:
        bio_vec = get_model().encode(user.bio).astype('float')
    else:
        bio_vec = None

    if bio_vec is None and book_vec is None:
        final_vec = np.zeros(384)
    elif bio_vec is None:
        final_vec = book_vec
    elif book_vec is None:
        final_vec = bio_vec
    else:
        final_vec = w_books * book_vec + w_bio * bio_vec

    # normalize
    final_vec = final_vec / np.linalg.norm(final_vec)   
    
    user.embedding = final_vec.tolist()

    review = Review(user_id=user_id, book_id=book_id, review=review, rating=rating)
    db.session.add(review)
    db.session.commit()

    return {"success": True}

@app.route("/api/update_bio", methods=["POST"])
def update_bio():
    data = request.json
    user = data.get("user")
    bio = data.get("bio")

    user = User.query.filter_by(netid=user).first()
    user_id = user.id
    user.bio = bio

     # update embedding vector (average of embedding vector most recent 5 review with rating over 4 stars)
    # Get last 5 books they reviewed as embedding anchors
    past_good = (
        db.session.query(Books.embedding)
        .join(Review, Review.book_id == Books.id)
        .filter(Review.user_id == user_id)
        .filter(Review.rating >= 4)
        .order_by(Review.updated_at.desc())
        .limit(5)                          # only take last 4 because we add new one = 5
        .all()
    )

    # Convert row objects → list of vectors
    past_vectors = [row.embedding for row in past_good]

    # If no good reviews at all, fall back to zero vector
    if len(past_vectors) == 0:
        book_vec = None
    else:
        book_vec = np.mean(np.array(past_vectors), axis=0)
    
    # weighing
    n = len(past_vectors)
    w_books = min(0.1 * n, 0.7)   # grows from 0 → 0.7 as user gets more history
    w_bio = 1 - w_books    

    # get bio vector
    if bio is not None:
        bio_vec = get_model().encode(bio).astype('float')
    else:
        bio_vec = None

    if bio_vec is None and book_vec is None:
        final_vec = np.zeros(384)
    elif bio_vec is None:
        final_vec = book_vec
    elif book_vec is None:
        final_vec = bio_vec
    else:
        final_vec = w_books * book_vec + w_bio * bio_vec
    
    # normalize
    final_vec = final_vec / np.linalg.norm(final_vec)
    
    user.embedding = final_vec.tolist()
    db.session.commit()

    return {"success": True}

@app.route("/api/delete_review", methods=["POST"])
def delete_review(): 
    data = request.json
    review_id = int(data.get("id"))

    review = Review.query.filter_by(id=review_id).first()

    # fix average rating and rating count for book
    book = Books.query.filter_by(id=review.book_id).first()
    book.average_rating = (book.average_rating * book.num_ratings - review.rating) / (book.num_ratings - 1)
    book.num_ratings -= 1

    db.session.delete(review)
    db.session.commit()

    return {"success": True}

@app.route("/api/get_author_books")
def get_author_books():
    author_name = request.args.get("name")

    print(author_name)

    books = Books.query.filter(Books.authors.any(name=author_name)).all()

    return {
        "books": [book.to_dict() for book in books]
    }

@app.route("/api/get_all_genres")
def get_all_genres():
    genres = Genre.query.all()

    return {
        "genres": [genre.to_dict() for genre in genres]
    }


@app.route("/api/search_people")
def search_people():
    key = request.args.get("search", None)
    following = request.args.get("following", None)
    followers = request.args.get("followers", None)
    user_netid = request.args.get("user", None)

    # transform following and followers into bools
    following = following == "true"
    followers = followers == "true"

    print(f"key: {key}, following: {following}, followers: {followers}, user_netid: {user_netid}")

    # Normalize key
    if key:
        key = key.lower()

    # Base query
    users_query = User.query

    # Load the user whose network we’re filtering
    base_user = None
    if user_netid:
        base_user = User.query.filter_by(netid=user_netid).first()

    # Helper for search
    def apply_search(q):
        if key:
            return q.filter(db.func.lower(User.netid).contains(key))
        return q

    # --------------------------------------
    # CASE 1 — SEARCH KEY PROVIDED
    # --------------------------------------
    if key:
        if following and followers:
            # Mutuals: user must be followed by AND follow base_user
            following_ids = db.session.query(Follow.followee_id).filter(
                Follow.follower_id == base_user.id
            )
            follower_ids = db.session.query(Follow.follower_id).filter(
                Follow.followee_id == base_user.id
            )

            users = (
                users_query
                .filter(User.id.in_(following_ids))
                .filter(User.id.in_(follower_ids))
            )
            users = apply_search(users).order_by(User.reputation.desc()).all()

        elif following:
            # Only people base_user follows
            users = (
                users_query
                .join(Follow, Follow.followee_id == User.id)
                .filter(Follow.follower_id == base_user.id)
            )
            users = apply_search(users).order_by(User.reputation.desc()).all()

        elif followers:
            # Only people who follow base_user
            users = (
                users_query
                .join(Follow, Follow.follower_id == User.id)
                .filter(Follow.followee_id == base_user.id)
            )
            users = apply_search(users).order_by(User.reputation.desc()).all()

        else:
            # Pure global search
            users = (
                users_query
                .filter(db.func.lower(User.netid).contains(key))
                .order_by(User.reputation.desc())
                .all()
            )

    # --------------------------------------
    # CASE 2 — NO SEARCH KEY
    # --------------------------------------
    else:
        if following and followers:
            # Mutuals only
            following_ids = db.session.query(Follow.followee_id).filter(
                Follow.follower_id == base_user.id
            )
            follower_ids = db.session.query(Follow.follower_id).filter(
                Follow.followee_id == base_user.id
            )

            users = (
                users_query
                .filter(User.id.in_(following_ids))
                .filter(User.id.in_(follower_ids))
                .order_by(User.reputation.desc())
                .all()
            )

        elif following:
            # Only people base_user follows
            users = (
                users_query
                .join(Follow, Follow.followee_id == User.id)
                .filter(Follow.follower_id == base_user.id)
                .order_by(User.reputation.desc())
                .all()
            )

        elif followers:
            # Only people who follow base_user
            users = (
                users_query
                .join(Follow, Follow.follower_id == User.id)
                .filter(Follow.followee_id == base_user.id)
                .order_by(User.reputation.desc())
                .all()
            )

        else:
            # No key, no filters → return all users
            users = (
                users_query
                .order_by(User.reputation.desc())
                .all()
            )

    return {
        "users": [u.to_dict() for u in users]
    }

@app.route("/api/search_books")
def search_books():
    book = request.args.get("book", None)
    author = request.args.get("author", None)
    genres = request.args.getlist("genres[]", None)
    following = request.args.get("following", None)
    description = request.args.get("description", None)
    advanced_search = request.args.get("advancedSearch", None)
    user_netid = request.args.get("user", None)
    already_read = request.args.get("alreadyRead", None)
    wishlist = request.args.get("wishlist", None)

    user_id = User.query.filter_by(netid=user_netid).first().id

    print(genres)

    # convert from strings to bools
    following = following == "true"
    advanced_search = advanced_search == "true"
    already_read = already_read == "true"
    wishlist = wishlist == "true"

    # make embedding vector
    description_embeddings = (
        get_model().encode(description).astype(float).tolist()
        if advanced_search and description else None
    )

    query = Books.query

    # title
    if book:
        query = query.filter(Books.title.ilike(f"%{book}%"))

    # author
    if author:
        query = query.join(Books.authors).filter(
            Author.name.ilike(f"%{author}%")
        )

    # genres
    if genres:
        # convert to ints
        genre_ids = [int(g) for g in genres]

        # Join once on the association table
        query = query.join(genre_to_books).filter(
            genre_to_books.c.genre_id.in_(genre_ids)
        ).group_by(Books.id)

        # require that book contains ALL selected genres
        query = query.having(func.count(genre_to_books.c.genre_id) == len(genre_ids))

    
    # following filter
    if following and user_id:
        query = (
            query.join(Books.reviews)
                 .join(Follow, Follow.followee_id == Review.user_id)
                 .filter(Follow.follower_id == user_id)
                 .filter(Review.rating >= 4)
        )

    # exclude wishlist
    if wishlist and user_id:
        query = query.filter(
            ~Books.id.in_(
                db.session.query(Wishlist.book_id).filter_by(user_id=user_id)
            )
        )

    # exclude already read
    if already_read and user_id:
        query = query.filter(
            ~Books.id.in_(
                db.session.query(AlreadyRead.book_id).filter_by(user_id=user_id)
            )
        )

    # advanced search
    if advanced_search and description_embeddings:
        # pgvector similarity search
        query = query.order_by(
            Books.embedding.cosine_distance(description_embeddings)
        )
    else:
        # Default ordering
        query = query.order_by(Books.average_rating.desc())
        # Remove duplicates caused by various JOINs
        query = query.distinct()

    books = query.limit(50).all()
    
    return {
        "books": [b.to_dict() for b in books]
    }

@app.route("/api/get_recommendations")
def get_recommendations():
    limit = 200
    user_netid = request.args.get("user")
    user = User.query.filter_by(netid=user_netid).first()
    user_id = user.id

    if not user_id:
        return {"error": "User not found"}, 404

    excluded_books = set()

    # books they read
    read_ids = db.session.query(AlreadyRead.book_id)\
                         .filter_by(user_id=user_id).all()
    excluded_books.update([b[0] for b in read_ids])

    # books in wishlist
    wishlist_ids = db.session.query(Wishlist.book_id)\
                             .filter_by(user_id=user_id).all()
    excluded_books.update([b[0] for b in wishlist_ids])

    # books they reviewed
    reviewed_ids = db.session.query(Review.book_id)\
                             .filter_by(user_id=user_id).all()
    excluded_books.update([b[0] for b in reviewed_ids])

    # Convert to set
    excluded_books = list(excluded_books)


    # If empty, pass None to NOT break "NOT IN" queries
    if not excluded_books:
        excluded_books = [-1]     # ensures NOT IN never filters everything


    # ======================
    # 2. Build user preference embedding
    # ======================

    # Get last 5 books they reviewed as embedding anchors
    past_good = (
        db.session.query(Books.embedding)
        .join(Review, Review.book_id == Books.id)
        .filter(Review.user_id == user_id)
        .filter(Review.rating >= 4)
        .order_by(Review.updated_at.desc())
        .limit(5)                          # only take last 4 because we add new one = 5
        .all()
    )

    # Convert row objects → list of vectors
    past_vectors = [row[0] for row in past_good]

    # If no good reviews at all, fall back to zero vector
    if len(past_vectors) == 0:
        book_vec = None
    else:
        book_vec = np.mean(np.array(past_vectors), axis=0)
    
    # weighing
    n = len(past_vectors)
    w_books = min(0.1 * n, 0.7)   # grows from 0 → 0.7 as user gets more history
    w_bio = 1 - w_books    

    # get bio vector
    if user.bio != "":
        bio_vec = get_model().encode(user.bio).astype('float')
    else:
        bio_vec = None
    
    if bio_vec is None and book_vec is None:
        user_embedding = None
    elif bio_vec is None:
        user_embedding = w_books * book_vec
    elif book_vec is None:
        user_embedding = w_bio * bio_vec
    else:
        user_embedding = w_books * book_vec + w_bio * bio_vec
    
    if user_embedding is not None:
        user_embedding = user_embedding.tolist()
    



    # ======================
    # 3. Base Query:
    # Only return books user has NOT already touched
    # ======================

    query = Books.query.filter(~Books.id.in_(excluded_books))


    # ======================
    # 4. Boost books liked by followed users
    # ======================

    followed_review_scores = (
        db.session.query(
            Review.book_id.label("book_id"),
            func.avg(Review.rating).label("follow_rating")
        )
        .join(Follow, Follow.followee_id == Review.user_id)
        .filter(Follow.follower_id == user_id)
        .filter(Review.rating >= 4)  # only strong likes
        .group_by(Review.book_id)
        .subquery()
    )

    query = query.outerjoin(
        followed_review_scores,
        followed_review_scores.c.book_id == Books.id
    )


    # ======================
    # 5. Embedding similarity scores
    # ======================
    num_users = User.query.count()

    if user_embedding is not None:
        book_similarity_score = Books.embedding.cosine_distance(user_embedding)

        # only try user matching if there are enough users
        if num_users > 50:
            user_sim_expr = User.embedding.cosine_distance(user_embedding)
        else:
            user_sim_expr = None
    else:
        book_similarity_score = None
        user_sim_expr = None


    # user similarity scores
    if user_sim_expr is not None:
        similar_users = (
            db.session.query(
                User.id,
                user_sim_expr.label("sim")
            )
            .filter(User.id != user_id)          # exclude self
            .order_by(user_sim_expr.asc())       # smaller distance = more similar
            .limit(5) # get 5 most similar users
            .all()
        )

        similar_user_ids = [uid for uid, sim in similar_users]


        similar_user_books = (
            db.session.query(Books.id.label("id"))
            .join(Review, Review.book_id == Books.id)
            .filter(Review.user_id.in_(similar_user_ids))
            .filter(Review.rating >= 4)
            .union(
                db.session.query(AlreadyRead.book_id.label("book_id"))
                .filter(AlreadyRead.user_id.in_(similar_user_ids))
            )
            .subquery()
        )

        similar_user_flag = case(
            (similar_user_books.c.id != None, 1),
            else_=0
        ).label("similar_user_score")

        query = query.outerjoin(
            similar_user_books,
            similar_user_books.c.id == Books.id
        )

        ORDER = []

        # vector similarity to user reading history
        if user_embedding is not None:
            ORDER.append(book_similarity_score.asc())
        
        # similar-user behavior
        ORDER.append(desc(similar_user_flag))

        # followed-user behavior
        ORDER.append(desc(followed_review_scores.c.follow_rating))

        # global popularity ranking
        ORDER.append(desc(Books.average_rating))
        ORDER.append(desc(Books.num_ratings))

        books = query.order_by(*ORDER).limit(limit).all()
    else:
        ORDER = []

        if book_similarity_score is not None:
            ORDER.append(book_similarity_score.asc()) # closer vector → better match

        ORDER.append(desc(followed_review_scores.c.follow_rating))  # liked by followees
        ORDER.append(desc(Books.average_rating))                    # general quality
        ORDER.append(desc(Books.num_ratings))                       # popularity fallback


        books = query.order_by(*ORDER).limit(limit).all()

    return {
        "books": [b.to_dict() for b in books]
    }

# add already read and book list to book page

if __name__ == "__main__":
    app.run(debug=True)

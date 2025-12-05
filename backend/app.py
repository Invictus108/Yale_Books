from flask import Flask, redirect, request, session
import requests
import xmltodict
import os
from urllib.parse import urlencode
from flask_cors import CORS
from extensions import db
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import uuid
import boto3
import mimetypes

load_dotenv()



model = SentenceTransformer('intfloat/e5-small-v2')

# init all api keys and connect database
def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SESSION_SECRET") # for signing cookies
    CORS(app,
        supports_credentials=True,
        origins=["https://yalebooks-be079.web.app/","http://localhost:5173"], # TODO: change to prod
        methods=["GET", "POST"]
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    import database_schemas

    with app.app_context():
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
SERVICE_URL = os.getenv("ORIGIN", "http://localhost:5000") + "/login_callback"

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
        reputation=0
    )
    
    db.session.add(new_user)
    db.session.commit()

# identity route to check if user is logged in
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

    return redirect("http://localhost:5173/") # frontend url

# main index
@app.route("/")
def home():
    if "netid" not in session:
        return redirect("/login")
    return f"Logged in as: {session['netid']}"

# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("http://localhost:5173/")

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
    embedding = model.encode(blurb).astype(float).tolist()

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
    user.bio = bio
    db.session.commit()

    return {"success": True}

@app.route("/api/delete_review", methods=["POST"])
def delete_review(): 
    data = request.json
    review_id = int(data.get("id"))

    review = Review.query.filter_by(id=review_id).first()
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



@app.route("/api/get_recommendations")
def get_recommendations():
    user_netid = request.args.get("user")
    user = User.query.filter_by(netid=user_netid).first()

    if not user:
        return {"error": "User not found"}, 404

    user_id = user.id

    # TODO

    # just return all for now
    books = Books.query.order_by(Books.average_rating.desc()).all()

    return {
        "books": [b.to_dict() for b in books]
    }

@app.route("/api/search_books")
def search_books():
    # TODO: add more advanced features in search
    book = request.args.get("book", None)
    author = request.args.get("author", None)
    genres = request.args.getlist("genres[]", None)
    following = request.args.get("following", None)
    description = request.args.get("description", None)
    advanced_search = request.args.get("advancedSearch", None)

    # conver following and advanced_search to bools
    following = following == "true"
    advanced_search = advanced_search == "true"

    print(f"book: {book}, author: {author}, genres: {genres}, following: {following}, description: {description}, advanced_search: {advanced_search}")

    



    if book:
        books = Books.query.filter(Books.title.contains(book)).order_by(Books.average_rating.desc()).all()

    else:
        books = Books.query.order_by(Books.average_rating.desc()).all()
    
    return {
        "books": [b.to_dict() for b in books]
    }


# add already read and book list to book page

if __name__ == "__main__":
    app.run(debug=True)

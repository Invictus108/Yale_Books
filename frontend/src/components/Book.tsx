import { coverSrc, onCoverError } from '../lib/cover';
import type { AuthorData, BookData, GenreData, ReviewData } from '../types';
import './Book.css'
import { useParams, useNavigate } from "react-router-dom"
import axios from 'axios';
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export default function Book() {
    const navigate = useNavigate()
    const { id } = useParams()

    const [reviews, setReviews] = useState<ReviewData[]>([]);
    const [book, setBook] = useState<Partial<BookData>>({});
    const [authors, setAuthors] = useState<AuthorData[]>([]);
    const [genres, setGenres] = useState<GenreData[]>([]);
    const [alreadyRead, setAlreadyRead] = useState(false);
    const [wishlist, setWishlist] = useState(false);
    const [alreadyReviewed, setAlreadyReviewed] = useState(false);


    useEffect(() => {
        let cancelled = false;
        const netid = sessionStorage.getItem("netid");
        const set = <T,>(fn: (v: T) => void, fallback: T) => (res: any, key: string) => {
            if (!cancelled) fn(res?.data?.[key] ?? fallback);
        };
        const get = (url: string, params: any, key: string, apply: (v: any) => void, fallback: any) =>
            axios.get(url, { params })
                .then((res) => set(apply, fallback)(res, key))
                .catch(() => { if (!cancelled) apply(fallback); });

        get("/api/get_book", {key: id}, "book", setBook, null);
        get("/api/get_book_reviews", {key: id}, "reviews", setReviews, []);
        get("/api/get_authors", {key: id}, "authors", setAuthors, []);
        get("/api/get_genres", {key: id}, "genres", setGenres, []);
        get("/api/check_if_read", {book: id, user: netid}, "exists", setAlreadyRead, false);
        get("/api/check_if_wishlist", {book: id, user: netid}, "exists", setWishlist, false);
        get("/api/check_already_reviewed", {book: id, user: netid}, "exists", setAlreadyReviewed, false);

        return () => { cancelled = true; };
    }, [id]);

    const handleAddAlreadyRead = () => {
        axios
        .post("/api/add_to_read", { user: sessionStorage.getItem("netid"), book: id })
        .then(() => setAlreadyRead(true));
    }

    const handleRemoveAlreadyRead = () => {
        axios
        .post("/api/remove_from_read", { user: sessionStorage.getItem("netid"), book: id })
        .then(() => setAlreadyRead(false));
    };

    const handleAddWishlist = () => {
        axios
        .post("/api/add_to_wishlist", { user: sessionStorage.getItem("netid"), book: id })
        .then(() => setWishlist(true));
    }

    const handleRemoveWishlist = () => {
        axios
        .post("/api/remove_from_wishlist", { user: sessionStorage.getItem("netid"), book: id })
        .then(() => setWishlist(false));
    };



    return (
       <div id="book-page">
    <div className="book-header">
        <button
            onClick={() => navigate(-1)}
            className="back-button"
        >
            ← Back
        </button>
    </div>

    <div className="book-layout">
        {/* LEFT: main content */}
        <div className="book-main">
            <div className="book-title-block">
                <h1 className="book-title">{book.title}</h1>

                <ul className="book-authors">
                    {authors.map((author, idx) => (
                        <li key={idx} className="book-author-item">
                            <Link
                                to={`/author/${author.name}`}
                                className="book-author-link"
                            >
                                {author.name}
                            </Link>
                        </li>
                    ))}
                </ul>

                <ul className="book-genres">
                    {genres.map((genre, idx) => (
                        <li key={idx} className="book-genre-chip">
                            {genre.genre}
                        </li>
                    ))}
                </ul>
            </div>

            <div className="book-meta">
                <p className="book-length">{book.length} pages</p>

                <div className="book-average-rating">
                    {(book.average_rating === 0) ? "no rating" : `⭐ ${book.average_rating}`}
                </div>

                {book.link && (
                    <a
                        href={book.link}
                        target="_blank"
                        rel="noreferrer"
                        className="book-purchase-link"
                    >
                        Purchase book ↗
                    </a>
                )}
            </div>


            <p className="book-blurb">{book.blurb}</p>

            <div className="book-actions">
                <div className="book-actions-row">
                    {alreadyRead ? (
                        <button
                            onClick={handleRemoveAlreadyRead}
                            className="secondary-button"
                        >
                            Mark as Unread
                        </button>
                    ) : (
                        <button
                            onClick={handleAddAlreadyRead}
                            className="primary-button"
                        >
                            Mark as Read
                        </button>
                    )}

                    {wishlist ? (
                        <button
                            onClick={handleRemoveWishlist}
                            className="secondary-button"
                        >
                            Remove from Wishlist
                        </button>
                    ) : (
                        <button
                            onClick={handleAddWishlist}
                            className="primary-button"
                        >
                            Add to Wishlist
                        </button>
                    )}
                </div>

                <div className="book-review-action">
                    {!alreadyReviewed ? (
                        <Link
                            to={`/review/${book.id}`}
                            className="primary-button review-button"
                        >
                            Add a Review
                        </Link>
                    ) : (
                        <p className="already-reviewed-text">
                            You have already reviewed this book
                        </p>
                    )}
                </div>
            </div>
        </div>

        {/* RIGHT: cover card */}
        <aside className="book-side">
            <div className="book-cover-card">
                <img
                    src={coverSrc(book.cover_url)}
                                        onError={onCoverError}
                    alt={`${book.title} cover`}
                    className="book-cover-image"
                />

                {book.cover_url && (
                    <a
                        href={book.cover_url}
                        target="_blank"
                        rel="noreferrer"
                        className="book-cover-link"
                    >
                        Open cover image ↗
                    </a>
                )}
            </div>
        </aside>
    </div>

    <section className="book-reviews-section">
        <h2 className="reviews-title">Reviews</h2>

        <ul className="reviews-list">
            {reviews.map((review, idx) => (
                <li key={idx} className="review-item">
                    <Link
                        to={`/people/${review.user_id}`}
                        className="review-link-card"
                    >
                        <div className="review-header">
                            <span className="review-user">
                                {review.user_netid}
                            </span>
                            <span className="review-rating">
                                ⭐ {review.rating}
                            </span>
                        </div>
                        <p className="review-text">{review.review}</p>
                        <p className="review-date">{review.updated_at}</p>
                    </Link>
                </li>
            ))}
        </ul>
    </section>
</div>


    )
}

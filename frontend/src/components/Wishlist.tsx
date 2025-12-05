import './Wishlist.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function Wishlist() {

    const [books, setBooks] = useState([]);

    useEffect(() => {
        axios.get("/api/get_wishlist", {params: {key: sessionStorage.getItem("netid")}}).then((res) => setBooks(res.data.wishlist));
    }, []);

    return (
       <div id="wishlist-page">
    <NavBar />

    <div className="wishlist-header">
        <h1 className="wishlist-title">Wishlist</h1>
        <p className="wishlist-subtitle">
            Books you want to read later.
        </p>
    </div>

    <div className="wishlist-content">
        <ul className="wishlist-list">
            {books.map((book) => (
                <li key={book.id} className="wishlist-item">
                    <Link
                        to={`/book/${book.id}`}
                        className="wishlist-link"
                    >
                        <div className="wishlist-card">
                            <div className="wishlist-cover-wrapper">
                                <img
                                    src={book.cover_url}
                                    alt={`${book.title} cover`}
                                    className="wishlist-cover"
                                />
                            </div>

                            <div className="wishlist-info">
                                <div className="wishlist-book-title">
                                    {book.title}
                                </div>
                                <div className="wishlist-meta">
                                    <span className="wishlist-rating">
                                        {(book.average_rating === 0) ? "no rating" : `⭐ ${book.average_rating}`}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </Link>
                </li>
            ))}
        </ul>
    </div>
</div>

    )
}
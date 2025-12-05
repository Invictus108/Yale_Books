import './AlreadyRead.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function AlreadyRead() {
    const [books, setBooks] = useState([]);

    useEffect(() => {
        axios.get("/api/get_already_read", {params: {key: sessionStorage.getItem("netid")}}).then((res) => setBooks(res.data.already_read));
    }, []);

    return (
        <div className="AlreadyRead" id="alreadyread-page">
    <NavBar />

    <div className="already-header">
        <h1 className="already-title">Already Read</h1>
        <p className="already-subtitle">
            Books you've finished reading.
        </p>
    </div>

    <div className="already-content">
        <ul className="already-list">
            {books.map((book) => (
                <li key={book.id} className="already-item">
                    <Link
                        to={`/book/${book.id}`}
                        className="already-link"
                    >
                        <div className="already-card">
                            <div className="already-cover-wrapper">
                                <img
                                    src={book.cover_url}
                                    alt={`${book.title} cover`}
                                    className="already-cover"
                                />
                            </div>

                            <div className="already-info">
                                <div className="already-book-title">
                                    {book.title}
                                </div>
                                <div className="already-meta">
                                    <span className="already-rating">
                                        {(book.average_rating === 0)
                                            ? "no rating"
                                            : `⭐ ${book.average_rating}`}
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
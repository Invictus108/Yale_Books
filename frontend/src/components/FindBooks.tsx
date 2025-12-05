import './FindBooks.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";
import { useParams, useNavigate } from "react-router-dom"

export default function FindBooks() {
    const [books, setBooks] = useState([]);


    // update on query
    useEffect(() => {
        axios.get("/api/get_recommendations", {params: {user: sessionStorage.getItem("netid")}}).then((res) => setBooks(res.data.books));
    }, []);



    return (
        <div id="recommended-page">
    <NavBar />

    <div className="recommended-header">
        <h1 className="recommended-title">Recommended Books for You</h1>
        <p className="recommended-subtitle">
            Based on your reading history and favorites.
        </p>
    </div>

    <div className="recommended-content">
        <ul className="recommended-list">
            {books.map((book) => (
                <li key={book.id} className="recommended-item">
                    <Link
                        to={`/book/${book.id}`}
                        className="recommended-link"
                    >
                        <div className="recommended-card">
                            <div className="recommended-cover-wrapper">
                                <img
                                    src={book.cover_url}
                                    alt={`${book.title} cover`}
                                    className="recommended-cover"
                                />
                            </div>

                            <div className="recommended-info">
                                <div className="recommended-book-title">
                                    {book.title}
                                </div>
                                <div className="recommended-rating">
                                     {(book.average_rating === 0) ? "no rating" : `⭐ ${book.average_rating}`}
                                </div>
                            </div>
                        </div>
                    </Link>
                </li>
            ))}
        </ul>
    </div>
</div>
    );
}
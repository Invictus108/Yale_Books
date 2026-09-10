import { coverSrc, onCoverError } from '../lib/cover';
import type { BookData } from '../types';
import './Home.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function Home() {
    const [books, setBooks] = useState<BookData[]>([]);

    useEffect(() => {
        axios.get("/api/get_recommendations", {
            params: { user: sessionStorage.getItem("netid") }
        })
            .then((res) => setBooks(res.data.books ?? []))
            .catch((e) => { console.error("recommendations failed", e); setBooks([]); });
    }, []);

    return (
        <div id="home-page">
            <NavBar />

            <div className="home-header">
                <h1 className="page-title">Home</h1>
                <h2 className="welcome-text">
                    Welcome to Yale Books {sessionStorage.getItem("netid")}
                </h2>
            </div>

            <div className="book-list-container">
                <ul className="book-list">
                    {books.map((book) => (
                        <li key={book.id} className="book-list-item">
                            <Link to={`/book/${book.id}`} className="book-link">
                                <div className="book-card">

                                    <img 
                                        src={coverSrc(book.cover_url)}
                                        onError={onCoverError}
                                        alt={`${book.title} cover`}
                                        className="book-cover"
                                    />

                                    <div className="book-info">
                                        <div className="book-title">{book.title}</div>
                                        <div className="book-rating">
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

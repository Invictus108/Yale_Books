import './Author.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";
import { useParams, useNavigate } from "react-router-dom"

export default function Author() {
    const {author} = useParams();
    const [books, setBooks] = useState([]);


    // update on query
    useEffect(() => {
        axios.get("/api/get_author_books", {params: {name: author}}).then((res) => setBooks(res.data.books));
    }, []);



    return (
        <div id="author-books-page" className="author-books-page">
    <NavBar />

    <div className="author-header">
        <h1 className="author-title">Books by {author}</h1>
        <p className="author-subtitle">
            Browse all books in Yale Books by this author.
        </p>
    </div>

    <div className="author-books-content">
        {books.length === 0 ? (
            <p className="author-empty">No books found for this author.</p>
        ) : (
            <ul className="author-book-list">
                {books.map((book) => (
                    <li key={book.id} className="author-book-item">
                        <Link
                            to={`/book/${book.id}`}
                            className="author-book-link"
                        >
                            <div className="author-book-card">
                                <div className="author-book-cover-wrapper">
                                    <img
                                        src={book.cover_url}
                                        alt={`${book.title} cover`}
                                        className="author-book-cover"
                                    />
                                </div>
                                <div className="author-book-info">
                                    <div className="author-book-title">
                                        {book.title}
                                    </div>
                                    <div className="author-book-meta">
                                        <span className="author-book-rating">
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
        )}
    </div>
</div>

    );
}
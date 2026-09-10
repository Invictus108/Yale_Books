import type { BookData, GenreData } from '../types';
import './Search.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function Search() {
    const [bookQuery, setBookQuery] = useState("");
    const [authorQuery, setAuthorQuery] = useState("");
    const [genres, setGenres] = useState<GenreData[]>([]);
    const [following, setFollowing] = useState(false);
    const [selectedGenres, setSelectedGenres] = useState<number[]>([]); 
    const [description, setDescription] = useState("");
    const [advancedSearch, setAdvancedSearch] = useState(false);
    const [alreadyRead, setAlreadyRead] = useState(false);
    const [wishlist, setWishlist] = useState(false);
    const [trigger, setTrigger] = useState(1);


    const [books, setBooks] = useState<BookData[]>([]);

    // get genres for form
    useEffect(() => {
        axios.get("/api/get_all_genres").then((res) => setGenres(res.data.genres));
    }, []);

    // update on query
    useEffect(() => {
        console.log(selectedGenres)
        axios.get("/api/search_books", {params: {book: bookQuery, author: authorQuery, genres: selectedGenres, following: following, description: description, advancedSearch: advancedSearch, user: sessionStorage.getItem("netid"), alreadyRead: alreadyRead, wishlist: wishlist}}).then((res) => setBooks(res.data.books)).then(() => setAdvancedSearch(false));
        
    }, [bookQuery, authorQuery, genres, following, selectedGenres, alreadyRead, wishlist, trigger]);

    
    const handleDropdownChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const options = e.target.options;
        const newSelectedIds: number[] = [];

        // Iterate through all options to find which ones are selected
        for (let i = 0; i < options.length; i++) {
            if (options[i].selected) {
                // Parse the value (which is the ID) into an integer
                newSelectedIds.push(parseInt(options[i].value, 10));
            }
        }
        // Update the state with the new array of IDs
        setSelectedGenres(newSelectedIds);
    };


    return (
 <div id="search-page">
    <NavBar />

    <div className="search-header">
        <h1 className="search-title">Search Books</h1>
        <p className="search-subtitle">
            Search by title, author, description, and genre filters.
        </p>
    </div>

    <div className="search-layout">
        <form className="search-form">
            <div className="search-field">
                <label className="search-label">Title</label>
                <input 
                    className="search-input"
                    type="text"
                    value={bookQuery}
                    onChange={(e) => setBookQuery(e.target.value)}
                    placeholder="Search by title"
                />
            </div>

            <div className="search-field">
                <label className="search-label">Author</label>
                <input 
                    className="search-input"
                    type="text"
                    value={authorQuery}
                    onChange={(e) => setAuthorQuery(e.target.value)}
                    placeholder="Search by author"
                />
            </div>

            <div className="search-field">
                <label className="search-label">Description (sorting hint)</label>
                <input
                    className="search-input"
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Description (will determine how it's sorted)"
                />
            </div>

            {/* --- NEW MULTI-SELECT GENRE DROPDOWN --- */}
            <div className="search-field">
                <label htmlFor="genre-select" className="search-label">
                    Filter by Genres <span className="search-label-hint">(Ctrl/Cmd-click for multiple)</span>
                </label>
                <div className="genre-select-container">
                    <select
                        id="genre-select"
                        multiple
                        size={5}
                        onChange={handleDropdownChange}
                        value={selectedGenres.map(String)}
                        className="genre-select"
                    >
                        {genres.map((option) => (
                            <option 
                                key={option.id} 
                                value={option.id}
                            >
                                {option.genre}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
            {/* -------------------------------------- */}

            {/* --- New Toggle Input 1 (Follower) --- */}
            <div className="search-field toggle-field">
                <label className="toggle-label">
                    <input
                        type="checkbox"
                        checked={following}
                        onChange={(e) => setFollowing(e.target.checked)}
                        className="toggle-checkbox"
                    />
                    <span>Only show book highly rated by people you follow</span>
                </label>
            </div>

            <div className="search-field toggle-field">
                <label className="toggle-label">
                    <input
                        type="checkbox"
                        checked={alreadyRead}
                        onChange={(e) => setAlreadyRead(e.target.checked)}
                        className="toggle-checkbox"
                    />
                    <span>Hide Finished Books</span>
                </label>
            </div>

            <div className="search-field toggle-field">
                <label className="toggle-label">
                    <input
                        type="checkbox"
                        checked={wishlist}
                        onChange={(e) => setWishlist(e.target.checked)}
                        className="toggle-checkbox"
                    />
                    <span>Hide Books in Wishlist</span>
                </label>
            </div>

            <div className="search-advanced-note">
                <p>Advanced Search will use ML and may take longer.</p>
            </div>

            <div className="search-actions">
                <button
                    className="advanced-button"
                    onClick={(e) => {
                        e.preventDefault();
                        setAdvancedSearch(true);
                        setTrigger(trigger + 1);
                    }}
                >
                    Advanced Search
                </button>
            </div>
        </form>

        <div className="search-results-section">
    {books.length === 0 ? (
        <div className="search-empty-state">
            <p>No books found.</p>
            <Link to="/add_book" className="add-book-link">
                Add Book
            </Link>
        </div>
    ) : (
        <div className="search-results-scroll">
            <ul className="search-results-list">
                {books.map((book) => (
                    <li key={book.id} className="search-result-item">
                        <Link
                            to={`/book/${book.id}`}
                            className="search-result-link"
                        >
                            <div className="search-result-card">
                                <div className="search-result-cover-wrapper">
                                    <img
                                        src={book.cover_url}
                                        alt={`${book.title} cover`}
                                        className="search-result-cover"
                                    />
                                </div>
                                <div className="search-result-info">
                                    <div className="search-result-title">
                                        {book.title}
                                    </div>
                                    <div className="search-result-meta">
                                        <span className="search-result-rating">
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
    )}
</div>


    </div>
</div>

    );
}

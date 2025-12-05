import './AddBook.css'
import NavBar from './NavBar.tsx';
import axios from 'axios';
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AddBook() {
    const [form, setForm] = useState({
        title: "",
        date_published: "",
        blurb: "",
        length: "",
        link: "",
        authors: "",
        genres: "",
    });


    const navigate = useNavigate()

    const [coverImage, setCoverImage] = useState<File | null>(null);

    const handleChange = (e: any) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: any) => {
        e.preventDefault();

        const fd = new FormData();
        Object.entries(form).forEach(([key, val]) => fd.append(key, val));
        fd.append("cover_image", coverImage!); // guaranteed non-null
        fd.append("netid", sessionStorage.getItem("netid")!);

        try {
            await axios.post("/api/add_book", fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            alert("Book created successfully!");
        } catch (err) {
            console.error(err);
            alert("Error creating book.");
        }
        navigate(-1);
    };
    return (
         <div id="add-book-page">
    <NavBar />

    <div className="add-book-container">
        <header className="add-book-header">
            <h1 className="add-book-title">Add New Book</h1>
            <p className="add-book-subtitle">
                Fill out the details below to add a new book to Yale Books.
            </p>
        </header>

        <form onSubmit={handleSubmit} className="add-book-form">
            <div className="form-field">
                <label className="field-label">Title</label>
                <input
                    className="field-input"
                    type="text"
                    name="title"
                    value={form.title}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Date Published</label>
                <input
                    className="field-input"
                    type="text"
                    name="date_published"
                    value={form.date_published}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Blurb</label>
                <textarea
                    className="field-textarea"
                    name="blurb"
                    value={form.blurb}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Length (pages)</label>
                <input
                    className="field-input"
                    type="number"
                    name="length"
                    value={form.length}
                    required
                    min={1}
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Purchase Link</label>
                <input
                    className="field-input"
                    type="text"
                    name="link"
                    value={form.link}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Authors (comma separated)</label>
                <input
                    className="field-input"
                    type="text"
                    name="authors"
                    value={form.authors}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Genres (comma separated)</label>
                <input
                    className="field-input"
                    type="text"
                    name="genres"
                    value={form.genres}
                    required
                    onChange={handleChange}
                />
            </div>

            <div className="form-field">
                <label className="field-label">Cover Image</label>
                <input
                    className="field-file-input"
                    type="file"
                    accept="image/*"
                    required
                    onChange={(e) => setCoverImage(e.target.files?.[0] ?? null)}
                />
                <p className="field-hint">Upload a clear front cover image.</p>
            </div>

            <div className="form-actions">
                <button type="submit" className="primary-button">
                    Create Book
                </button>
            </div>
        </form>
    </div>
</div>

    )
}
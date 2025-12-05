import './Review.css'
import axios from 'axios';
import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Review() {
    const navigate = useNavigate()
    const { id } = useParams()

    const [rating, setRating] = useState(0);
    const [review, setReview] = useState("");

    const handleSubmit = (e: any) => {
        e.preventDefault();
        axios
        .post("/api/add_review", { user: sessionStorage.getItem("netid"), book: id, rating: rating, review: review })
        .then(() => navigate(-1));
    }

    return (
        <div id="review-page" className="review-page">
            <button
            onClick={() => navigate(-1)}
            className="back-button"
        >
            ← Back
        </button>
    <div className="review-card">
        <h1 className="review-title">Review</h1>

        <form onSubmit={handleSubmit} className="review-form">
            <div className="review-field">
                <label className="review-label">
                    Rating (1–5):
                </label>
                <select
                    className="review-select"
                    value={rating}
                    onChange={(e) => setRating(Number(e.target.value))}
                    required
                >
                    <option value="">Select…</option>
                    <option value="1">1 ⭐</option>
                    <option value="2">2 ⭐</option>
                    <option value="3">3 ⭐</option>
                    <option value="4">4 ⭐</option>
                    <option value="5">5 ⭐</option>
                </select>
            </div>

            <div className="review-field">
                <label className="review-label">
                    Review:
                </label>
                <textarea
                    className="review-textarea"
                    value={review}
                    onChange={(e) => setReview(e.target.value)}
                    placeholder="Write your thoughts..."
                    required
                />
            </div>

            <div className="review-actions">
                <button type="submit" className="primary-button review-submit-button">
                    Submit Review
                </button>
            </div>
        </form>
    </div>
</div>

    )
}
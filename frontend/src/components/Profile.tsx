import { coverSrc, onCoverError } from '../lib/cover';
import type { ReviewData, UserData } from '../types';
import './Profile.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function Profile() {
    const [id, setId] = useState(null);

    // get user id
    useEffect(() => {
        axios.get("/api/whoami", {params: {user: sessionStorage.getItem("netid")}}).then((res) => setId(res.data.id)).catch((e) => console.error("request failed", e));
    }, []); 

    const [reviews, setReviews] = useState<ReviewData[]>([]);
    const [user, setUser] = useState<Partial<UserData>>({});


    useEffect(() => {
        if (!id) return;
        axios.get("/api/get_person", {params: {key: id}}).then((res) => setUser(res.data.user)).catch((e) => console.error("request failed", e));
        axios.get("/api/get_user_reviews", {params: {key: id}}).then((res) => setReviews(res.data.reviews)).catch((e) => console.error("request failed", e));
    }, [id]);


    const handleDelete = (review_id: number) => {
        console.log(review_id);
        axios.post("/api/delete_review",  {id: review_id}).then(() => {
            axios.get("/api/get_person", {params: {key: id}}).then((res) => setUser(res.data.user)).catch((e) => console.error("request failed", e));
            axios.get("/api/get_user_reviews", {params: {key: id}}).then((res) => setReviews(res.data.reviews)).catch((e) => console.error("request failed", e));
        })
        
    }



    return (
       <div id="my-profile-page" className="profile-container">
    <NavBar />

    <div className="profile-inner">
        <header className="profile-header">
            <h1 className="profile-page-title">Profile</h1>

            <div className="profile-identity">
                <div className="profile-avatar">
                    {user.netid?.[0]?.toUpperCase() ?? "?"}
                </div>
                <div className="profile-identity-text">
                    <h2 className="profile-netid">{user.netid}</h2>
                    <p className="profile-reputation">
                        Reputation: <span>{user.reputation}</span>
                    </p>
                </div>
            </div>
        </header>

        <section className="profile-top-section">
            <div className="profile-stats-card">
                <div className="profile-stat">
                    <span className="profile-stat-label">Followers</span>
                    <span className="profile-stat-value">{user.followers}</span>
                </div>
                <div className="profile-stat">
                    <span className="profile-stat-label">Following</span>
                    <span className="profile-stat-value">{user.following}</span>
                </div>
            </div>

            <div className="profile-edit-wrapper">
                <Link to={`/bio`} className="profile-edit-link">
                    Edit Profile
                </Link>
            </div>
        </section>

        <section className="profile-bio-section">
            <h2 className="profile-section-title">Bio</h2>
            <p className="profile-bio">
                {user.bio || "You haven't added a bio yet."}
            </p>
        </section>

        <section className="profile-reviews-section">
            <h2 className="profile-section-title">Your Reviews</h2>

            {reviews.length === 0 ? (
                <p className="profile-empty-reviews">
                    You haven't written any reviews yet.
                </p>
            ) : (
                <ul className="profile-reviews-list">
                    {reviews.map((review) => (
                        <li key={review.id} className="profile-review-item">
                            <div className="profile-review-card">
                                <Link
                                    to={`/book/${review.book.id}`}
                                    className="profile-review-main"
                                >
                                    <div className="profile-review-cover-wrapper">
                                        <img
                                            src={coverSrc(review.book.cover_url)}
                                        onError={onCoverError}
                                            alt={`${review.book.title} cover`}
                                            className="profile-review-cover"
                                        />
                                    </div>

                                    <div className="profile-review-info">
                                        <div className="profile-review-header">
                                            <div className="profile-review-title">
                                                {review.book.title}
                                            </div>
                                        </div>
                                        <div className="profile-review-rating">
                                                ⭐ {review.rating}
                                            </div>
                                        <p className="profile-review-text">
                                            {review.review}
                                        </p>
                                        <p className="profile-review-date">
                                            {review.updated_at}
                                        </p>
                                    </div>
                                </Link>

                                <button
                                    type="button"
                                    className="profile-delete-button"
                                    onClick={() => handleDelete(review.id)}
                                >
                                    Delete
                                </button>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </section>
    </div>
</div>


    )
}

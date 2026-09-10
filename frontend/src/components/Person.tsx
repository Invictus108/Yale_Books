import { coverSrc, onCoverError } from '../lib/cover';
import type { ReviewData, UserData } from '../types';
import './Person.css'
import { useParams, useNavigate } from "react-router-dom"
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function Book() {
    const navigate = useNavigate()
    const { id } = useParams()

    const [reviews, setReviews] = useState<ReviewData[]>([]);
    const [user, setUser] = useState<Partial<UserData>>({});
    const [follow, setFollow] = useState(false);


    useEffect(() => {
        let cancelled = false;
        axios.get("/api/get_person", {params: {key: id}})
            .then((res) => { if (!cancelled) setUser(res.data.user); }).catch(() => {});
        axios.get("/api/get_user_reviews", {params: {key: id}})
            .then((res) => { if (!cancelled) setReviews(res.data.reviews ?? []); })
            .catch(() => { if (!cancelled) setReviews([]); });
        axios.get("/api/is_friend", {params: {user1: id, user2: sessionStorage.getItem("netid")}})
            .then((res) => { if (!cancelled) setFollow(res.data.is_friend); }).catch(() => {});
        return () => { cancelled = true; };
    }, [id]);

    // update follow count as it changes
    useEffect(() => {
        axios.get("/api/get_person", {params: {key: id}}).then((res) => setUser(res.data.user)).catch((e) => console.error("request failed", e));
    }, [follow]);

    // follow and unfollow handlers
    const handleFollow = () => {
        axios
        .post("/api/follow", { follower: sessionStorage.getItem("netid"), followee: id })
        .then(() => setFollow(true));
    };

    const handleUnfollow = () => {
        axios
        .post("/api/unfollow", { follower: sessionStorage.getItem("netid"), followee: id })
        .then(() => setFollow(false));
    };



    return (
        <div id="profile-page">
    <div className="profile-header">
        <button
            onClick={() => navigate(-1)}
            className="back-button"
        >
            ← Back
        </button>

        <div className="profile-identity">
            <div className="profile-avatar">
                {user.netid?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="profile-identity-text">
                <h1 className="profile-netid">{user.netid}</h1>
                <p className="profile-reputation">
                    Reputation: <span>{user.reputation}</span>
                </p>
            </div>
        </div>
    </div>

    <div className="profile-top-row">
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

        <div className="profile-actions">
            {follow ? (
                <button
                    onClick={handleUnfollow}
                    className="secondary-button profile-follow-button"
                >
                    Unfollow
                </button>
            ) : (
                <button
                    onClick={handleFollow}
                    className="primary-button profile-follow-button"
                >
                    Follow
                </button>
            )}
        </div>
    </div>

    <div className="profile-bio-card">
        <h2 className="profile-section-title">Bio</h2>
        <p className="profile-bio">
            {user.bio || "This user hasn't added a bio yet."}
        </p>
    </div>

    <section className="profile-reviews-section">
        <h2 className="profile-section-title">Reviews</h2>

        {reviews.length === 0 ? (
            <p className="profile-empty-reviews">
                No reviews from this user yet.
            </p>
        ) : (
            <ul className="profile-reviews-list">
                {reviews.map((review, idx) => (
                    <li key={idx} className="profile-review-item">
                        <Link
                            to={`/book/${review.book.id}`}
                            className="profile-review-link"
                        >
                            <div className="profile-review-card">
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
                            </div>
                        </Link>
                    </li>
                ))}
            </ul>
        )}
    </section>
</div>

    )
}

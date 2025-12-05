import './People.css'
import NavBar from './NavBar.tsx';
import { useState, useEffect } from "react";
import axios from 'axios';
import { Link } from "react-router-dom";

export default function People() {
    const [query, setQuery] = useState("");
    const [people, setPeople] = useState([]);
    const [following, setFollowing] = useState(false);
    const [followers, setFollowers] = useState(false);

    // update on query
    useEffect(() => {
        axios.get("/api/search_people", {params: {search: query, following: following, followers: followers, user: sessionStorage.getItem("netid")}}).then((res) => setPeople(res.data.users));
    }, [query, following, followers]);

    return (
        <div id="people-page">
    <NavBar />

    <div className="people-header">
        <h1 className="people-title">People</h1>
        <p className="people-subtitle">Search Yale Books users by NetID and filter by connections.</p>
    </div>

    <div className="people-layout">
        <form className="people-form">
            <div className="people-field">
                <label className="people-label">Search by NetID</label>
                <input 
                    className="people-input"
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="NetID"
                />
            </div>

            {/* --- New Toggle Input 1 (Follower) --- */}
            <div className="people-field people-toggle">
                <label className="toggle-label">
                    <input
                        type="checkbox"
                        checked={following}
                        onChange={(e) => setFollowing(e.target.checked)}
                        className="toggle-checkbox"
                    />
                    <span>Show Only People You Follow</span>
                </label>
            </div>

            {/* --- New Toggle Input 2 (Following) --- */}
            <div className="people-field people-toggle">
                <label className="toggle-label">
                    <input
                        type="checkbox"
                        checked={followers}
                        onChange={(e) => setFollowers(e.target.checked)}
                        className="toggle-checkbox"
                    />
                    <span>Show Only People Who Follow You</span>
                </label>
            </div>
        </form>

   <div className="people-results">
    {people.length === 0 ? (
        <p className="people-empty">No people found.</p>
    ) : (
        <div className="people-results-scroll">
            <ul className="people-list">
                {people.map((person) => (
                    <li key={person.id} className="people-item">
                        <Link to={`/people/${person.id}`} className="people-link">
                            <div className="people-card">
                                <div className="people-avatar">
                                    {person.netid?.[0]?.toUpperCase() ?? "?"}
                                </div>
                                <div className="people-info">
                                    <div className="people-netid">
                                        {person.netid}
                                    </div>
                                    <div className="people-meta">
                                        <span className="people-reputation">
                                            reputation: {person.reputation}
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

    )
}
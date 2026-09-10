import './BioForm.css'
import axios from 'axios';
import { useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Review() {
    const navigate = useNavigate()

    const [bio, setBio] = useState("");

    const handleSubmit = (e: any) => {
        e.preventDefault();
        axios
        .post("/api/update_bio", { user: sessionStorage.getItem("netid"), bio: bio })
        .then(() => navigate(-1));
    }

    return (
        <div id="bio-page" className="bio-page">
            <button
            onClick={() => navigate(-1)}
            className="back-button"
        >
            ← Back
        </button>
    <div className="bio-card">
        <h1 className="bio-title">Edit Bio</h1>

        <form onSubmit={handleSubmit} className="bio-form">
            <div className="bio-field">
                <label className="bio-label" htmlFor="bio-textarea">
                    Bio
                </label>
                <textarea
                    id="bio-textarea"
                    className="bio-textarea"
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="Write bio here..."
                    required
                />
            </div>

            <div className="bio-actions">
                <button type="submit" className="primary-button bio-submit-button">
                    Submit Bio
                </button>
            </div>
        </form>
    </div>
</div>

    )
}

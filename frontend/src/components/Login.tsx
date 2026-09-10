import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import './Login.css'

type LoginProps = {
  onLogin?: (netid: string) => void;
};

export default function Login({ onLogin }: LoginProps){
    const [demo, setDemo] = useState(false);
    const [netid, setNetid] = useState("");
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    // ask the backend whether CAS is on or we are in demo mode
    useEffect(() => {
        axios.get("/api/auth_mode")
            .then((res) => setDemo(Boolean(res.data.demo)))
            .catch(() => setDemo(false));
    }, []);

    const goToCas = () => (window.location.href = `${API_URL}/login`);

    // demo login - just a netid, no password
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();

        const cleaned = netid.trim().toLowerCase();
        if (!cleaned) {
            setError("Please enter your NetID.");
            return;
        }

        setSubmitting(true);
        setError("");

        try {
            const res = await axios.post("/demo_login", { netid: cleaned });
            if (onLogin) {
                onLogin(res.data.netid);
            } else {
                window.location.reload();
            }
        } catch (err: any) {
            setError(err?.response?.data?.error || "Could not log in. Please try again.");
            setSubmitting(false);
        }
    };

    // normal production flow
    if (!demo) {
        return (
  <div id="not-logged-page" className="not-logged-page">
  <div className="not-logged-card">
    <h1 className="not-logged-title">You are not logged in</h1>
    <p className="not-logged-text">
      Please log in with your Yale CAS account to access Yale Books.
    </p>

    <button
      className="primary-button not-logged-button"
      onClick={goToCas}
    >
      Login with CAS
    </button>
  </div>
</div>
        )
    }

    // demo mode - CAS is down, so let people in with just their NetID
    return (
  <div id="not-logged-page" className="not-logged-page">
  <div className="not-logged-card">
    <h1 className="not-logged-title">Sign in to Yale Books</h1>
    <p className="not-logged-text">
      Yale CAS is unavailable, so this is a demo login. Enter your NetID to continue.
    </p>

    <form className="demo-login-form" onSubmit={handleSubmit}>
      <label className="demo-login-label" htmlFor="demo-netid">NetID</label>
      <input
        id="demo-netid"
        className="demo-login-input"
        type="text"
        value={netid}
        onChange={(e) => setNetid(e.target.value)}
        placeholder="abc123"
        autoComplete="username"
        autoFocus
      />

      {error && <p className="demo-login-error">{error}</p>}

      <button
        className="primary-button not-logged-button"
        type="submit"
        disabled={submitting}
      >
        {submitting ? "Signing in..." : "Continue"}
      </button>
    </form>

    <p className="demo-login-note">
      Demo mode: no password is required and nothing is verified.
    </p>

    <details className="cas-dropdown">
      <summary className="cas-dropdown-summary">Try to log in with CAS instead</summary>
      <div className="cas-dropdown-body">
        <p className="not-logged-text">
          If Yale CAS is back up, you can use the normal login.
        </p>
        <button
          className="primary-button not-logged-button"
          type="button"
          onClick={goToCas}
        >
          Login with CAS
        </button>
      </div>
    </details>
  </div>
</div>
    )
}

import './Login.css'

export default function Login(){
    return (
  <div id="not-logged-page" className="not-logged-page">
  <div className="not-logged-card">
    <h1 className="not-logged-title">You are not logged in</h1>
    <p className="not-logged-text">
      Please log in with your Yale CAS account to access Yale Books.
    </p>

    <button
      className="primary-button not-logged-button"
      onClick={() => (window.location.href = "/login")}
    >
      Login with CAS
    </button>
  </div>
</div>


    ) 
}
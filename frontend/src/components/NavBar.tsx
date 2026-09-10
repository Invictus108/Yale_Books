import { API_URL } from '../config';
import { Link, useLocation } from "react-router-dom";
import "./NavBar.css";

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="nav-left">
          <div id="navbar-title">Yale Books</div>
        </div>

        <ul className="nav-links">
          <li className={location.pathname === "/" ? "active-link" : ""}>
            <Link to="/">Home</Link>
          </li>
          <li className={location.pathname === "/findbooks" ? "active-link" : ""}>
            <Link to="/findbooks">Find Books</Link>
          </li>
          <li className={location.pathname === "/mybooks" ? "active-link" : ""}>
            <Link to="/mybooks">Wishlist</Link>
          </li>
          <li className={location.pathname === "/finishedbooks" ? "active-link" : ""}>
            <Link to="/finishedbooks">Finished</Link>
          </li>
          <li className={location.pathname === "/search" ? "active-link" : ""}>
            <Link to="/search">Search</Link>
          </li>
          <li className={location.pathname === "/people" ? "active-link" : ""}>
            <Link to="/people">People</Link>
          </li>
          <li className={location.pathname === "/profile" ? "active-link" : ""}>
            <Link to="/profile">Profile</Link>
          </li>
          <li>
            <button
              className="logout-button"
              onClick={() => (window.location.href = `${API_URL}/logout`)}
            >
              Logout
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
}

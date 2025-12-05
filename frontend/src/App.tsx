import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import axios from "axios";
import Login from './components/Login.tsx';
import Home from './components/Home.tsx';
import Book from './components/Book.tsx';
import Wishlist from "./components/Wishlist.tsx";
import FindBooks from "./components/FindBooks.tsx";
import Search from "./components/Search.tsx";
import People from "./components/People.tsx";
import Person from "./components/Person.tsx";
import AddBook from "./components/AddBook.tsx";
import AlreadyRead from "./components/AlreadyRead.tsx";
import Profile from "./components/Profile.tsx";
import Review from "./components/Review.tsx";
import BioForm from "./components/BioForm.tsx";
import Author from "./components/Author.tsx";

export default function App() {
  const [netid, setNetid] = useState(null);

  // check to see if user is logged in
  useEffect(() => {
    axios.get("/api/me").then((res) => setNetid(res.data.netid));
  }, []);

  // redirect to login
  if (!netid) {
    return ( <Login />)
  } else {
    sessionStorage.setItem("netid", netid);
  }

  // else use main router
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/findbooks" element={<FindBooks />} />
        <Route path="/mybooks" element={<Wishlist />} />
        <Route path="/finishedbooks" element={<AlreadyRead />} />
        <Route path="/search" element={<Search />} />
        <Route path="/people" element={<People />} />
        <Route path="/add_book" element={<AddBook />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/bio" element={<BioForm />} />

        <Route path="/author/:author" element={<Author />} />
        <Route path="/review/:id" element={<Review />} />
        <Route path="/book/:id" element={<Book />} />
        <Route path="/people/:id" element={<Person />} />
      </Routes>
    </Router>
  )
}

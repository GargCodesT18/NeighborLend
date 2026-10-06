import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Menu, X, User } from 'lucide-react';
import './Navbar.css';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path ? 'active' : '';

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="navbar glass">
      <div className="container nav-container">
        <Link to="/" className="nav-logo gradient-text">
          NeighborLend
        </Link>

        <div className="nav-links desktop-only">
          <Link to="/browse" className={`nav-link ${isActive('/browse')}`}>Browse</Link>
          {isAuthenticated && (
            <>
              <Link to="/create-listing" className={`nav-link ${isActive('/create-listing')}`}>Lend Item</Link>
              <Link to="/create-request" className={`nav-link ${isActive('/create-request')}`}>Request Item</Link>
              <Link to="/my-listings" className={`nav-link ${isActive('/my-listings')}`}>My Listings</Link>
            </>
          )}
        </div>

        <div className="nav-actions desktop-only">
          {isAuthenticated ? (
            <div className="user-menu">
              <div className="user-avatar">
                <User size={18} />
              </div>
              <span className="user-name">{user?.username || 'User'}</span>
              <button onClick={handleLogout} className="btn-outline logout-btn">Logout</button>
            </div>
          ) : (
            <div className="auth-buttons">
              <Link to="/login" className="btn-outline">Log in</Link>
              <Link to="/register" className="btn-primary">Sign up</Link>
            </div>
          )}
        </div>

        <button 
          className="mobile-menu-btn mobile-only" 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="mobile-menu glass">
          <Link to="/browse" className={`nav-link ${isActive('/browse')}`} onClick={() => setMobileMenuOpen(false)}>Browse</Link>
          {isAuthenticated ? (
            <>
              <Link to="/create-listing" className={`nav-link ${isActive('/create-listing')}`} onClick={() => setMobileMenuOpen(false)}>Lend Item</Link>
              <Link to="/create-request" className={`nav-link ${isActive('/create-request')}`} onClick={() => setMobileMenuOpen(false)}>Request Item</Link>
              <Link to="/my-listings" className={`nav-link ${isActive('/my-listings')}`} onClick={() => setMobileMenuOpen(false)}>My Listings</Link>
              <div className="mobile-user">
                <span>{user?.username}</span>
                <button onClick={() => { handleLogout(); setMobileMenuOpen(false); }} className="btn-outline logout-btn">Logout</button>
              </div>
            </>
          ) : (
            <div className="mobile-auth">
              <Link to="/login" className="btn-outline" onClick={() => setMobileMenuOpen(false)}>Log in</Link>
              <Link to="/register" className="btn-primary" onClick={() => setMobileMenuOpen(false)}>Sign up</Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};

export default Navbar;

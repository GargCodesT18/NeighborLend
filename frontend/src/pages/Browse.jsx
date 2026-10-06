import React, { useState, useEffect } from 'react';
import { Search, MapPin, SlidersHorizontal } from 'lucide-react';
import ListingCard from '../components/ListingCard';
import api from '../api/client';
import './Browse.css';

const CATEGORIES = ['All', 'Tools', 'Electronics', 'Sports', 'Party', 'Books', 'Other'];

const Browse = () => {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [radius, setRadius] = useState(10);
  const [location, setLocation] = useState({ lat: 28.6139, lon: 77.2090 }); // Default Delhi
  const [locationName, setLocationName] = useState('New Delhi (Default)');

  const fetchListings = async () => {
    setLoading(true);
    try {
      // Mock API params construction
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (category !== 'All') params.append('category', category);
      params.append('lat', location.lat);
      params.append('lon', location.lon);
      params.append('radius_km', radius);

      // In real scenario: const res = await api.get(`/listings/search?${params.toString()}`);
      // For now, let's mock or call empty
      const res = await api.get(`/listings/search?${params.toString()}`).catch(() => ({ data: [] }));
      
      // Mock data if API is down
      if (!res.data || res.data.length === 0) {
        setListings([
          { id: 1, title: 'Bosch Power Drill', price_per_day: 150, category: 'Tools', address: 'Connaught Place, Delhi', distance_km: 2.4, owner: { username: 'ajay_s', rating: 4.8 } },
          { id: 2, title: 'Sony PS5 Console + 2 Controllers', price_per_day: 800, category: 'Electronics', address: 'Hauz Khas, Delhi', distance_km: 5.1, owner: { username: 'gamer99', rating: 4.9 } },
          { id: 3, title: 'Trekking Tent (4 Person)', price_per_day: 300, category: 'Sports', address: 'Vasant Kunj, Delhi', distance_km: 8.7, owner: { username: 'trekker', rating: 5.0 } },
        ]);
      } else {
        setListings(res.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchListings();
  }, [category]); // Re-fetch when category changes

  const handleSearch = (e) => {
    e.preventDefault();
    fetchListings();
  };

  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setLocationName('Current Location');
      });
    } else {
      alert("Geolocation is not supported by this browser.");
    }
  };

  return (
    <div className="browse-page container fade-in-up">
      
      {/* Search Header */}
      <section className="search-section glass">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <Search className="search-icon" size={20} />
            <input 
              type="text" 
              placeholder="What do you need?" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
          <button type="submit" className="btn-primary search-btn">Search</button>
        </form>

        <div className="filters-row">
          <div className="categories-scroll">
            {CATEGORIES.map(cat => (
              <button 
                key={cat}
                className={`category-pill ${category === cat ? 'active' : ''}`}
                onClick={() => setCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="location-filters">
            <div className="location-display" title={locationName}>
              <MapPin size={16} />
              <span className="truncate">{locationName}</span>
              <button onClick={getUserLocation} className="use-location-btn">Use My Location</button>
            </div>
            
            <div className="radius-filter">
              <SlidersHorizontal size={16} />
              <span>{radius} km</span>
              <input 
                type="range" 
                min="1" max="50" 
                value={radius} 
                onChange={(e) => setRadius(e.target.value)}
                onMouseUp={fetchListings}
                className="radius-slider"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Results */}
      <section className="results-section">
        <div className="results-header">
          <h2>Items near you {category !== 'All' && `in ${category}`}</h2>
          <span className="results-count">{listings.length} results</span>
        </div>

        {loading ? (
          <div className="listings-grid">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="skeleton-card glass"></div>
            ))}
          </div>
        ) : listings.length > 0 ? (
          <div className="listings-grid">
            {listings.map(listing => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        ) : (
          <div className="empty-state glass">
            <div className="empty-icon-wrapper">
              <Search size={48} />
            </div>
            <h3>No items found</h3>
            <p>Try expanding your search radius or changing the category.</p>
          </div>
        )}
      </section>
    </div>
  );
};

export default Browse;

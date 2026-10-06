import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { MapPin, Star, Shield, AlertCircle, Clock, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import './ListingDetail.css';

const ListingDetail = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock fetch listing by id
    const fetchListing = async () => {
      try {
        await new Promise(r => setTimeout(r, 800));
        setListing({
          id,
          title: 'Bosch Professional Power Drill',
          description: 'High power professional drill. Works perfectly. Comes with a set of 10 bits. Only used a few times for home projects.',
          price_per_day: 150,
          security_deposit: 1000,
          category: 'Tools',
          address: 'Connaught Place, New Delhi',
          lat: 28.6304,
          lon: 77.2177,
          image_url: null,
          ai_label: 'Power Drill',
          ai_confidence: 96,
          owner: {
            id: 2,
            username: 'ajay_s',
            rating: 4.8,
            member_since: '2023',
            trust_score: 85
          }
        });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchListing();
  }, [id]);

  if (loading) return <div className="loading-state">Loading...</div>;
  if (!listing) return <div className="loading-state">Listing not found</div>;

  const isOwner = user && user.username === listing.owner.username; // simplified check

  return (
    <div className="listing-detail-page fade-in-up">
      <div className="detail-hero">
        {listing.image_url ? (
          <img src={listing.image_url} alt={listing.title} className="detail-hero-image" />
        ) : (
          <div className="detail-hero-placeholder"></div>
        )}
        
        <div className="container detail-hero-content">
          <div className="detail-info-card glass">
            <span className="category-badge">{listing.category}</span>
            <h1 className="detail-title">{listing.title}</h1>
            <div className="detail-price-row">
              <span className="price-large gradient-text">₹{listing.price_per_day}</span>
              <span className="price-unit">/ day</span>
            </div>
            <div className="deposit-info">
              <Shield size={16} className="text-warning" />
              <span>Refundable Deposit: ₹{listing.security_deposit}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="container detail-body">
        <div className="detail-main">
          
          <section className="detail-section glass">
            <h3>Description</h3>
            <p className="description-text">{listing.description}</p>
          </section>

          {listing.ai_label && (
            <section className="detail-section glass ai-verification">
              <div className="ai-verification-header">
                <Check size={20} className="text-success" />
                <h3>AI Verified</h3>
              </div>
              <p>Our AI identified this item as <strong>{listing.ai_label}</strong> with {listing.ai_confidence}% confidence.</p>
            </section>
          )}

          <section className="detail-section glass">
            <h3>Location</h3>
            <div className="location-info">
              <MapPin className="text-accent" />
              <span>{listing.address}</span>
            </div>
            {/* Map placeholder */}
            <div className="map-placeholder">
              Map View (Lat: {listing.lat}, Lon: {listing.lon})
            </div>
          </section>

        </div>

        <div className="detail-sidebar">
          
          <div className="action-card glass">
            {isOwner ? (
              <div className="owner-actions">
                <button className="btn-primary full-width mb-3">Edit Listing</button>
                <button className="btn-outline text-danger full-width">Delete Listing</button>
              </div>
            ) : (
              <div className="borrower-actions">
                <button className="btn-primary full-width mb-3 tooltip-wrapper">
                  Book Now
                  <span className="tooltip-text">Coming soon in MVP v2</span>
                </button>
                <button className="btn-outline full-width tooltip-wrapper">
                  Negotiate
                  <span className="tooltip-text">Coming soon in MVP v2</span>
                </button>
              </div>
            )}
          </div>

          <div className="owner-card glass">
            <div className="owner-header">
              <div className="owner-avatar-large">
                {listing.owner.username[0].toUpperCase()}
              </div>
              <div>
                <h4>{listing.owner.username}</h4>
                <div className="member-since">Member since {listing.owner.member_since}</div>
              </div>
            </div>
            
            <div className="owner-stats">
              <div className="stat">
                <Star className="text-warning" size={18} fill="currentColor" />
                <span>{listing.owner.rating} Rating</span>
              </div>
              <div className="stat">
                <Shield className="text-success" size={18} />
                <span>{listing.owner.trust_score} Trust Score</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ListingDetail;

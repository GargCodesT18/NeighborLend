import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Image as ImageIcon, Star } from 'lucide-react';
import './ListingCard.css';

const ListingCard = ({ listing }) => {
  const navigate = useNavigate();
  
  const handleClick = () => {
    navigate(`/listing/${listing.id}`);
  };

  return (
    <div className="listing-card glass" onClick={handleClick}>
      <div className="listing-photo-area">
        {listing.image_url ? (
          <img src={listing.image_url} alt={listing.title} className="listing-photo" />
        ) : (
          <div className="listing-photo-placeholder">
            <ImageIcon size={48} className="placeholder-icon" />
          </div>
        )}
        
        <div className="photo-overlay">
          <div className="listing-category-badge">
            {listing.category || 'Item'}
          </div>
          <div className="listing-price-badge">
            ₹{listing.price_per_day}/day
          </div>
        </div>
      </div>

      <div className="listing-content">
        <h3 className="listing-title">{listing.title}</h3>
        
        <div className="listing-location">
          <MapPin size={14} className="location-icon" />
          <span>{listing.address || 'Location unavailable'}</span>
          {listing.distance_km && (
            <span className="distance-badge">• {listing.distance_km.toFixed(1)} km</span>
          )}
        </div>

        <div className="listing-owner">
          <div className="owner-avatar">
            <span className="owner-initial">{listing.owner?.username?.[0]?.toUpperCase() || 'U'}</span>
          </div>
          <span className="owner-name">{listing.owner?.username || 'Unknown User'}</span>
          <div className="owner-rating">
            <Star size={12} className="star-icon" fill="currentColor" />
            <span>{listing.owner?.rating || '4.9'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ListingCard;

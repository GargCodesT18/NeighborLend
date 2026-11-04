import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Edit2, Play, Pause, Trash2, X, Save, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import './MyListings.css';

const MyBorrowRequests = () => {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'as_borrower', 'as_lender'

  useEffect(() => {
    const fetchMyRequests = async () => {
      try {
        const res = await api.get('/borrow-requests/my');
        setRequests(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchMyRequests();
  }, []);

  const filteredRequests = requests.filter(r => {
    if (activeTab === 'all') return true;
    if (activeTab === 'as_borrower') return r.borrower_id === user?.id;
    if (activeTab === 'as_lender') return r.lender_id === user?.id;
    return true;
  });

  return (
    <div className="my-listings-page container fade-in-up">
      <div className="page-header">
        <h1>My Borrow Requests</h1>
        <div className="tab-buttons">
          <button className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>All</button>
          <button className={`tab-btn ${activeTab === 'as_borrower' ? 'active' : ''}`} onClick={() => setActiveTab('as_borrower')}>As Borrower</button>
          <button className={`tab-btn ${activeTab === 'as_lender' ? 'active' : ''}`} onClick={() => setActiveTab('as_lender')}>As Lender</button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading your borrow requests...</div>
      ) : filteredRequests.length > 0 ? (
        <div className="dashboard-grid">
          {filteredRequests.map(request => (
            <Link key={request.id} to={`/borrow-requests/${request.id}`} className="dashboard-card glass card-link">
              <div className="card-header">
                <div className={`status-badge ${request.status}`}>
                  {request.status}
                </div>
                <div className="status-badge handover-badge">
                  {request.handover_status || 'not_applicable'}
                </div>
              </div>

              <div className="card-body">
                <h3>{request.title}</h3>
                <span className="card-category">{request.category}</span>
                <div className="card-price">₹{request.max_price_per_day || request.price_per_day} / day</div>
              </div>

              <div className="card-footer">
                <div className="stat">
                  <span className="stat-val">{request.borrower_name || 'Unknown'}</span>
                  <span className="stat-label">Borrower</span>
                </div>
                <div className="stat">
                  <span className="stat-val">{request.lender_id ? 'Lender' : 'Open'}</span>
                  <span className="stat-label">{request.lender_id ? 'Matched' : 'Waiting'}</span>
                </div>
              </div>
              <div className="card-action-hint">
                <ArrowRight size={16} /> Click to view details
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="empty-state glass">
          <div className="empty-icon-wrapper">
            <Plus size={48} />
          </div>
          <h3>No borrow requests yet</h3>
          <p>Start a conversation and make an offer to create a rental request.</p>
          <Link to="/browse" className="btn-primary mt-4">Browse Items</Link>
        </div>
      )}
    </div>
  );
};

export default MyBorrowRequests;
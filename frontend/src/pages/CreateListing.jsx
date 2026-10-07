import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, CheckCircle2, Sparkles, MapPin, Search } from 'lucide-react';
import api from '../api/client';
import './CreateListing.css';

const CATEGORIES = ['Tools', 'Electronics', 'Sports', 'Party', 'Books', 'Other'];

const CreateListing = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [aiOffline, setAiOffline] = useState(false);
  const fileInputRef = useRef(null);

  // Form State
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [uploadedUrl, setUploadedUrl] = useState(null);
  
  const [formData, setFormData] = useState({
    title: '',
    category: 'Other',
    description: '',
    years_owned: 1,
    original_price: '',
    price_per_day: '',
    security_deposit: '',
    lat: 28.6139,
    lon: 77.2090,
    address: '',
    lending_radius: 5
  });

  // Step 1: Handle File
  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (selectedFile) => {
    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setIsLoading(true);
    setAiOffline(false);

    try {
      const form = new FormData();
      form.append('file', selectedFile);
      
      const uploadRes = await api.post('/upload', form, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      const data = uploadRes.data;
      
      setUploadedUrl(data.url);
      
      if (data.ai_label) {
        setAiData({ 
          label: data.ai_label, 
          confidence: (data.ai_confidence * 100).toFixed(0), 
          suggested_category: 'Other' 
        });
        setFormData(prev => ({
          ...prev,
          title: data.ai_label
        }));
      } else {
        setAiData(null);
      }
    } catch (err) {
      console.error(err);
      setAiOffline(true);
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Handle Details
  const handleGetPriceSuggestion = async () => {
    setIsLoading(true);
    try {
      // Mock API Suggest Price
      await new Promise(r => setTimeout(r, 1000));
      setFormData(prev => ({ ...prev, price_per_day: 150, security_deposit: 1000 }));
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Step 3: Location & Submit
  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setFormData(prev => ({
          ...prev,
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          address: 'Current Location'
        }));
      });
    }
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      const payload = {
        name: formData.title,
        category: formData.category,
        description: formData.description,
        years_owned: Number(formData.years_owned),
        price_bought: Number(formData.original_price),
        price_per_day: Number(formData.price_per_day),
        security_deposit: Number(formData.security_deposit),
        lending_radius_km: Number(formData.lending_radius),
        latitude: formData.lat ? Number(formData.lat) : null,
        longitude: formData.lon ? Number(formData.lon) : null,
        address_text: formData.address,
        ai_label: aiData?.label || null,
        ai_confidence: aiData ? Number(aiData.confidence) / 100.0 : null,
        photo_urls: uploadedUrl ? [uploadedUrl] : []
      };

      await api.post('/listings', payload);
      navigate('/my-listings');
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="create-listing-page container fade-in-up">
      <div className="wizard-container glass">
        
        {/* Progress Tracker */}
        <div className="wizard-progress">
          <div className={`step-indicator ${step >= 1 ? 'active' : ''}`}>1. AI Scan</div>
          <div className="step-line"></div>
          <div className={`step-indicator ${step >= 2 ? 'active' : ''}`}>2. Details</div>
          <div className="step-line"></div>
          <div className={`step-indicator ${step >= 3 ? 'active' : ''}`}>3. Publish</div>
        </div>

        {/* Step 1: AI Scan */}
        {step === 1 && (
          <div className="wizard-step">
            <h2>Identify your item</h2>
            <p className="text-muted">Upload a photo and our AI will do the heavy lifting.</p>
            
            <div 
              className={`dropzone ${preview ? 'has-image' : ''}`}
              onDragOver={e => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => !preview && fileInputRef.current?.click()}
            >
              <input type="file" ref={fileInputRef} onChange={handleFileSelect} hidden accept="image/*" />
              
              {preview ? (
                <div className="preview-container">
                  <img src={preview} alt="Preview" className="image-preview" />
                  <button className="btn-outline reupload-btn" onClick={(e) => { e.stopPropagation(); setPreview(null); setAiData(null); setFile(null); }}>
                    Use different photo
                  </button>
                </div>
              ) : (
                <div className="dropzone-content">
                  <UploadCloud size={48} className="upload-icon" />
                  <h3>Click or drag photo here</h3>
                  <p>Supports JPG, PNG (Max 5MB)</p>
                </div>
              )}
            </div>

            {isLoading && (
              <div className="ai-loading">
                <Sparkles className="sparkle-icon" />
                <p>AI is analyzing your image...</p>
              </div>
            )}

            {aiData && !isLoading && (
              <div className="ai-result success">
                <CheckCircle2 size={24} />
                <div className="ai-result-text">
                  <h4>AI identified: {aiData.label}</h4>
                  <div className="confidence-bar-bg">
                    <div className="confidence-bar" style={{width: `${aiData.confidence}%`}}></div>
                  </div>
                  <span className="confidence-text">{aiData.confidence}% match</span>
                </div>
              </div>
            )}

            {aiOffline && (
              <div className="ai-result error">
                <p>AI service is currently offline. Please proceed and enter details manually.</p>
              </div>
            )}

            <div className="wizard-actions">
              <button 
                className="btn-primary" 
                onClick={() => setStep(2)}
                disabled={!preview || isLoading}
              >
                Next Step
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Details */}
        {step === 2 && (
          <div className="wizard-step">
            <h2>Item Details</h2>
            <div className="form-grid">
              <div className="form-group full-width">
                <label>Item Name</label>
                <input type="text" name="title" value={formData.title} onChange={handleInputChange} placeholder="e.g. Bosch Power Drill" />
              </div>
              
              <div className="form-group">
                <label>Category</label>
                <select name="category" value={formData.category} onChange={handleInputChange}>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              
              <div className="form-group full-width">
                <label>Description</label>
                <textarea name="description" value={formData.description} onChange={handleInputChange} rows={4} placeholder="Describe the condition, what's included, etc."></textarea>
              </div>

              <div className="form-group">
                <label>Original Purchase Price (₹)</label>
                <input type="number" name="original_price" value={formData.original_price} onChange={handleInputChange} />
              </div>
              <div className="form-group">
                <label>Years Owned</label>
                <input type="number" name="years_owned" value={formData.years_owned} onChange={handleInputChange} />
              </div>

              <div className="form-group full-width price-suggestion-box glass">
                <div className="box-header">
                  <Sparkles size={20} className="text-accent" />
                  <h4>Not sure how to price?</h4>
                </div>
                <button className="btn-outline" onClick={handleGetPriceSuggestion} disabled={isLoading}>
                  {isLoading ? 'Calculating...' : 'Get AI Price Suggestion'}
                </button>
              </div>

              <div className="form-group">
                <label>Price per Day (₹)</label>
                <input type="number" name="price_per_day" value={formData.price_per_day} onChange={handleInputChange} />
              </div>
              <div className="form-group">
                <label>Security Deposit (₹)</label>
                <input type="number" name="security_deposit" value={formData.security_deposit} onChange={handleInputChange} />
              </div>
            </div>

            <div className="wizard-actions">
              <button className="btn-outline" onClick={() => setStep(1)}>Back</button>
              <button className="btn-primary" onClick={() => setStep(3)}>Next Step</button>
            </div>
          </div>
        )}

        {/* Step 3: Location */}
        {step === 3 && (
          <div className="wizard-step">
            <h2>Location & Availability</h2>
            <div className="form-grid">
              
              <div className="form-group full-width">
                <label>Pickup Address</label>
                <div className="input-with-button">
                  <input type="text" name="address" value={formData.address} onChange={handleInputChange} placeholder="Enter block/street name" />
                  <button className="btn-outline icon-btn" onClick={handleGetLocation} title="Use My Location">
                    <MapPin size={20} />
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Latitude</label>
                <input type="text" name="lat" value={formData.lat} onChange={handleInputChange} />
              </div>
              <div className="form-group">
                <label>Longitude</label>
                <input type="text" name="lon" value={formData.lon} onChange={handleInputChange} />
              </div>

              <div className="form-group full-width">
                <label>Lending Radius: {formData.lending_radius} km</label>
                <input 
                  type="range" 
                  name="lending_radius"
                  min="1" max="20" 
                  value={formData.lending_radius} 
                  onChange={handleInputChange}
                  className="full-width-slider"
                />
              </div>

            </div>

            <div className="wizard-actions">
              <button className="btn-outline" onClick={() => setStep(2)}>Back</button>
              <button className="btn-primary publish-btn" onClick={handleSubmit} disabled={isLoading}>
                {isLoading ? <span className="spinner"></span> : 'Publish Listing'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default CreateListing;

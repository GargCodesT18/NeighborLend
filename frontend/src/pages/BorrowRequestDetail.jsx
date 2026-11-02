import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { MessageCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import './BorrowRequestDetail.css';

const HANDOVER_LABELS = {
  pending: 'Awaiting Product Handover',
  marked_given: 'Awaiting Borrower Confirmation',
  confirmed: 'Handover Confirmed',
  issue_reported: 'Issue Reported',
};

const formatDateTime = (value) => value ? new Date(value).toLocaleString() : '—';

const BorrowRequestDetail = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const [request, setRequest] = useState(null);
  const [disputeDescription, setDisputeDescription] = useState('');
  const [issueDescription, setIssueDescription] = useState('');
  const [issueFormOpen, setIssueFormOpen] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchRequest = useCallback(async () => {
    try {
      const response = await api.get(`/borrow-requests/${id}`);
      let nextRequest = response.data;
      const isParticipant = user && [nextRequest.borrower_id, nextRequest.lender_id].includes(user.id);
      if (isParticipant && nextRequest.listing_id && nextRequest.handover_status !== 'not_applicable') {
        const handover = await api.get(`/borrow-requests/${id}/handover`);
        nextRequest = { ...nextRequest, ...handover.data };
      }
      setRequest(nextRequest);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load this borrowing request.');
    } finally {
      setLoading(false);
    }
  }, [id, user?.id]);

  useEffect(() => {
    fetchRequest();
  }, [fetchRequest]);

  useEffect(() => {
    if (!request || !['pending', 'marked_given'].includes(request.handover_status)) return undefined;
    const isParticipant = user && [request.borrower_id, request.lender_id].includes(user.id);
    if (!isParticipant) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const response = await api.get(`/borrow-requests/${id}/handover`);
        setRequest((current) => current ? { ...current, ...response.data } : current);
      } catch {
        // Keep the current request visible if a quiet background refresh fails.
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [id, request?.handover_status, request?.borrower_id, request?.lender_id, user?.id]);

  const runHandoverAction = async (action, confirmMessage) => {
    if (!window.confirm(confirmMessage)) return;
    setSubmitting(true);
    setError('');
    try {
      await api.post(`/borrow-requests/${id}/handover/${action}`);
      await fetchRequest();
      window.dispatchEvent(new Event('notifications:updated'));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update the handover.');
    } finally {
      setSubmitting(false);
    }
  };

  const reportHandoverIssue = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.post(`/borrow-requests/${id}/handover/report-issue`, { description: issueDescription });
      setIssueDescription('');
      setIssueFormOpen(false);
      await fetchRequest();
      window.dispatchEvent(new Event('notifications:updated'));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not report the handover issue.');
    } finally {
      setSubmitting(false);
    }
  };

  const reportReturn = async () => {
    setSubmitting(true);
    setError('');
    try {
      await api.post(`/borrow-requests/${id}/return`);
      await fetchRequest();
      window.dispatchEvent(new Event('notifications:updated'));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not report the return.');
    } finally {
      setSubmitting(false);
    }
  };

  const reportDispute = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.post(`/borrow-requests/${id}/dispute`, { description: disputeDescription });
      setDisputeDescription('');
      await fetchRequest();
      window.dispatchEvent(new Event('notifications:updated'));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not report the dispute.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="rental-detail-loading">Loading request…</div>;
  if (!request) return <div className="rental-detail-loading">{error || 'Request not found.'}</div>;

  const canManageRental = request.listing_id
    && user
    && [request.borrower_id, request.lender_id].includes(user.id);
  const handoverManaged = request.handover_status && request.handover_status !== 'not_applicable';
  const isLender = user?.id === request.lender_id;
  const isBorrower = user?.id === request.borrower_id;
  const canUseReturnActions = canManageRental
    && (!handoverManaged || request.handover_status === 'confirmed');

  return (
    <section className="rental-detail-page container fade-in-up">
      <article className="rental-detail-card glass">
        <span className="rental-category">{request.category}</span>
        <h1>{request.title}</h1>
        <p className="rental-description">{request.description || 'No additional details provided.'}</p>
        <dl>
          <div><dt>Requested by</dt><dd>{request.borrower_name}</dd></div>
          <div><dt>Maximum daily price</dt><dd>{request.max_price_per_day ? `₹${request.max_price_per_day}` : 'Not specified'}</dd></div>
          <div><dt>Agreed from</dt><dd>{request.needed_from ? new Date(request.needed_from).toLocaleDateString() : 'Flexible'}</dd></div>
          <div><dt>Agreed until</dt><dd>{request.needed_until ? new Date(request.needed_until).toLocaleDateString() : 'Flexible'}</dd></div>
        </dl>
        {error && <div className="error-banner" role="alert">{error}</div>}

        {handoverManaged && (
          <div className="rental-lifecycle handover-panel">
            <h2>Product handover</h2>
            <p className={`handover-status status-${request.handover_status}`}>
              {HANDOVER_LABELS[request.handover_status] || request.handover_status}
            </p>
            {request.handover_marked_at && (
              <p className="handover-meta">Marked handed over: {formatDateTime(request.handover_marked_at)}</p>
            )}

            {request.handover_status === 'pending' && isLender && (
              <button
                type="button"
                className="btn-primary"
                disabled={submitting}
                onClick={() => runHandoverAction(
                  'mark-given',
                  'Confirm that you physically handed this product to the borrower. They will be asked to inspect and confirm it.',
                )}
              >
                {submitting ? 'Updating…' : 'Mark as Handed Over'}
              </button>
            )}

            {request.handover_status === 'marked_given' && isBorrower && (
              <div className="handover-actions">
                <p>Inspect the product before confirming its condition.</p>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={submitting}
                  onClick={() => runHandoverAction(
                    'confirm',
                    'Confirm that you physically received the product and it matches the agreed condition. This starts the borrowing period.',
                  )}
                >
                  Received in Good Condition
                </button>
                {!issueFormOpen && (
                  <button type="button" className="btn-outline" disabled={submitting} onClick={() => setIssueFormOpen(true)}>
                    Report an Issue
                  </button>
                )}
                {issueFormOpen && (
                  <form className="handover-issue-form" onSubmit={reportHandoverIssue}>
                    <label htmlFor="handover-issue-description">Describe the issue</label>
                    <textarea
                      id="handover-issue-description"
                      value={issueDescription}
                      onChange={(event) => setIssueDescription(event.target.value)}
                      maxLength={2000}
                      required
                    />
                    <div className="handover-issue-actions">
                      <button type="submit" className="btn-primary" disabled={submitting || !issueDescription.trim()}>
                        {submitting ? 'Submitting…' : 'Submit Issue'}
                      </button>
                      <button type="button" className="btn-outline" disabled={submitting} onClick={() => setIssueFormOpen(false)}>
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}

            {request.handover_status === 'confirmed' && (
              <div className="handover-active-details">
                <p>Confirmed: {formatDateTime(request.handover_confirmed_at)}</p>
                <p>Borrowing started: {formatDateTime(request.borrowing_started_at)}</p>
                <p>Return due: {formatDateTime(request.return_due_at)}</p>
                <p className="handover-active-label">Borrowing is active.</p>
              </div>
            )}

            {request.handover_status === 'issue_reported' && (
              <div className="handover-issue-details">
                <p><strong>Reported:</strong> {formatDateTime(request.handover_issue_reported_at)}</p>
                <p>{request.handover_issue_description}</p>
                <p>Borrowing will not start until the issue is addressed. Use your existing conversation to coordinate with the other party.</p>
                {request.conversation_id && (
                  <Link className="btn-outline handover-chat-link" to={`/messages/${request.conversation_id}`}>
                    <MessageCircle size={16} /> Open conversation
                  </Link>
                )}
              </div>
            )}
          </div>
        )}

        {canUseReturnActions && (
          <div className="rental-lifecycle">
            <h2>Rental status</h2>
            <p>{request.returned_at ? 'Return reported' : 'Return not yet reported'}</p>
            {request.disputed_at && <p>A dispute has been reported for this rental.</p>}
            {!request.returned_at && (
              <button type="button" className="btn-primary" onClick={reportReturn} disabled={submitting}>
                Report item returned
              </button>
            )}
            {!request.disputed_at && (
              <form onSubmit={reportDispute}>
                <label htmlFor="dispute-description">Report a dispute</label>
                <textarea
                  id="dispute-description"
                  value={disputeDescription}
                  onChange={(event) => setDisputeDescription(event.target.value)}
                  maxLength={2000}
                  required
                />
                <button type="submit" className="btn-outline" disabled={submitting}>
                  Submit dispute
                </button>
              </form>
            )}
          </div>
        )}
      </article>
    </section>
  );
};

export default BorrowRequestDetail;

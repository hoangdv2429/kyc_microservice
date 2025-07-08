import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Button,
  Box,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab
} from '@mui/material';
import { adminAPI, utils } from '../services/api';

const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [pendingReviews, setPendingReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reviewDialog, setReviewDialog] = useState(null);
  const [reviewForm, setReviewForm] = useState({
    decision: 'passed',
    note: '',
    approved_tier: 2,
    rejection_reason: ''
  });

  useEffect(() => {
    if (activeTab === 0) {
      loadPendingReviews();
    }
  }, [activeTab]);

  const loadPendingReviews = async () => {
    try {
      setLoading(true);
      setError('');
      const reviews = await adminAPI.getPendingReviews();
      setPendingReviews(reviews);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load pending reviews');
    } finally {
      setLoading(false);
    }
  };

  const openReviewDialog = (review) => {
    setReviewDialog(review);
    setReviewForm({
      decision: 'passed',
      note: '',
      approved_tier: 2,
      rejection_reason: ''
    });
  };

  const closeReviewDialog = () => {
    setReviewDialog(null);
    setReviewForm({
      decision: 'passed',
      note: '',
      approved_tier: 2,
      rejection_reason: ''
    });
  };

  const submitReview = async () => {
    try {
      setLoading(true);
      
      const reviewData = {
        reviewer_id: utils.generateUUID(), // In real app, this would be the admin's user ID
        decision: reviewForm.decision,
        note: reviewForm.note,
        ...(reviewForm.decision === 'passed' ? { approved_tier: reviewForm.approved_tier } : {}),
        ...(reviewForm.decision === 'rejected' ? { rejection_reason: reviewForm.rejection_reason } : {})
      };

      await adminAPI.submitReview(reviewDialog.ticket_id, reviewData);
      
      // Refresh the pending reviews list
      await loadPendingReviews();
      closeReviewDialog();
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = (status) => {
    const config = {
      'pending': { color: 'warning', icon: '⏳' },
      'processing': { color: 'info', icon: '🔄' },
      'manual_review': { color: 'secondary', icon: '👥' }
    };
    
    const { color, icon } = config[status] || { color: 'default', icon: '❓' };
    
    return (
      <Chip
        label={`${icon} ${status.toUpperCase().replace('_', ' ')}`}
        color={color}
        size="small"
      />
    );
  };

  const renderPendingReviews = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">
          👥 Pending Manual Reviews
        </Typography>
        <Button 
          variant="outlined" 
          onClick={loadPendingReviews}
          disabled={loading}
        >
          🔄 Refresh
        </Button>
      </Box>

      {loading && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
          <Typography variant="body2" sx={{ mt: 2 }}>
            Loading pending reviews...
          </Typography>
        </Box>
      )}

      {!loading && pendingReviews.length === 0 && (
        <Alert severity="info">
          No pending reviews at this time. All KYC submissions are either automatically approved/rejected or still being processed.
        </Alert>
      )}

      <Grid container spacing={3}>
        {pendingReviews.map((review) => (
          <Grid item xs={12} md={6} key={review.ticket_id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    {review.full_name || 'Unknown User'}
                  </Typography>
                  {getStatusChip(review.status)}
                </Box>

                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>Ticket ID:</strong> {review.ticket_id}
                </Typography>
                
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>Email:</strong> {review.email || 'N/A'}
                </Typography>
                
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <strong>Submitted:</strong> {utils.formatTimestamp(review.submitted_at)}
                </Typography>

                {/* Quick Image Preview */}
                {(review.doc_front || review.doc_back || review.selfie) && (
                  <Box sx={{ mt: 1, mb: 2 }}>
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      📷 Documents:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {review.doc_front && (
                        <Box
                          component="img"
                          src={review.doc_front}
                          alt="ID Front"
                          sx={{
                            width: 40,
                            height: 30,
                            objectFit: 'cover',
                            borderRadius: 0.5,
                            border: '1px solid #ddd',
                            cursor: 'pointer'
                          }}
                          onClick={() => window.open(review.doc_front, '_blank')}
                          title="ID Document Front - Click to enlarge"
                        />
                      )}
                      {review.doc_back && (
                        <Box
                          component="img"
                          src={review.doc_back}
                          alt="ID Back"
                          sx={{
                            width: 40,
                            height: 30,
                            objectFit: 'cover',
                            borderRadius: 0.5,
                            border: '1px solid #ddd',
                            cursor: 'pointer'
                          }}
                          onClick={() => window.open(review.doc_back, '_blank')}
                          title="ID Document Back - Click to enlarge"
                        />
                      )}
                      {review.selfie && (
                        <Box
                          component="img"
                          src={review.selfie}
                          alt="Selfie"
                          sx={{
                            width: 40,
                            height: 30,
                            objectFit: 'cover',
                            borderRadius: 0.5,
                            border: '1px solid #ddd',
                            cursor: 'pointer'
                          }}
                          onClick={() => window.open(review.selfie, '_blank')}
                          title="Selfie - Click to enlarge"
                        />
                      )}
                    </Box>
                  </Box>
                )}

                {review.risk_score !== null && (
                  <Box sx={{ mt: 2, mb: 2 }}>
                    <Typography variant="body2" color="textSecondary">
                      Risk Score:
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography 
                        variant="h6" 
                        sx={{ 
                          color: review.risk_score >= 0.65 ? '#ff9800' : '#f44336',
                          fontWeight: 'bold'
                        }}
                      >
                        {(review.risk_score * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        (Threshold: 65%)
                      </Typography>
                    </Box>
                  </Box>
                )}

                <Button
                  variant="contained"
                  fullWidth
                  onClick={() => openReviewDialog(review)}
                  sx={{ 
                    mt: 2,
                    background: 'linear-gradient(45deg, #667eea, #764ba2)'
                  }}
                >
                  📝 Review Case
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );

  const renderStats = () => (
    <Box>
      <Typography variant="h5" fontWeight="bold" gutterBottom>
        📊 System Statistics
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary" fontWeight="bold">
                1,234
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Total Submissions
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main" fontWeight="bold">
                94.2%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Approval Rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main" fontWeight="bold">
                {pendingReviews.length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Pending Reviews
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main" fontWeight="bold">
                2.3min
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Avg. Processing Time
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            🔧 System Configuration
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="textSecondary">
                Auto Approval Threshold:
              </Typography>
              <Typography variant="body1" fontWeight="bold">
                85% Risk Score
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="textSecondary">
                Manual Review Threshold:
              </Typography>
              <Typography variant="body1" fontWeight="bold">
                65% Risk Score
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="textSecondary">
                Face Match Threshold:
              </Typography>
              <Typography variant="body1" fontWeight="bold">
                70% Confidence
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="textSecondary">
                Liveness Threshold:
              </Typography>
              <Typography variant="body1" fontWeight="bold">
                80% Confidence
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );

  // Helper to get backend proxy image URL
  const getImageUrl = (ticketId, imageType) => {
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/v1';
    return `${baseUrl}admin/image/${ticketId}/${imageType}`;
  };

  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', textAlign: 'center' }}>
        🛡️ Admin Panel
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="👥 Pending Reviews" />
          <Tab label="📊 Statistics" />
        </Tabs>
      </Box>

      {activeTab === 0 && renderPendingReviews()}
      {activeTab === 1 && renderStats()}

      {/* Review Dialog */}
      <Dialog open={!!reviewDialog} onClose={closeReviewDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          📝 Review KYC Submission
        </DialogTitle>
        <DialogContent>
          {reviewDialog && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {reviewDialog.full_name}
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="textSecondary">
                    Ticket ID: {reviewDialog.ticket_id}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="textSecondary">
                    Email: {reviewDialog.email}
                  </Typography>
                </Grid>
              </Grid>

              {/* Document Images Section */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                  📄 Submitted Documents
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Card sx={{ height: '100%' }}>
                      <CardContent sx={{ textAlign: 'center', p: 1 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          🆔 ID Front
                        </Typography>
                        {reviewDialog.doc_front ? (
                          <Box
                            component="img"
                            src={getImageUrl(reviewDialog.ticket_id, 'doc_front')}
                            alt="ID Document Front"
                            sx={{
                              width: '100%',
                              maxHeight: 200,
                              objectFit: 'contain',
                              border: '1px solid #ddd',
                              borderRadius: 1,
                              cursor: 'pointer'
                            }}
                            onClick={() => window.open(getImageUrl(reviewDialog.ticket_id, 'doc_front'), '_blank')}
                          />
                        ) : (
                          <Box
                            sx={{
                              height: 150,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              bgcolor: '#f5f5f5',
                              borderRadius: 1
                            }}
                          >
                            <Typography variant="body2" color="textSecondary">
                              No image available
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} md={4}>
                    <Card sx={{ height: '100%' }}>
                      <CardContent sx={{ textAlign: 'center', p: 1 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          🆔 ID Back
                        </Typography>
                        {reviewDialog.doc_back ? (
                          <Box
                            component="img"
                            src={getImageUrl(reviewDialog.ticket_id, 'doc_back')}
                            alt="ID Document Back"
                            sx={{
                              width: '100%',
                              maxHeight: 200,
                              objectFit: 'contain',
                              border: '1px solid #ddd',
                              borderRadius: 1,
                              cursor: 'pointer'
                            }}
                            onClick={() => window.open(getImageUrl(reviewDialog.ticket_id, 'doc_back'), '_blank')}
                          />
                        ) : (
                          <Box
                            sx={{
                              height: 150,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              bgcolor: '#f5f5f5',
                              borderRadius: 1
                            }}
                          >
                            <Typography variant="body2" color="textSecondary">
                              No image available
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} md={4}>
                    <Card sx={{ height: '100%' }}>
                      <CardContent sx={{ textAlign: 'center', p: 1 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          🤳 Selfie
                        </Typography>
                        {reviewDialog.selfie ? (
                          <Box
                            component="img"
                            src={getImageUrl(reviewDialog.ticket_id, 'selfie')}
                            alt="Selfie"
                            sx={{
                              width: '100%',
                              maxHeight: 200,
                              objectFit: 'contain',
                              border: '1px solid #ddd',
                              borderRadius: 1,
                              cursor: 'pointer'
                            }}
                            onClick={() => window.open(getImageUrl(reviewDialog.ticket_id, 'selfie'), '_blank')}
                          />
                        ) : (
                          <Box
                            sx={{
                              height: 150,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              bgcolor: '#f5f5f5',
                              borderRadius: 1
                            }}
                          >
                            <Typography variant="body2" color="textSecondary">
                              No image available
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>

                {/* Verification Metrics */}
                {(reviewDialog.face_score !== null || reviewDialog.liveness_score !== null || reviewDialog.risk_score !== null) && (
                  <Box sx={{ mt: 2, p: 2, bgcolor: '#f8f9fa', borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      📊 Verification Metrics
                    </Typography>
                    <Grid container spacing={2}>
                      {reviewDialog.face_score !== null && (
                        <Grid item xs={4}>
                          <Typography variant="body2" color="textSecondary">Face Match:</Typography>
                          <Typography 
                            variant="body1" 
                            fontWeight="bold"
                            sx={{ color: reviewDialog.face_score >= 0.7 ? '#4caf50' : '#f44336' }}
                          >
                            {(reviewDialog.face_score * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                      )}
                      {reviewDialog.liveness_score !== null && (
                        <Grid item xs={4}>
                          <Typography variant="body2" color="textSecondary">Liveness:</Typography>
                          <Typography 
                            variant="body1" 
                            fontWeight="bold"
                            sx={{ color: reviewDialog.liveness_score >= 0.8 ? '#4caf50' : '#f44336' }}
                          >
                            {(reviewDialog.liveness_score * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                      )}
                      {reviewDialog.risk_score !== null && (
                        <Grid item xs={4}>
                          <Typography variant="body2" color="textSecondary">Risk Score:</Typography>
                          <Typography 
                            variant="body1" 
                            fontWeight="bold"
                            sx={{ color: reviewDialog.risk_score <= 0.65 ? '#4caf50' : '#f44336' }}
                          >
                            {(reviewDialog.risk_score * 100).toFixed(1)}%
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </Box>
                )}
              </Box>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Decision</InputLabel>
                <Select
                  value={reviewForm.decision}
                  onChange={(e) => setReviewForm({ ...reviewForm, decision: e.target.value })}
                  label="Decision"
                >
                  <MenuItem value="passed">✅ Approve</MenuItem>
                  <MenuItem value="rejected">❌ Reject</MenuItem>
                </Select>
              </FormControl>

              {reviewForm.decision === 'passed' && (
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Approved Tier</InputLabel>
                  <Select
                    value={reviewForm.approved_tier}
                    onChange={(e) => setReviewForm({ ...reviewForm, approved_tier: e.target.value })}
                    label="Approved Tier"
                  >
                    <MenuItem value={1}>Tier 1 - Basic</MenuItem>
                    <MenuItem value={2}>Tier 2 - Enhanced</MenuItem>
                  </Select>
                </FormControl>
              )}

              {reviewForm.decision === 'rejected' && (
                <TextField
                  fullWidth
                  label="Rejection Reason"
                  value={reviewForm.rejection_reason}
                  onChange={(e) => setReviewForm({ ...reviewForm, rejection_reason: e.target.value })}
                  multiline
                  rows={2}
                  sx={{ mb: 2 }}
                  required
                />
              )}

              <TextField
                fullWidth
                label="Review Notes"
                value={reviewForm.note}
                onChange={(e) => setReviewForm({ ...reviewForm, note: e.target.value })}
                multiline
                rows={3}
                placeholder="Add any additional notes about this review..."
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeReviewDialog}>
            Cancel
          </Button>
          <Button 
            variant="contained" 
            onClick={submitReview}
            disabled={loading || (reviewForm.decision === 'rejected' && !reviewForm.rejection_reason)}
            sx={{ background: 'linear-gradient(45deg, #667eea, #764ba2)' }}
          >
            {loading ? <CircularProgress size={24} /> : 'Submit Review'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default AdminPanel;

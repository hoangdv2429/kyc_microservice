import React, { useState } from 'react';
import {
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  LinearProgress
} from '@mui/material';
import { kycAPI, utils } from '../services/api';

const StatusChecker = () => {
  const [ticketId, setTicketId] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);

  const checkStatus = async () => {
    if (!ticketId.trim()) {
      setError('Please enter a ticket ID');
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      const result = await kycAPI.getStatus(ticketId.trim());
      setStatus(result);
      
      // Auto-refresh for pending/processing status
      if (result.status === 'pending' || result.status === 'processing') {
        setAutoRefresh(true);
        setTimeout(() => {
          if (autoRefresh) {
            checkStatus();
          }
        }, 5000); // Refresh every 5 seconds
      } else {
        setAutoRefresh(false);
      }
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch status');
      setStatus(null);
      setAutoRefresh(false);
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = (statusValue) => {
    const statusConfig = {
      'pending': { color: 'warning', icon: '⏳' },
      'processing': { color: 'info', icon: '🔄' },
      'approved': { color: 'success', icon: '✅' },
      'rejected': { color: 'error', icon: '❌' },
      'manual_review': { color: 'secondary', icon: '👥' }
    };

    const config = statusConfig[statusValue] || { color: 'default', icon: '❓' };
    
    return (
      <Chip
        label={`${config.icon} ${statusValue.toUpperCase().replace('_', ' ')}`}
        color={config.color}
        size="large"
        sx={{ fontSize: '1.1rem', py: 2, px: 1 }}
      />
    );
  };

  const getProgressValue = (statusValue) => {
    const progressMap = {
      'pending': 25,
      'processing': 50,
      'manual_review': 75,
      'approved': 100,
      'rejected': 100
    };
    return progressMap[statusValue] || 0;
  };

  const renderMetrics = () => {
    if (!status) return null;

    const metrics = [
      { label: 'OCR Confidence', value: status.ocr_json?.confidence, unit: '%', threshold: 50 },
      { label: 'Face Match Score', value: status.face_score, unit: '%', threshold: 70 },
      { label: 'Liveness Score', value: status.liveness_score, unit: '%', threshold: 80 },
      { label: 'Risk Score', value: status.risk_score, unit: '%', threshold: 60 }
    ];

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            📊 Verification Metrics
          </Typography>
          <Grid container spacing={2}>
            {metrics.map((metric, index) => (
              metric.value !== null && metric.value !== undefined && (
                <Grid item xs={12} sm={6} key={index}>
                  <Box sx={{ 
                    p: 2, 
                    backgroundColor: '#f5f5f5', 
                    borderRadius: 2,
                    border: metric.value >= metric.threshold ? '2px solid #4caf50' : '2px solid #ff9800'
                  }}>
                    <Typography variant="body2" color="textSecondary">
                      {metric.label}
                    </Typography>
                    <Typography variant="h6" sx={{ 
                      color: metric.value >= metric.threshold ? '#4caf50' : '#ff9800',
                      fontWeight: 'bold'
                    }}>
                      {(metric.value * 100).toFixed(1)}{metric.unit}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Threshold: {metric.threshold}%
                    </Typography>
                  </Box>
                </Grid>
              )
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderOCRData = () => {
    if (!status?.ocr_json?.extracted_data) return null;

    const ocrData = status.ocr_json.extracted_data;

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            📄 Extracted Document Data
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(ocrData).map(([key, value]) => (
              <Grid item xs={12} sm={6} key={key}>
                <Box sx={{ p: 1 }}>
                  <Typography variant="body2" color="textSecondary" sx={{ textTransform: 'capitalize' }}>
                    {key.replace(/_/g, ' ')}:
                  </Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {value || 'N/A'}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderAdditionalInfo = () => {
    if (!status) return null;

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ℹ️ Additional Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="textSecondary">
                Submitted At:
              </Typography>
              <Typography variant="body1">
                {status.submitted_at ? utils.formatTimestamp(status.submitted_at) : 'N/A'}
              </Typography>
            </Grid>
            
            {status.reviewed_at && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="textSecondary">
                  Reviewed At:
                </Typography>
                <Typography variant="body1">
                  {utils.formatTimestamp(status.reviewed_at)}
                </Typography>
              </Grid>
            )}
            
            {status.approved_tier && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="textSecondary">
                  Approved Tier:
                </Typography>
                <Typography variant="body1" fontWeight="bold" color="primary">
                  Tier {status.approved_tier}
                </Typography>
              </Grid>
            )}
            
            {status.note && (
              <Grid item xs={12}>
                <Typography variant="body2" color="textSecondary">
                  Review Note:
                </Typography>
                <Typography variant="body1">
                  {status.note}
                </Typography>
              </Grid>
            )}
            
            {status.rejection_reason && (
              <Grid item xs={12}>
                <Typography variant="body2" color="textSecondary">
                  Rejection Reason:
                </Typography>
                <Typography variant="body1" color="error">
                  {status.rejection_reason}
                </Typography>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  return (
    <Paper sx={{ p: 4, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', textAlign: 'center' }}>
        🔍 KYC Status Checker
      </Typography>

      <Typography variant="body1" paragraph sx={{ textAlign: 'center', color: '#666' }}>
        Enter your ticket ID to check the status of your KYC verification
      </Typography>

      <Box sx={{ mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={8}>
            <TextField
              fullWidth
              label="Ticket ID"
              value={ticketId}
              onChange={(e) => setTicketId(e.target.value)}
              placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000"
              onKeyPress={(e) => e.key === 'Enter' && checkStatus()}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <Button
              fullWidth
              variant="contained"
              onClick={checkStatus}
              disabled={loading}
              sx={{ 
                height: 56,
                background: 'linear-gradient(45deg, #667eea, #764ba2)',
                '&:hover': { background: 'linear-gradient(45deg, #5a6fd8, #6a4190)' }
              }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : '🔍 Check Status'}
            </Button>
          </Grid>
        </Grid>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {autoRefresh && (
        <Alert severity="info" sx={{ mb: 3 }}>
          🔄 Auto-refreshing every 5 seconds... Click "Check Status" again to stop.
        </Alert>
      )}

      {status && (
        <Box>
          {/* Main Status Card */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom>
                Current Status
              </Typography>
              {getStatusChip(status.status)}
              
              <Box sx={{ mt: 3, mb: 2 }}>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Progress
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={getProgressValue(status.status)}
                  sx={{ 
                    height: 8, 
                    borderRadius: 4,
                    backgroundColor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': {
                      background: 'linear-gradient(45deg, #667eea, #764ba2)'
                    }
                  }}
                />
                <Typography variant="caption" color="textSecondary">
                  {getProgressValue(status.status)}% Complete
                </Typography>
              </Box>

              {status.status === 'pending' && (
                <Typography variant="body2" color="textSecondary">
                  Your KYC is queued for processing. This usually takes 1-5 minutes.
                </Typography>
              )}
              
              {status.status === 'processing' && (
                <Typography variant="body2" color="textSecondary">
                  AI verification in progress. Analyzing documents and biometric data.
                </Typography>
              )}
              
              {status.status === 'manual_review' && (
                <Typography variant="body2" color="textSecondary">
                  Your case requires human review. This typically takes 1-3 business days.
                </Typography>
              )}
              
              {status.status === 'approved' && (
                <Typography variant="body2" color="success.main">
                  🎉 Congratulations! Your KYC has been approved.
                </Typography>
              )}
              
              {status.status === 'rejected' && (
                <Typography variant="body2" color="error.main">
                  Your KYC was not approved. Please see the details below.
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Metrics */}
          {renderMetrics()}

          {/* OCR Data */}
          {renderOCRData()}

          {/* Additional Info */}
          {renderAdditionalInfo()}
        </Box>
      )}

      {/* Sample Ticket IDs for Testing */}
      <Card sx={{ mt: 4, p: 2, backgroundColor: '#f5f5f5' }}>
        <Typography variant="h6" gutterBottom>
          🧪 Testing
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          For testing purposes, you can use these sample ticket IDs or submit a new KYC to get a real ticket ID:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button 
            size="small" 
            variant="outlined"
            onClick={() => setTicketId('b40ad8f4-b2c4-430b-afe9-ae24e8e1bb06')}
          >
            Sample ID 1
          </Button>
          <Button 
            size="small" 
            variant="outlined"
            onClick={() => setTicketId('e8d41cb3-222e-4439-8926-a2c25e9f4026')}
          >
            Sample ID 2
          </Button>
        </Box>
      </Card>
    </Paper>
  );
};

export default StatusChecker;

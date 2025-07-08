import React from 'react';
import { 
  Paper, 
  Typography, 
  Box, 
  Grid, 
  Card, 
  CardContent, 
  Button,
  Chip
} from '@mui/material';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const quickStats = [
    { label: 'Total KYC Submissions', value: '1,234', color: '#2196f3' },
    { label: 'Pending Reviews', value: '23', color: '#ff9800' },
    { label: 'Approved Today', value: '45', color: '#4caf50' },
    { label: 'Success Rate', value: '94.2%', color: '#9c27b0' }
  ];

  const systemStatus = [
    { service: 'API Server', status: 'healthy', uptime: '99.9%' },
    { service: 'Database', status: 'healthy', uptime: '99.8%' },
    { service: 'Redis Cache', status: 'healthy', uptime: '99.9%' },
    { service: 'Worker Queue', status: 'healthy', uptime: '99.7%' },
    { service: 'MinIO Storage', status: 'healthy', uptime: '99.9%' }
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: '#333' }}>
        🏠 KYC System Dashboard
      </Typography>
      
      <Typography variant="body1" paragraph sx={{ color: '#666', mb: 4 }}>
        Welcome to the EchoFi KYC Verification System. Monitor submissions, review pending cases, and manage the verification process.
      </Typography>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {quickStats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ 
              background: `linear-gradient(135deg, ${stat.color}20, ${stat.color}10)`,
              border: `2px solid ${stat.color}30`
            }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ color: stat.color, fontWeight: 'bold' }}>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {stat.label}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Quick Actions */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
          🚀 Quick Actions
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Button 
              variant="contained" 
              fullWidth 
              component={Link} 
              to="/submit"
              sx={{ 
                background: 'linear-gradient(45deg, #667eea, #764ba2)',
                '&:hover': { background: 'linear-gradient(45deg, #5a6fd8, #6a4190)' }
              }}
            >
              📝 Submit New KYC
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button 
              variant="outlined" 
              fullWidth 
              component={Link} 
              to="/status"
              sx={{ borderColor: '#667eea', color: '#667eea' }}
            >
              🔍 Check Status
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button 
              variant="outlined" 
              fullWidth 
              component={Link} 
              to="/admin"
              sx={{ borderColor: '#764ba2', color: '#764ba2' }}
            >
              👥 Admin Panel
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button 
              variant="outlined" 
              fullWidth 
              onClick={() => window.open('http://localhost:8080/docs', '_blank')}
              sx={{ borderColor: '#ff9800', color: '#ff9800' }}
            >
              📚 API Docs
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* System Status */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
          ⚡ System Status
        </Typography>
        <Grid container spacing={2}>
          {systemStatus.map((service, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                p: 2,
                backgroundColor: '#f5f5f5',
                borderRadius: 2
              }}>
                <Box>
                  <Typography variant="body1" fontWeight="bold">
                    {service.service}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Uptime: {service.uptime}
                  </Typography>
                </Box>
                <Chip 
                  label={service.status.toUpperCase()} 
                  color={service.status === 'healthy' ? 'success' : 'error'}
                  size="small"
                />
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Features Overview */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
          🔧 System Features
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                📄 Document Verification
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Advanced OCR processing for ID documents with real-time validation and fraud detection.
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                👤 Biometric Matching
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Face recognition and liveness detection to ensure the person matches their ID document.
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                🔍 Manual Review
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Human oversight for borderline cases with comprehensive admin review workflow.
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default Dashboard;

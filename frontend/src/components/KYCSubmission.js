import React, { useState, useRef } from 'react';
import {
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Grid,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stepper,
  Step,
  StepLabel
} from '@mui/material';
import { kycAPI, fileAPI, utils } from '../services/api';

const KYCSubmission = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [error, setError] = useState('');

  // Form data
  const [formData, setFormData] = useState({
    user_id: utils.generateUUID(),
    full_name: '',
    dob: '',
    address: '',
    email: '',
    phone: '',
    requested_tier: 1
  });

  // File states
  const [files, setFiles] = useState({
    doc_front: null,
    doc_back: null,
    selfie: null
  });

  const [filePreviews, setFilePreviews] = useState({
    doc_front: null,
    doc_back: null,
    selfie: null
  });

  const [uploadedUrls, setUploadedUrls] = useState({
    doc_front_url: '',
    doc_back_url: '',
    selfie_url: ''
  });

  // Camera refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);

  const steps = ['Personal Information', 'Document Upload', 'Selfie Capture', 'Review & Submit'];

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFileUpload = async (type, file) => {
    if (!file) return;

    try {
      setLoading(true);
      
      // Create preview
      const preview = await fileAPI.fileToBase64(file);
      setFilePreviews(prev => ({
        ...prev,
        [type]: preview
      }));

      // Upload file to MinIO
      const uploadResult = await fileAPI.uploadFile(file, type);
      setUploadedUrls(prev => ({
        ...prev,
        [`${type}_url`]: uploadResult.url
      }));

      setFiles(prev => ({
        ...prev,
        [type]: file
      }));

      setError('');
    } catch (err) {
      setError(`Failed to upload ${type}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: 640, 
          height: 480, 
          facingMode: 'user' 
        }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (err) {
      setError('Camera access denied. Please allow camera access or upload a selfie file.');
    }
  };

  const capturePhoto = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (canvas && video) {
      const context = canvas.getContext('2d');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0);
      
      canvas.toBlob(async (blob) => {
        const file = new File([blob], 'selfie.jpg', { type: 'image/jpeg' });
        await handleFileUpload('selfie', file);
        
        // Stop camera
        const stream = video.srcObject;
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
        }
        setCameraActive(false);
      }, 'image/jpeg', 0.8);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError('');

      // Validate required fields
      if (!formData.full_name || !formData.email || !uploadedUrls.doc_front_url || !uploadedUrls.doc_back_url || !uploadedUrls.selfie_url) {
        throw new Error('Please fill all required fields and upload all documents');
      }

      // Prepare submission data
      const submissionData = {
        ...formData,
        ...uploadedUrls
      };

      console.log('Submitting KYC:', submissionData);

      // Submit KYC
      const result = await kycAPI.submitKYC(submissionData);
      setSubmissionResult(result);
      setCurrentStep(4); // Move to success step

    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const renderPersonalInfo = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom>Personal Information</Typography>
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          label="Full Name *"
          value={formData.full_name}
          onChange={(e) => handleInputChange('full_name', e.target.value)}
          placeholder="John Doe"
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          label="Date of Birth"
          type="date"
          value={formData.dob}
          onChange={(e) => handleInputChange('dob', e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          label="Email *"
          type="email"
          value={formData.email}
          onChange={(e) => handleInputChange('email', e.target.value)}
          placeholder="john@example.com"
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          label="Phone"
          value={formData.phone}
          onChange={(e) => handleInputChange('phone', e.target.value)}
          placeholder="+1234567890"
        />
      </Grid>
      <Grid item xs={12}>
        <TextField
          fullWidth
          label="Address"
          multiline
          rows={3}
          value={formData.address}
          onChange={(e) => handleInputChange('address', e.target.value)}
          placeholder="123 Main Street, City, Country"
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <FormControl fullWidth>
          <InputLabel>Requested KYC Tier *</InputLabel>
          <Select
            value={formData.requested_tier}
            onChange={(e) => handleInputChange('requested_tier', e.target.value)}
            label="Requested KYC Tier *"
          >
            <MenuItem value={1}>Tier 1 - Basic Verification</MenuItem>
            <MenuItem value={2}>Tier 2 - Enhanced Verification</MenuItem>
          </Select>
        </FormControl>
      </Grid>
    </Grid>
  );

  const FileUploadArea = ({ type, label, accept = "image/*" }) => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>{label}</Typography>
        <Box
          sx={{
            border: '2px dashed #ccc',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: 'pointer',
            '&:hover': { borderColor: '#667eea', backgroundColor: '#f8f9ff' }
          }}
          onClick={() => document.getElementById(`${type}-upload`).click()}
        >
          <input
            id={`${type}-upload`}
            type="file"
            accept={accept}
            style={{ display: 'none' }}
            onChange={(e) => handleFileUpload(type, e.target.files[0])}
          />
          
          {filePreviews[type] ? (
            <Box>
              <img 
                src={filePreviews[type]} 
                alt={`${type} preview`}
                style={{ maxWidth: '200px', maxHeight: '200px', borderRadius: '8px' }}
              />
              <Typography variant="body2" sx={{ mt: 1 }}>
                ✅ {files[type]?.name}
              </Typography>
            </Box>
          ) : (
            <Box>
              <Typography variant="body1">
                📁 Click to upload {label.toLowerCase()}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Supported: JPG, PNG (Max 10MB)
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );

  const renderDocumentUpload = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom>Document Upload</Typography>
      </Grid>
      <Grid item xs={12} md={6}>
        <FileUploadArea type="doc_front" label="ID Document (Front) *" />
      </Grid>
      <Grid item xs={12} md={6}>
        <FileUploadArea type="doc_back" label="ID Document (Back) *" />
      </Grid>
    </Grid>
  );

  const renderSelfieCapture = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom>Selfie Verification</Typography>
      </Grid>
      <Grid item xs={12}>
        {cameraActive ? (
          <Box sx={{ textAlign: 'center' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              style={{ maxWidth: '100%', borderRadius: '10px', marginBottom: '20px' }}
            />
            <br />
            <Button 
              variant="contained" 
              onClick={capturePhoto}
              sx={{ 
                background: 'linear-gradient(45deg, #667eea, #764ba2)',
                mr: 2
              }}
            >
              📸 Capture Photo
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCameraActive(false)}
            >
              ❌ Cancel
            </Button>
          </Box>
        ) : (
          <Box>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <Button 
                variant="contained" 
                onClick={startCamera}
                sx={{ 
                  background: 'linear-gradient(45deg, #667eea, #764ba2)',
                  mr: 2
                }}
              >
                📷 Start Camera
              </Button>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Or upload a selfie file below
              </Typography>
            </Box>
            <FileUploadArea type="selfie" label="Selfie Photo *" />
          </Box>
        )}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
      </Grid>
    </Grid>
  );

  const renderReview = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom>Review & Submit</Typography>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Personal Information</Typography>
            <Typography><strong>Name:</strong> {formData.full_name}</Typography>
            <Typography><strong>Email:</strong> {formData.email}</Typography>
            <Typography><strong>Phone:</strong> {formData.phone}</Typography>
            <Typography><strong>DOB:</strong> {formData.dob}</Typography>
            <Typography><strong>Tier:</strong> {formData.requested_tier}</Typography>
            <Typography><strong>User ID:</strong> {formData.user_id}</Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Uploaded Documents</Typography>
            <Typography>✅ ID Front: {files.doc_front?.name || 'Uploaded'}</Typography>
            <Typography>✅ ID Back: {files.doc_back?.name || 'Uploaded'}</Typography>
            <Typography>✅ Selfie: {files.selfie?.name || 'Captured'}</Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderSuccess = () => (
    <Box sx={{ textAlign: 'center' }}>
      <Typography variant="h4" gutterBottom sx={{ color: '#4caf50' }}>
        🎉 KYC Submitted Successfully!
      </Typography>
      <Card sx={{ mt: 3, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Ticket ID: {submissionResult?.ticket_id}
        </Typography>
        <Typography variant="body1" paragraph>
          Your KYC verification has been submitted and is being processed. 
          You can check the status using the ticket ID above.
        </Typography>
        <Button 
          variant="contained"
          onClick={() => {
            navigator.clipboard.writeText(submissionResult?.ticket_id);
            alert('Ticket ID copied to clipboard!');
          }}
          sx={{ mr: 2 }}
        >
          📋 Copy Ticket ID
        </Button>
        <Button 
          variant="outlined"
          onClick={() => {
            setCurrentStep(0);
            setSubmissionResult(null);
            setFormData({ ...formData, user_id: utils.generateUUID() });
            setFiles({ doc_front: null, doc_back: null, selfie: null });
            setFilePreviews({ doc_front: null, doc_back: null, selfie: null });
            setUploadedUrls({ doc_front_url: '', doc_back_url: '', selfie_url: '' });
          }}
        >
          🔄 Submit Another
        </Button>
      </Card>
    </Box>
  );

  return (
    <Paper sx={{ p: 4, maxWidth: 1000, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', textAlign: 'center' }}>
        📝 KYC Verification Submission
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {currentStep < 4 && (
        <Stepper activeStep={currentStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      )}

      <Box sx={{ mb: 4 }}>
        {currentStep === 0 && renderPersonalInfo()}
        {currentStep === 1 && renderDocumentUpload()}
        {currentStep === 2 && renderSelfieCapture()}
        {currentStep === 3 && renderReview()}
        {currentStep === 4 && renderSuccess()}
      </Box>

      {currentStep < 4 && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            disabled={currentStep === 0}
            onClick={() => setCurrentStep(currentStep - 1)}
          >
            ← Back
          </Button>
          
          {currentStep === 3 ? (
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading}
              sx={{ background: 'linear-gradient(45deg, #667eea, #764ba2)' }}
            >
              {loading ? <CircularProgress size={24} /> : '🚀 Submit KYC'}
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={() => setCurrentStep(currentStep + 1)}
              disabled={
                (currentStep === 0 && (!formData.full_name || !formData.email)) ||
                (currentStep === 1 && (!uploadedUrls.doc_front_url || !uploadedUrls.doc_back_url)) ||
                (currentStep === 2 && !uploadedUrls.selfie_url)
              }
            >
              Next →
            </Button>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default KYCSubmission;

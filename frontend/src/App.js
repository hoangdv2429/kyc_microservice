import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Container } from '@mui/material';
import KYCSubmission from './components/KYCSubmission';
import StatusChecker from './components/StatusChecker';
import AdminPanel from './components/AdminPanel';
import Dashboard from './components/Dashboard';

function App() {
  return (
    <Router>
      <div className="app-container">
        <AppBar position="static" sx={{ background: 'linear-gradient(45deg, #667eea, #764ba2)' }}>
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              🔐 EchoFi KYC Verification System
            </Typography>
            <Button color="inherit" component={Link} to="/">Dashboard</Button>
            <Button color="inherit" component={Link} to="/submit">Submit KYC</Button>
            <Button color="inherit" component={Link} to="/status">Check Status</Button>
            <Button color="inherit" component={Link} to="/admin">Admin Panel</Button>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/submit" element={<KYCSubmission />} />
            <Route path="/status" element={<StatusChecker />} />
            <Route path="/admin" element={<AdminPanel />} />
          </Routes>
        </Container>
      </div>
    </Router>
  );
}

export default App;

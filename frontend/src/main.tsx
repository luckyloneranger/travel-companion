import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { APIProvider } from '@vis.gl/react-google-maps';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import App from './App';
import './index.css';

const MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

function Root() {
  return (
    <React.StrictMode>
      <ErrorBoundary>
        <BrowserRouter>
          <APIProvider apiKey={MAPS_API_KEY}>
            <App />
          </APIProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </React.StrictMode>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />);

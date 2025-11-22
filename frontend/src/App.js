import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ProductionDashboard from './components/ProductionDashboard';
import FileUploader from './components/FileUploader';
import ProductionCard from './components/ProductionCard';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [productionItems, setProductionItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);

  // Fetch production items on component mount
  useEffect(() => {
    fetchProductionItems();
    fetchStatistics();
  }, []);

  const fetchProductionItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/production-items`);
      setProductionItems(response.data.items || []);
    } catch (err) {
      setError('Failed to fetch production items');
      console.error('Error fetching production items:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/statistics`);
      setStatistics(response.data);
    } catch (err) {
      console.error('Error fetching statistics:', err);
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/export`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `production_data_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Failed to export data');
      console.error('Export error:', err);
    }
  };

  const handleFileUpload = async (file) => {
    setUploadStatus('uploading');
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadStatus('success');
      console.log('Upload successful:', response.data);
      
      // Set AI summary if available
      if (response.data.ai_summary) {
        setAiSummary(response.data.ai_summary);
      }

      // Refresh production items and statistics after successful upload
      setTimeout(() => {
        fetchProductionItems();
        fetchStatistics();
        setUploadStatus(null);
      }, 2000);
    } catch (err) {
      setUploadStatus('error');
      setError('Failed to upload file. Please try again.');
      console.error('Upload error:', err);

      setTimeout(() => {
        setUploadStatus(null);
      }, 3000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-2xl font-bold text-gray-900">
              Production Planning Dashboard
            </h1>
            <div className="flex items-center space-x-4">
              {productionItems.length > 0 && (
                <button
                  onClick={handleExport}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export
                </button>
              )}
              <span className="text-sm text-gray-500">
                {productionItems.length} items
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Section */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Upload Production Sheet</h2>
            <FileUploader
              onUpload={handleFileUpload}
              status={uploadStatus}
            />
            {uploadStatus === 'success' && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-800">
                  File uploaded successfully! Processing data...
                </p>
              </div>
            )}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
            {aiSummary && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h4 className="text-sm font-semibold text-blue-900 mb-1">AI Summary</h4>
                    <p className="text-sm text-blue-800">{aiSummary}</p>
                    <button
                      onClick={() => setAiSummary(null)}
                      className="text-xs text-blue-600 hover:text-blue-800 mt-2"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-4">Statistics</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm font-medium text-gray-500">Total Orders</div>
                <div className="mt-2 text-3xl font-bold text-gray-900">{statistics.total_items}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm font-medium text-gray-500">Avg Quantity</div>
                <div className="mt-2 text-3xl font-bold text-gray-900">{statistics.average_quantity?.toLocaleString()}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm font-medium text-gray-500">Completed</div>
                <div className="mt-2 text-3xl font-bold text-green-600">{statistics.by_status?.completed || 0}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm font-medium text-gray-500">Source Files</div>
                <div className="mt-2 text-3xl font-bold text-gray-900">{Object.keys(statistics.by_source || {}).length}</div>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Section */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Production Overview</h2>
          <ProductionDashboard items={productionItems} />
        </div>

        {/* Production Items Grid */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Production Line Items</h2>
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
            </div>
          ) : productionItems.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {productionItems.map((item) => (
                <ProductionCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No production items yet
              </h3>
              <p className="text-gray-500">
                Upload a production planning sheet to get started
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;

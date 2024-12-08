import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// components
import TextOutput from './components/TextOutput';
import FileUploader from './components/FileUploader';
import NavBar from './components/NavBar';
import Table from './components/Table/Table';

function App() {
  const [userQuery, setUserQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [fileList, setFileList] = useState([]);
  const [chunkText, setChunkText] = useState('');
  const [error, setError] = useState(null);
  const [rawResponse, setRawResponse] = useState(null); // Store the raw response text

  // Fetch the list of files from the backend
  const handleGetFiles = async () => {
    try {
      const response = await axios.get('http://192.168.4.78:8000/files/');
      setFileList(response.data?.files || []);
      console.log('File List:', fileList);
    } catch (err) {
      console.error('Error fetching files:', err);
    }
  };

  // Handle the submission of the user query
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!userQuery.trim()) {
      setError('Please enter a valid query.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Step 1: Fetch similar chunks
      const response = await axios.post('http://192.168.4.78:8000/search/', {
        query: userQuery,
        topk_k: 9,
      });

      console.log('Response from /search/:', response?.data?.results);

      const combinedChunkText = response.data.results
        .map((chunk) => chunk.chunk_text)
        .join('\n');
      setChunkText(combinedChunkText);

      // Step 2: Call the RAG API
      const ragResponse = await axios.post(
        'http://192.168.4.78:8000/rag_api/',
        {
          user_query: userQuery,
          document_chunks: combinedChunkText,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );

      console.log('Response from /rag_api/:', ragResponse.data);

      // Extract the response content
      const responseText = ragResponse?.data?.response?.response?.trim();
      setRawResponse(responseText); // Set the raw response for display

    } catch (err) {
      console.error('Error during query handling:', err.message || err);
      setError('Failed to fetch results. Please check the server logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleGetFiles();
  }, []);

  return (
    <Router>
      <div className="App">
        <div className="layout-container">
          {/* Navbar */}
          <div className="navbar">
            <NavBar />
          </div>
          <Routes>
            <Route
              path="/upload"
              element={
                <div className="main-content">
                  <h2>Upload Documents</h2>
                  <FileUploader />
                </div>
              }
            />
            <Route
              path="/"
              element={
                <div className="main-content">
                  <div className="row">
                    {/* Raw Response Output */}
                    <div className="graph-output">
                      {rawResponse ? (
                        <TextOutput data={rawResponse} />
                      ) : (
                        <p>Output Placeholder</p>
                      )}
                    </div>
                  </div>

                  {/* Input Area at the Bottom */}
                  <div className="input-container">
                    <textarea
                      placeholder="Enter your query"
                      value={userQuery}
                      onChange={(e) => setUserQuery(e.target.value)}
                      rows={5}
                      cols={50}
                      style={{
                        resize: 'both',
                        width: '100%',
                        minHeight: '100px',
                        padding: '10px',
                        borderRadius: '4px',
                        border: '1px solid #ccc',
                      }}
                    />
                    <div className="submit-button-container">
                      <button disabled={loading} type="submit" onClick={handleSubmit}>
                        {loading ? 'Loading...' : 'Submit'}
                      </button>
                    </div>
                  </div>
                  {error && <p style={{ color: 'red' }}>{error}</p>}
                </div>
              }
            />
            <Route
              path="/files"
              element={
                <div className="main-content">
                  <Table fileList={fileList} />
                </div>
              }
            />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;

// src/App.jsx

import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [userQuery, setUserQuery] = useState(''); // State to hold the user query
  const [loading, setLoading] = useState(false);  // State to show loading spinner
  const [result, setResult] = useState('');       // State to store the result
  const [error, setError] = useState(null);       // State to handle any errors

  // Function to handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);  // Show loading spinner
    setError(null);    // Reset error state
    setResult('');     // Clear previous result

    try {
      const response = await axios.post('http://localhost:8000/process_documents/', {
        document_name: 'example.txt',  // Replace with actual document name
        user_query: userQuery,
      });

      setResult(response.data.generated_answer?.response);
    } catch (err) {
      setError('Failed to fetch result from the server');
    } finally {
      setLoading(false);  // Hide loading spinner
    }
  };

  return (
    <div className="App">
      <h1>Document Query System</h1>

      {/* Query Input Form */}
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Enter your query"
          value={userQuery}
          onChange={(e) => setUserQuery(e.target.value)}
          required
        />
        <button type="submit">Submit</button>
      </form>

      {/* Display Loading Spinner */}
      {loading && <div className="loader"></div>}

      {/* Display Result */}
      {result && (
        <div className="result">
          <h2>Answer:</h2>
          <p>{result}</p>
        </div>
      )}

      {/* Display Error Message */}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default App;

// © 2024 Brian Scanlon. All rights reserved.

import { useState } from 'react';
import axios from 'axios';

// styles
import './App.css';

// components
import ForceNodeGraph from './components/ForceNodeGraph';

function App() {
  const [userQuery, setUserQuery] = useState(''); // State to hold the user query
  const [loading, setLoading] = useState(false);  // State to show loading spinner
  const [result, setResult] = useState([]);       // State to store the result as an array of paragraphs
  const [error, setError] = useState(null);       // State to handle any errors

  // Function to handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);  // Show loading spinner
    setError(null);    // Reset error state
    setResult([]);     // Clear previous result

    try {
      const response = await axios.post('http://localhost:8000/process_documents/', {
        document_name: 'example.txt',  // Replace with actual document name
        user_query: userQuery,
      });

      // Format the response into numbered paragraphs
      const formattedResult = response.data.generated_answer?.response
        .split('\n\n') // Split by double newlines (assuming paragraphs are separated by this)
        .map((paragraph, index) => `${paragraph}`); // Add numbering

      setResult(formattedResult);
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
        <button disabled={loading} type="submit">Submit</button>
      </form>

      {/* Display Loading Spinner */}
      {loading && <div className="loader"></div>}

      {/* Display Result */}
      {result.length > 0 && (
        <>
          <div className="result">
            <h2>Answer:</h2>
            {result.map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
          <ForceNodeGraph />
        </>
      )}

      {/* Display Error Message */}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default App;

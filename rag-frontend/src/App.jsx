import { useState } from 'react';
import axios from 'axios';

// styles
import './App.css';

// components
import ForceNodeGraph from './components/ForceNodeGraph';

function App() {
  const [userQuery, setUserQuery] = useState(''); // State to hold the user query
  const [loading, setLoading] = useState(false);  // State to show loading spinner
  const [result, setResult] = useState(null);     // State to store the result
  const [error, setError] = useState(null);       // State to handle any errors

  // Function to handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);  // Show loading spinner
    setError(null);    // Reset error state
    setResult(null);   // Clear previous result

    try {
      const response = await axios.post('http://localhost:8000/process_documents/', {
        user_query: userQuery,
      });

      console.log('Raw Response:', response);

      // Extract the raw response from the model
      let formattedResult = response?.data?.generated_answer?.response;

      // Check if the response is wrapped in backticks and remove them
      if (formattedResult && formattedResult.startsWith('```') && formattedResult.endsWith('```')) {
        formattedResult = formattedResult.slice(3, -3); // Remove the backticks and leading/trailing whitespace
      }

      // Clean up the string for correct formatting and handle any escape sequences
      formattedResult = formattedResult.replace(/\\'/g, "'");  // Fix escaped single quotes
      formattedResult = formattedResult.replace(/\\"/g, '"');  // Fix escaped double quotes
      formattedResult = formattedResult.replace(/\\n/g, '');   // Remove newline escape sequences
      formattedResult = formattedResult.replace(/\\t/g, '');   // Remove tab escape sequences

      console.log('Cleaned Response:', formattedResult);

      // Parse the cleaned-up string into a valid JSON object
      const parsedResult = JSON.parse(formattedResult);

      console.log('Parsed Result:', parsedResult);

      // Ensure the parsed result has both nodes and links (or edges)
      if (parsedResult && parsedResult.nodes && parsedResult.links) {
        setResult(parsedResult);  // Set the parsed result with nodes and links
      } else if (parsedResult && parsedResult.nodes && parsedResult.edges) {
        setResult({ // If edges are used instead of links
          nodes: parsedResult.nodes,
          links: parsedResult.edges, // Remap edges to links for consistency
        });
      } else {
        setError('The response format is incorrect or missing nodes/links.');
      }
    } catch (err) {
      console.error('Error fetching data: ', err);
      setError('Failed to fetch result from the server');
    } finally {
      setLoading(false);  // Hide loading spinner
    }
  };

  return (
    <div className="App">
      <div className="pageLayout">
        {/* Display Result */}
        {result && result.nodes && result.links && (
          <>
            <div className="result">
              <h2>Answer:</h2>
              {/* Pass the result (nodes and links) directly as an object */}
              <ForceNodeGraph data2={result} />
            </div>
          </>
        )}

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

        {/* Display Error Message */}
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  );
}

export default App;

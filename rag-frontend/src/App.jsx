import { useReducer, useState } from 'react';
import axios from 'axios';
import logHelper from './helpers/loglevel'; // Import the log helper

// styles
import './App.css';

// components
import ForceNodeGraph from './components/ForceNodeGraph';

// Reducer for state management
const initialState = {
  userQuery: '',
  loading: false,
  result: null,
  error: null,
};

const reducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: true };
    case 'SET_RESULT':
      return { ...state, result: action.payload, loading: false };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_USER_QUERY':
      return { ...state, userQuery: action.payload };
    default:
      return state;
  }
};

function App() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!state.userQuery.trim()) {
      dispatch({ type: 'SET_ERROR', payload: 'Please enter a valid query.' });
      return;
    }

    dispatch({ type: 'SET_LOADING' });

    try {
      const response = await axios.post('http://localhost:8000/process_documents/', {
        user_query: state.userQuery,
      });

      logHelper.info('Response:', response);

      let formattedResult = response?.data?.generated_answer?.response;

      // Check if the response is wrapped in backticks and remove them
      if (formattedResult && formattedResult.startsWith('```') && formattedResult.endsWith('```')) {
        formattedResult = formattedResult.slice(3, -3); // Remove the backticks and leading/trailing whitespace
      }

      formattedResult = formattedResult.replace(/\\'/g, "'"); // Fix escaped single quotes
      formattedResult = formattedResult.replace(/\\"/g, '"'); // Fix escaped double quotes
      formattedResult = formattedResult.replace(/\\n/g, ''); // Remove newline escape sequences
      formattedResult = formattedResult.replace(/\\t/g, ''); // Remove tab escape sequences

      logHelper.debug('Cleaned Response:', formattedResult);

      // Parse the cleaned-up string into a valid JSON object
      const parsedResult = JSON.parse(formattedResult);

      logHelper.debug('Parsed Result:', parsedResult);

      if (parsedResult && parsedResult.nodes && parsedResult.links) {
        dispatch({ type: 'SET_RESULT', payload: parsedResult });
      } else if (parsedResult && parsedResult.nodes && parsedResult.edges) {
        dispatch({
          type: 'SET_RESULT',
          payload: {
            nodes: parsedResult.nodes,
            links: parsedResult.edges, // Remap edges to links for consistency
          },
        });
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'The response format is incorrect or missing nodes/links.' });
      }
    } catch (err) {
      logHelper.error('Error fetching data: ', err);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to fetch result from the server' });
    }
  };

  return (
    <div className="App">
      <div className="layout-container">
        {/* Navbar */}
        <div className="navbar">
          <p>Navbar</p>
        </div>

        <div className="main-content">
          {/* Graph Output */}
          <div className="graph-output">
            {state.result && state.result.nodes && state.result.links && (
              <>
                <h2>Graph Output:</h2>
                <ForceNodeGraph data2={state.result} />
              </>
            )}
          </div>

          {/* Stream Output */}
          <div className="stream-output">
            <h2>Stream output from LLM response</h2>
            {/* Placeholder content for streaming */}
            <p>Streamed data will appear here.</p>
          </div>
        </div>

        {/* Text input and submit button */}
        <div className="input-container">
          <textarea
            placeholder="Enter your query"
            value={state.userQuery}
            onChange={(e) => dispatch({ type: 'SET_USER_QUERY', payload: e.target.value })}
            required
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
            <button disabled={state.loading} type="submit" onClick={handleSubmit}>
              {state.loading ? 'Loading...' : 'Submit'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

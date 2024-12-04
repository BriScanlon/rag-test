import { useReducer, useState, useEffect } from 'react';
import axios from 'axios';
import logHelper from './helpers/loglevel';
import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// components
import ForceNodeGraph from './components/ForceNodeGraph';
import TextOutput from './components/TextOutput';
import FileUploader from './components/FileUploader';
import NavBar from './components/NavBar';
import { log } from 'loglevel';
import Table from './components/Table/Table';



// Reducer for state management
const initialState = {
  userQuery: '',
  loading: false,
  result: null,
  error: null,
  streamData: '',
  previousResults: '',
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
    case 'SET_STREAM_DATA':
      return { ...state, streamData: action.payload };
      return { ...state, previousResults: state.previousResults + action.payload };
    default:
      return state;
  }
};

function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [streaming, setStreaming] = useState(false);
  const [fileList, setFileList] = useState([]);

  // function to call the list of files from the backend
  const handleGetFiles = async () => {
    try {
      const response = await axios.get('http://192.168.4.78:8000/files/');
      const responseJson = response.data;
      setFileList(responseJson?.files);
      console.log(JSON.stringify(fileList));
    } catch (err) {
      logHelper.error('Error fetching data: ', err);
    }
  }

  // Function to handle the submission of the user query
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!state.userQuery.trim()) {
      dispatch({ type: 'SET_ERROR', payload: 'Please enter a valid query.' });
      return;
    }

    dispatch({ type: 'SET_LOADING' });

    try {
      // Call the backend API to process the document query
      const response = await axios.post('http://192.168.4.78:8000/process_documents/', {
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

      // Map node IDs to actual IDs and prepare the links
      if (parsedResult && parsedResult.nodes && parsedResult.links) {
        const nodesMap = new Map();
        parsedResult.nodes.forEach(node => {
          nodesMap.set(node.id, node);
        });

        // Map links to the actual node names
        const links = parsedResult.links.map(link => {
          return {
            source: nodesMap.get(link.source_id)?.name,
            target: nodesMap.get(link.target_id)?.name,
            relation: link.relation,
          };
        });

        dispatch({ type: 'SET_RESULT', payload: { nodes: parsedResult.nodes, links } });
        // Append the non-streaming result to the previous results
        dispatch({ type: 'APPEND_TO_RESULTS', payload: formattedResult });
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'The response format is incorrect or missing nodes/links.' });
      }

      // Start the streaming of the response data for TextOutput
      // handleStream();  // Call the stream handler to start receiving real-time data
    } catch (err) {
      logHelper.error('Error fetching data: ', err);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to fetch result from the server' });
    }
  };

  // Function to handle the streaming of data from the FastAPI using fetch
  const handleStream = async () => {
    try {
      // Start streaming by setting streaming status to true
      setStreaming(true);

      const response = await fetch('http://192.168.4.78:8000/stream_text_output/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_query: state.userQuery }),
      });

      if (!response.body) {
        throw new Error('No response body received.');
      }

      const reader = response.body.getReader();  // Get the reader from the stream
      const decoder = new TextDecoder();
      let done = false;
      let chunk = '';

      // Read the stream and update the state
      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        chunk += decoder.decode(value, { stream: true });

        // Dispatch the updated stream data
        dispatch({ type: 'SET_STREAM_DATA', payload: chunk });
      }

      // Stop streaming when done
      setStreaming(false);
    } catch (err) {
      console.error('Error with streaming data', err);
      setStreaming(false); // Ensure streaming is stopped if there is an error
    }
  };

  useEffect(() => {
    handleGetFiles();
  }, [])

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
                  {/* Row for Graph Output and Stream Output */}
                  <div className="row">
                    {/* Graph Output */}
                    <div className="graph-output">
                      {state.result && state.result.nodes && state.result.links ? (
                        <ForceNodeGraph data2={state.result} />
                      ) : (
                        <p>Graph Output Placeholder</p>
                      )}
                    </div>

                    {/* Stream Output */}
                    <div className="stream-output">
                      <TextOutput data={state.result ? JSON.stringify(state.result) : "Stream output placeholder"} />
                    </div>
                  </div>

                  {/* Input Area at the Bottom */}
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
                      <button
                        disabled={state.loading}
                        type="submit"
                        onClick={handleSubmit}
                      >
                        {state.loading ? 'Loading...' : 'Submit'}
                      </button>
                    </div>
                  </div>
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

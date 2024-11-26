import React, { useEffect, useState } from 'react';
import './TextOutput.css';  // Import the corresponding CSS file for styling

// Component to display text output in real-time (streaming)
const TextOutput = ({ data }) => {
  const [content, setContent] = useState('');

  // Watch for changes in streamData and update the content state
  useEffect(() => {
    if (data) {
      setContent((prevContent) => prevContent + data); // Append new stream data
    }
  }, [data]); // Only rerun when `data` changes

  return (
    <div className="text-output-container">
      <h2>Stream Output from LLM Response</h2>
      <div className="text-output-box">
        {/* Display streamed content */}
        <p>{content}</p>
      </div>
    </div>
  );
};

export default TextOutput;

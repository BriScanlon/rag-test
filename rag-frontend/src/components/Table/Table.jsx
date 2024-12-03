import React from 'react';
import './Table.css';

const Table = ({ fileList }) => {
    // Function to handle processing a document
    const processDocument = async (fileUrl) => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000); // 15-second timeout

        try {
            const response = await fetch('http://127.0.0.1:8000/document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_url: fileUrl }),
                signal: controller.signal,
            });

            clearTimeout(timeout);

            if (!response.ok) {
                const errorData = await response.json();
                alert(`Error processing document: ${errorData.detail}`);
                return;
            }

            const result = await response.json();
            alert(`Success! Processed document saved at: ${result.processed_file_path}`);
        } catch (error) {
            clearTimeout(timeout);

            if (error.name === 'AbortError') {
                alert('Request timed out. Please try again.');
            } else {
                console.error('Error processing document:', error);
                alert('An error occurred while processing the document.');
            }
        }
    };


    return (
        <div className="file-table-container">
            <table className="file-table">
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>File Link</th>
                    </tr>
                </thead>
                <tbody>
                    {fileList.map((file, index) => (
                        <tr key={index}>
                            <td>{file?.filename}</td>
                            <td><a href={file?.hdfs_path}>Download file</a></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default Table;

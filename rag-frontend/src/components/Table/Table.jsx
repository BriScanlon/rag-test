import React from 'react';
import './Table.css';

const Table = ({ fileList }) => {
    // Function to handle processing a document
    const processDocument = async (fileUrl) => {
        try {
            const response = await fetch('http://127.0.0.1:8000/document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_url: fileUrl }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                alert(`Error processing document: ${errorData.detail}`);
                return;
            }

            const result = await response.json();
            alert(`Success! Processed document saved at: ${result.processed_file_path}`);
        } catch (error) {
            console.error('Error processing document:', error);
            alert('An error occurred while processing the document.');
        }
    };

    return (
        <div className="file-table-container">
            <table className="file-table">
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>File Link</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {fileList.map((file, index) => (
                        <tr key={index}>
                            <td>{file?.filename}</td>
                            <td><a href={file?.hdfs_path}>Download file</a></td>
                            <td>
                                <button
                                    className='process-button'
                                    onClick={() => processDocument(file.hdfs_path)}
                                >
                                    Process Document
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default Table;

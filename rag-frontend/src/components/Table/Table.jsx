import React from 'react';

// styles
import './Table.css';


/**
 * Table Component
 * Displays a list of files in a table format with a "Process Document" button for each file.
 * 
 * @param {Array} fileList - An array of file objects containing file details such as filename.
 * @returns {JSX.Element} A table displaying the file list with action buttons.
 */
const Table = ({ fileList }) => {
    return (
        <div className="file-table-container">
            <table className="file-table">
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {fileList.map((file, index) => (
                        <tr key={index}>
                            <td>{file.filename}</td>
                            <td>
                                <button className='process-button' onClick={() => alert(`Process ${file.filename}`)}>
                                    Process Document
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

export default Table;
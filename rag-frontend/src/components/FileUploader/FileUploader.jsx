import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const FileUploader = () => {
    const [uploadError, setUploadError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const onDrop = (acceptedFiles) => {
        setUploadError('');
        setSuccessMessage('');
        
        acceptedFiles.forEach(async (file) => {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await axios.post('http://localhost:8000/document', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
                setSuccessMessage(response.data.status);
            } catch (error) {
                if (error.response && error.response.data.detail === 'File already exists') {
                    setUploadError('File already exists.');
                } else {
                    setUploadError('Failed to upload the file.');
                }
            }
        });
    };

    const { getRootProps, getInputProps } = useDropzone({
        onDrop,
        accept: '.pdf, .docx',
    });

    return (
        <div {...getRootProps()} style={{ border: '2px dashed gray', padding: '20px', textAlign: 'center' }}>
            <input {...getInputProps()} />
            <p>Click to select files</p>
            {uploadError && <p style={{ color: 'red' }}>{uploadError}</p>}
            {successMessage && <p style={{ color: 'green' }}>{successMessage}</p>}
        </div>
    );
};

export default FileUploader;

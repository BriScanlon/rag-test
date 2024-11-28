from hdfs import InsecureClient

# Initialize HDFS client
hdfs_client = InsecureClient("http://192.168.4.218:9870", user="hadoop")

try:
    # Define HDFS path for the test file
    hdfs_path = "/uploads/test.txt"
    
    # Create content to upload
    test_content = b"Hello, HDFS! This is a test file."
    
    # Upload the content to HDFS
    with hdfs_client.write(hdfs_path, overwrite=True, replication=1) as writer:
        writer.write(test_content)
    
    print(f"File uploaded successfully to {hdfs_path}")
    
    # Verify the upload by listing the contents of the '/uploads' directory
    uploads_status = hdfs_client.list("/uploads", status=True)
    print("Uploads Directory Status After Upload:")
    for file_name, file_status in uploads_status:
        print(f"File Name: {file_name}, Status: {file_status}")

except Exception as e:
    print(f"Error uploading file: {e}")

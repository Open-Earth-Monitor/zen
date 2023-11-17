from zen.dataset import Dataset, Deposition, Zenodo

# Define the Zenodo access token
access_token = 'YOUR_ZENODO_ACCESS_TOKEN'  # Replace with your actual access token

# Create a new dataset associated with a new deposition
dataset = Dataset('dataset.json', url=Zenodo.sandbox, token=access_token)

# Add local files to the dataset
local_file_paths = ['file1.txt', 'file2.txt']
dataset.files.from_files(local_file_paths)
dataset.files.update_metadata()

# Update the dataset metadata
dataset.save()

# Access the deposition and its files directly
print(f'Deposition ID: {dataset.deposition.id}')
print(f'Files: {dataset.files.data}')

# Upload the local files to the Zenodo deposition
dataset.files.upload()

# Update the deposition metadata
dataset.deposition.update(metadata)

# Update the dataset metadata after the files are uploaded
dataset.save()

# Access the deposition after the files are uploaded
deposition_after_upload = zenodo.depositions.get(dataset.deposition.id)
print(f'Deposition ID after upload: {deposition_after_upload.id}')
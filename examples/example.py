# To create your personal token
# Please, go to to https://zenodo.org or https://sandbox.zenodo.org
my_token = 'your_api_token'

## step 1 - create a local dataset

from zen import LocalFiles
ds = LocalFiles(['examples/file1.csv', 'examples/file2.csv'])
ds.save('examples/dataset.json')
print([f.url for f in ds])

## step 2 - bind a deposition to the local dataset

from zen import Zenodo
dep = ds.get_deposition(url=Zenodo.sandbox_url, token=my_token)
dep.metadata.upload_type = 'dataset'
dep.metadata.title = 'Example dataset'
dep.metadata.description = 'Files from index {index_min} to {index_max}.'
dep.update(replacements={'index_min': 1, 'index_max': 3})

## step 3 - upload and publish your data to zenodo

from zen import LocalFiles, Zenodo
ds = LocalFiles.from_file('examples/dataset.json')
dep = ds.get_deposition(url=Zenodo.sandbox_url, token=my_token)
ds.upload(dep)
dep.publish()

## step 4 - updating your data

ds = LocalFiles.from_file('examples/dataset.json')
ds.add(['examples/file3.csv'])
dep = ds.get_deposition(url=Zenodo.sandbox_url, token=my_token)
dep.new_version()
ds.upload(dep)
dep.publish()

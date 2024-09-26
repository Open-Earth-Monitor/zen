"""
This module provides a convenient way to programmatically work with Zenodo, facilitating the 
publication and management of research data on this platform. Researchers can create datasets, 
associate local files, upload data to Zenodo, and keep the dataset metadata up-to-date, all 
using Python code. This can streamline the process of sharing research data and integrating 
it with Zenodo's services.

Examples:
    Make sure to run the examples in Zenodo's sandbox::
    
        # Import Dataset and Zenodo classes
        from zen import LocalFiles, Zenodo
        
        # Add local files to the dataset
        local_file_paths = ['examples/file1.csv', 'examples/file2.csv']
        ds = LocalFiles(local_file_paths)
        ds.save('examples/dataset.json')
        
        # The LocalFiles object is a container for local files
        len(ds)  # Number of files in the dataset
        ds.storage_size
        ds.data  # Show the raw list of files
        ds[0]  # Access the first local file in the dataset
        
        # Setup a Zenodo deposition for the dataset. If there is no deposition
        # associated with dataset, creates a new one. You can also pass an existing
        # deposition to associate with your local files dataset.
        # Replace `token` by your actual access token.
        dep = ds.set_deposition(url=Zenodo.sandbox_url, token='your_access_token')
        
        # Accessing the deposition associated with your local files
        dep.data  # Dictionary representing Zenodo Deposition raw data
        dep.id  # Deposition ID
        dep.files  # DepositionFiles class to interact with remote files
        dep.metadata  # Metadata class to interact with deposition metadata
        
        # Upload the local files not already uploaded to Zenodo
        ds.upload(dep)
        
        # To open the dataset in a later Python session, use `from_file()` method
        ds = LocalFiles.from_file('examples/dataset.json')
        
        # If some local files has been changed, `upload()` method will detect it. 
        # It uploads just those local files not updated in Zenodo.
        # Calling `set_deposition()` method again just returns the existing deposition
        # already linked to the current dataset.
        # Replace `token` by your actual access token.
        dep = ds.set_deposition(url=Zenodo.sandbox_url, token='your_access_token')
        ds.upload(dep)
        
        # Adding additional files to the dataset
        new_local_file_paths = ['examples/file3.csv']
        ds.add(new_local_file_paths)
        
        # Save to persist changes in local dataset
        ds.save()
        
        # Interacting with files in Zenodo
        dep.files  # Access API endpoints to interact with files
        dep.files.create('examples/file3.csv')  # Upload a new file
        # The above code does not produce any side effect in ds dataset
        dep.refresh()  # Refresh deposition object to reflect Zenodo files
        
        # Access files
        dep.files[0]  # Get the first file
        dep.files[0] == dep[0]  # True
        dep[0].url  # Get URL to access the first file in Zenodo
        dep[0].download()  # Download the file to the working directory
        
        # Lists all modified local files or not uploaded to Zenodo deposition
        [f for f in ds if f not in dep]
        
        # Lists all files in Zenodo deposition not present in the local dataset
        [f for f in dep if f not in ds]
        
        # Upload only new/modified files to Zenodo deposition
        ds.upload(dep)
        
        # Delete a file from Zenodo deposition
        # This does not affect the local files dataset
        dep[0].delete()
        dep.refresh()
        
        # Update the deposition metadata
        from zen.metadata import MetaDataset, Creators
        meta = MetaDataset(title='My title', description='My description',
                           creators=[Creators.new('Doe, John', 'Zenodo')])
        # Update Zenodo deposition metadata
        dep.update(meta)
        
        # Alternative way to change metadata
        dep.metadata.title = 'Alternative title'
        dep.metadata.creators.add('Mae, Anna', 'Zenodo')
        dep.update()
        
        # Interacting with Zenodo deposition
        # Discard any edition in the deposition from Zenodo
        # If the deposition is not published, delete it from Zenodo
        dep.discard()
        # Publish the deposition
        # After publication, you cannot add, remove, or update any files
        dep.publish()
        # Create a new version of the deposition to add more files
        dep.new_version()
    

Note:
    - Before using this submodule, make sure you have a valid Zenodo account and access token.
    - Always refer to the Zenodo API documentation for detailed information about available 
      endpoints and parameters.
    - For more information, visit: https://developers.zenodo.org/

"""
from __future__ import annotations
from typing import List, Dict, Set, Callable, Iterator, Any, Union, Optional, TYPE_CHECKING
from typing_extensions import Self
if TYPE_CHECKING:
    from .api import Zenodo
    from .metadata import Metadata
from copy import copy, deepcopy
from datetime import datetime
import zen.api as __api__
import zen.metadata as __metadata__
import zen.utils as __utils__
import json
import os
import re
import requests
import tqdm
import time
import random

Zenodo = __api__.Zenodo

class BaseFile(dict):
    """Base Class for Representing Files with Associated Metadata.
    
    This class represents a file, whether it's local or remote, and includes associated metadata. 
    It serves as the foundation for the LocalFile and ZenodoFile classes.
    
    The `BaseFile` class is designed to encapsulate file-related information and metadata. It can 
    be instantiated with either a dictionary representing file information or a file path as a 
    string. When given a file path, it automatically extracts the filename and creates download 
    links. For dictionary input, the required 'filename' and 'links' entries must be present.

    Subclasses of `BaseFile` provide specific functionality for handling local and remote files.
    
    Args:
        file (Union[Dict[str,Any],str]): The dictionary representing a file or a file path.
    
    """
    def __init__(self, file: Union[Dict[str,Any],str]) -> None:
        if isinstance(file, str):
            if len(file) == 0:
                raise ValueError("Invalid file parameter. Value can't be empty.")
            data = dict(filename=os.path.basename(file), links=dict(download=copy(file)), 
                        properties=dict())
        elif isinstance(file, dict):
            data = deepcopy(file)
            if 'filename' not in data:
                raise ValueError("Invalid file parameter. Value must have entry 'filename'.")
            if 'links' not in data:
                raise ValueError("Invalid file parameter. Value must have entry 'links'.")
        else:
            raise TypeError('Invalid `file` parameter. Expecting a `str` but got a ' +
                            f'`{type(file)}` instead.')
        super().__init__(**data)
    
    @property
    def filename(self) -> str:
        """The base name of the file.
        """
        if 'filename' not in self:
            raise ValueError("File has not a 'filename' attribute.")
        return self['filename']
    
    @property
    def links(self) -> Dict[str,Dict[str,str]]:
        """Links to various aspects of the file, such as download links.
        """
        if 'links' not in self:
            raise ValueError("File has not a 'links' attribute.")
        return self['links']
    
    @property
    def url(self) -> str:
        """The URL to access the file data.
        """
        if 'download' not in self.links:
            raise ValueError("File has not a 'links.download' attribute.")
        return self.links['download']
    
    @property
    def checksum(self) -> Union[str,None]:
        """The checksum value of the file, if available.
        """
        if 'checksum' in self:
            return self['checksum']
    
    @property
    def filesize(self) -> Union[int,None]:
        """The size of the file in bytes.
        """
        if 'filesize' in self:
            return self['filesize']
    
    @property
    def filedate(self) -> Union[str,None]:
        """The last modification date of the file.
        """
        if 'filedate' in self:
            return self['filedate']
    
    @property
    def is_local(self) -> bool:
        """Indicates whether the file is stored locally (on the user's machine).
        """
        return os.path.isfile(self.url)
    
    @property
    def is_remote(self) -> bool:
        """Indicates whether the file is stored remotely (accessible via a URL).
        
        The supported URL schemas are defined in `utils.valid_schemas` variable.
        """
        return self.url.startswith(__utils__.valid_schemas)


class LocalFile(BaseFile):
    """Represents a local file within a Dataset.
    
    This class represents a local file that is part of a dataset. It extends the functionality of 
    the `BaseFile` class to provide methods for updating file metadata, uploading the file to a 
    Zenodo deposition, and managing local files.
    
    The `LocalFile` class is specifically designed to represent and manage local files within a 
    dataset. It inherits the core functionality from the `BaseFile` class and can be instantiated 
    with either a dictionary representing file information or a file path as a string.
    
    Args:
        file (Union[Dict[str,Any], str]): The file information or file path. If the last component 
            of the provided path (i.e. the basename of the path) identifies the file uniquely, the 
            path can be passed as a path string, otherwise the file have to be passed as a 
            dictionary.
    
    Example:
    
        >>> from zen.dataset import LocalFile
        >>> local_file = LocalFile('examples/file1.csv')
        >>> local_file.update_metadata()  # Get the file date and size
        >>> print(local_file.filename)
        file1.csv
    
    """
    def __init__(self, file: Union[Dict[str,Any],str]) -> None:
        super().__init__(file)
    
    def update(self, other: LocalFile) -> None:
        """Update current file metadata with metadata from other file.
        
        Args:
            other (LocalFile): The file from which values will be taken to merge.

        Raises:
            ValueError: if merging files have not the same filename
        
        """
        if self.filename != other.filename:
            raise ValueError('Invalid file merge. Files must have the same filename.')
        valid_checksum = self.checksum is None or other.checksum is not None or \
            ((self.filesize is None or other.filesize is None or self.filesize == other.filesize) and \
            (self.filedate is None or other.filedate is None or self.filedate == other.filedate))
        super().update(other)
        if not valid_checksum:
            del self['checksum']

    def update_metadata(self) -> None:
        """Update the current file metadata.
        
        Retrieves and updates the file's metadata, such as size and modification date.
        It automatically detects whether the file is stored locally or accessible remotely via URL.
        If file size or file last modification date change, the checksum is erased and a new
        one will be recomputed during upload.
        
        Raises:
            ValueError: if the file is not accessible.
        
        """
        if not self.is_local and not self.is_remote:
            raise ValueError(f"Invalid file value. File '{self['filename']}' is invalid.")
        if self.is_local:
            filesize = os.path.getsize(self.url)
            filedate = datetime.fromtimestamp(os.path.getmtime(self.url)).isoformat()
        if self.is_remote:
            filesize = None
            filedate = None
            response = requests.head(self.url)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            if content_length:
                filesize = int(content_length)
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                filedate = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z').isoformat()
        if filesize is not None:
            if self.checksum is not None and self.filesize is not None and self.filesize != filesize:
                del self['checksum']
            self['filesize'] = filesize
        if filedate is not None:
            if self.checksum is not None and self.filedate is not None and self.filedate != filedate:
                del self['checksum']
            self.filedate = filedate
    
    def upload(self, deposition: Deposition, force: bool=False, max_retries: int=15, 
               min_delay: int=10, max_delay: int=60) -> Self:
        """Uploads the local file to a Zenodo deposition.
        
        Uploads the local file to a Zenodo deposition, updating its metadata in the process. If the 
        file is remote, it will be temporarily downloaded for uploading. The checksum is calculated 
        before upload, and the file's metadata is updated accordingly. If parameter `force` is 
        `False`, this method will not upload if the file is already present in the deposition with
        the same checksum.
        
        Args:
            deposition (Deposition): The deposition to where upload the file.
            force (bool=False): Should the file be uploaded regardless it already been uploaded?

        Returns:
            LocalFile: The uploaded file with its updated metadata.
        
        """
        if not isinstance(deposition, Deposition):
            raise TypeError('Invalid `deposition` parameter. Expecting a `Deposition` but got a ' +
                            f'`{type(deposition)}` instead.')
        try:
            url = self.url
            tempfile = None
            self.update_metadata()
            print(f'Processing file: {url}')
            if self.is_remote and self.checksum is None:
                tempdir = os.path.join(os.getcwd(), '.zen')
                if not os.path.isdir(tempdir):
                    os.makedirs(tempdir)
                tempfile = os.path.join(tempdir, os.path.basename(self['filename']))
                url = __utils__.download_file(url, tempfile)
            if self.checksum is None:
                # checksum is erased whenever self.update_metadata() is called and the local 
                # file has been changed since last time the metadata was retrieved.
                self.checksum = __utils__.checksum(url, 'md5')
            if force or self not in deposition.files:
                # upload only if forced, or filename is not in the deposition, or the checksums differ.
                retries = 0
                while True:
                    try:
                        deposition.files.create(url)
                        break
                    except Exception as e:
                        print(f"Attempt {retries + 1} failed:", e)
                        if retries < max_retries - 1:
                            # Generate a random time delay between min_delay and max_delay seconds
                            random_delay = random.randint(min_delay, max_delay)
                            print(f"Retrying in {random_delay} seconds...")
                            time.sleep(random_delay)  # Wait for the random delay
                        else:
                            raise RuntimeError("Max retries exceeded")  
                        retries += 1
        finally:
            if tempfile is not None:
                os.remove(tempfile)
        return self
    
    def parse_template(self, template: str) -> dict:
        """Parses and extract properties from file name.
        
        Parses the filename using a string template. Any template substring passed outside 
        curly braces have to match exactly that portion on the filename. The template strings 
        inside curly braces, i.e., string placeholders, have to match at least one character 
        in the filename. A template matches a filename when all characters of the filename
        matches the template substrings and placeholders at the same exact order.
        
        Args:
            template (str): The template used to parse the filename and extract file properties.
        
        Returns:
            dict: A dictionary containing the parsed properties.
        
        """
        properties = dict()
        if template is None:
            return properties
        placeholders = __utils__.find_placeholders(template, None)
        try:
            template = f'^{template}$'.replace('.', r'\.')
            template = template.replace('{', r'(?P<').replace('}', '>.*?)')
            matches = re.match(template, self['filename'])
            if matches:
                for placeholder in placeholders:
                    properties[placeholder] = matches.group(placeholder)
        except:
           raise ValueError("Error while extracting placeholders' values. " + 
                            "Check for duplicated placeholder names in template string.")
        return properties
    
    @property
    def placeholders(self):
        return __utils__.find_placeholders(self.filename)
    
    @property
    def url(self) -> str:
        """The URL to access the file data.
        """
        return super().url
    
    @url.setter
    def url(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError('Invalid `url` value. Expecting a `str` but got a ' +
                            f'{type(value)} instead.')
        self.links['download'] = value
    
    @property
    def checksum(self) -> Union[str,None]:
        """The checksum value of the file, if available.
        """
        return super().checksum
    
    @checksum.setter
    def checksum(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError('Invalid `checksum` value. Expecting a `str` but got a ' +
                            f'{type(value)} instead.')
        self['checksum'] = value
    
    @property
    def filesize(self) -> Union[int,None]:
        """The size of the file in bytes.
        """
        return super().filesize
    
    @filesize.setter
    def filesize(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError('Invalid `filesize` value. Expecting an `int` but got a ' +
                            f'{type(value)} instead.')
        self['filesize'] = value
    
    @property
    def filedate(self) -> Union[str,None]:
        """The last modification date of the file.
        """
        return super().filedate
    
    @filedate.setter
    def filedate(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError('Invalid `filedate` value. Expecting a `str` but got a ' +
                            f'{type(value)} instead.')
        if not __utils__.is_iso8601_datetime(value):
            raise ValueError(f"Invalid `filedate` value. Value '{value}' is not in " +
                             "the format '%Y-%m-%d %H:%M:%S.%f%z'.")
        self['filedate'] = value
    
    @property
    def properties(self) -> Union[Dict[str,Any],None]:
        """Additional properties or metadata associated with the file.
        
        This is mainly used to store values used in file template expansion.
        For more details, please, see `LocalFiles.expand()` method.
        
        """
        if 'properties' in self:
            return self['properties']
    
    @properties.setter
    def properties(self, value: Dict[str,Any]) -> None:
        if not isinstance(value, dict):
            raise TypeError('Invalid `property` value. Expecting a `dict` but got a ' +
                            f'{type(value)} instead.')
        self['properties'] = value


class ZenodoFile(BaseFile):
    """Represents a File Associated with a Zenodo Deposition.
    
    This class is designed to represent a file that is associated with a Zenodo deposition. It 
    extends the functionality of the `BaseFile` class and provides methods for refreshing file 
    data from Zenodo, deleting the file from Zenodo, and retrieving the checksum of the file.
    
    The `ZenodoFile` class is tailored for files that are part of a Zenodo deposition. It is 
    instantiated with a dictionary representing file information and the corresponding Zenodo 
    deposition to which the file is linked.

    This class offers methods to interact with Zenodo's API, allowing you to refresh file data, 
    delete files from a Zenodo deposition, and retrieve checksums.

    Args:
        file (Dict[str,Any]): The file dictionary.
        deposition (Deposition): The Zenodo deposition to which this Zenodo file belongs.
    
    Example:
    
        1. Create a new Zenodo deposition and upload a file:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='your_api_token')
        >>> dep = zen.depositions.create()
        >>> dep.files.upload('examples/file1.csv')
        
        2. Download a file from deposition to current directory
        
        >>> zenodo_file = dep.files[0]
        >>> zenodo_file.download()
        
        Discard the deposition example.
        
        >>> dep.discard()
    
    """
    def __init__(self, file: Dict[str,Any], deposition: Deposition) -> None:
        if not isinstance(file, dict):
            raise TypeError('Invalid `file` parameter. Expecting a `dict` but got a ' +
                            f'`{type(file)}` instead.')
        super().__init__(file)
        self._deposition = deposition
    
    def download(self, dirname: Optional[str]=None) -> str:
        """Downloads a file to a local directory.
        
        Args: 
            dirname (Optional[str]=None): The local path to download the file (default to 
                current directory). 
        
        Returns: 
            str: The path of downloaded file. 
        
        Raises: 
            ValueError: If directory does not exist or file has not a valid download link.
        
        """ 
        if dirname is None:
            dirname = os.getcwd()
        if not os.path.isdir(dirname):
            raise ValueError(f"Invalid `dirname` parameter. Directory '{dirname}' is invalid.")
        dest_file = os.path.join(dirname, self['filename'])
        # Support for draft files
        url = self.url
        if url.find('draft/files') > -1:
            url = self._deposition.api.api.url_token(url)
        __utils__.download_file(url, dest_file)
    
    def refresh(self) -> Self:
        """Refresh the file data from Zenodo.
        """
        file = self._deposition.api.api.retrieve_deposition_file(self)
        self.__init__(file, self._deposition)
        return self
    
    def delete(self) -> None:
        """Delete the file from Zenodo.
        """
        self._deposition.api.api.delete_deposition_file(self)
    
    @property
    def checksum(self) -> str:
        """The checksum of the Zenodo file.
        """
        return self._deposition.api.api.checksum_deposition_file(self)


class _BaseDataset:
    def __init__(self, data: Optional[Any]) -> None:
        self._data = data
        self._invalidated = False
    
    def __repr__(self) -> str:
        return str(self._data)
    
    def _revalidate(self) -> None:
        self._invalidated = False
    
    def invalidate(self) -> None:
        """Flags the dataset as not synchronized.
        """
        self._invalidated = True


class _FileDataset(_BaseDataset):
    def __init__(self, files: Optional[List[Union[Dict[str,Any],str]]]=None) -> None:
        # Default
        if files is None:
            files = list()
        # Check params
        if not isinstance(files, list):
            raise TypeError('Invalid `files` parameter. Expecting a `list` but got a ' + 
                            f'`{type(files)}` instead.')
        # Check duplication
        data = [self._new_file(file) for file in files]
        if len(data) != len(set([file.filename for file in data])):
            raise ValueError('Duplicated filenames in the file list.')
        # Initialize files
        super().__init__(data)
        self._data: List[BaseFile] = self._data
        self._index = {file.filename: file for file in self._data}
        
    def __repr__(self):
        return f'<Files: {len(self._data)} file(s)>'
    
    def __len__(self):
        return len(self._data)
    
    def __getitem__(self, key: int) -> BaseFile:
        return self._data[key]
    
    def __iter__(self) -> Iterator[BaseFile]:
        for file in self._data:
            yield file
    
    def __contains__(self, item: BaseFile):
        return item.filename in self._index and (self._index[item.filename].checksum is None or \
            item.checksum is None or item.checksum == self._index[item.filename].checksum)
    
    def _new_file(self, file: Union[Dict[str,Any],str]) -> BaseFile:
        return BaseFile(file)
    
    def _for_each(self, fn_foreach: Callable[[BaseFile],None], progress: bool=True) -> None:
        for file in tqdm.tqdm(self._data, disable=not progress or len(self._data) <= 1):
            fn_foreach(file)
    
    def _filter(self, fn_filter: Optional[Callable[[BaseFile],bool]]=None) -> List[BaseFile]:
        # Check params
        if fn_filter.__code__.co_argcount < 1:
            raise ValueError('Invalid `fn_filter` parameter. Function must be able to receive ' + 
                             'at least one argument.')
        # Filter files
        return [file for file in self._data if fn_filter(self._new_file(file))]


class _DatasetFile:
    @classmethod
    def from_file(cls, file: str) -> _DatasetFile:
        if file is None:
            raise TypeError('Invalid `file` parameter. Expecting a `str` but got a ' +
                            f'`{type(file)}` instead.')
        if not os.path.isfile(file):
            raise ValueError(f"Invalid `file` parameter. File '{file}' is invalid.")
        data = __utils__.load_json(file)
        if 'localfiles' not in data:
            raise ValueError("Invalid dataset JSON file. No 'localfiles' entry found.")
        if 'zenodo' in data and data['zenodo'] is not None and 'id' not in data['zenodo']:
            raise ValueError("Invalid dataset JSON file. Dataset must have 'zenodo.id' value.")
        dataset = cls(data['localfiles'], data['zenodo'])
        dataset.files.file = file
        return dataset
    
    def __init__(self, files: Union[LocalFiles,List[Dict[str, Any],str],None], 
                 deposition: Optional[Union[Dict[str,Any],int]]=None) -> None:
        if files is not None and not isinstance(files, LocalFiles):
            files = LocalFiles(files)
        self.files: Union[LocalFiles,None] = files
        self.deposition: Union[Dict[str,Any],int,None] = deposition
    
    def save(self, file: str) -> None:
        data = dict(zenodo=self.deposition, localfiles=self.files.data)
        __utils__.save_json(data, file)


class LocalFiles(_FileDataset):
    """Represents a dataset associating local files to a Zenodo deposition.
    
    This class provides methods for creating, updating, and managing local and Zenodo datasets. 
    As your local dataset changes, this class simplifies the process of updating and maintaining 
    it on Zenodo. You can quickly push updates without manually managing the complexities of 
    Zenodo's API.
    
    The `LocalFiles` class provides access to the local files associated with the dataset. It
    can be initialized with a list of local files or a template file name that can be expanded
    into a set of file paths using string placeholders. During template expansion, properties 
    are extracted from the filenames and stored in the respective file in the 'properties' key.
    Call `save()` method to make sure that any local update is saved in the dataset JSON file.
    
    The `deposition` property represents the Zenodo deposition associated with the dataset. It 
    provides access to the Zenodo deposition object for the dataset, which is important for 
    managing the dataset on the Zenodo platform. After creating a new dataset, you can bind it
    to a specific Zenodo deposition using `set_deposition()` method. 
    
    Args:
        files (Optional[List[Union[Dict[str,Any],str]]]=None): The list of local files or 
            file paths.
        template (Optional[str]=None): The filename template to extract properties from the list 
            of file names.
        
    Example:
    
        1. Create a local dataset:
        
        >>> from zen import LocalFiles
        >>> local_file_paths = ['examples/file1.csv', 'examples/file2.csv']
        >>> ds = LocalFiles(local_file_paths)
        
        2. Save to a file:
        
        >>> ds.save('examples/dataset.json')
        
        3. Create or retrieve a deposition
        
        >>> dep = ds.set_deposition(url=Zenodo.sandbox_url, token='your_api_token')
        
        At the first run, this will create the deposition. After that it
        just load saved deposition from local dataset file.
        
        4. Upload files to Zenodo deposition
        
        >>> ds.upload(dep)  # upload files
        
        5. Add and upload additional files
        
        >>> ds.add(['examples/file3.csv'])
        >>> ds.upload(dep)  # upload just new/modified files
        >>> ds.upload(dep, force=True)  # upload everything again
        
        Discard the deposition example.
        
        >>> dep.discard()
    
    """
    @staticmethod
    def _expand(file: LocalFile, **kwargs) -> LocalFile:
        for k, v in kwargs.items():
            file['filename'] = file.filename.replace('{' + k + '}', str(v))
            file.properties[k] = v
            file.url = file.url.replace('{' + k + '}', str(v))
        return file
    
    @classmethod
    def from_template(cls, template: str) -> Self:
        """Create a New Dataset Based on a File Name Template.
        
        This method imports files to the current dataset based on a provided file name template. The 
        template is expanded into a list of files, and these files are associated with the current 
        dataset.
        
        The `from_template()` method allows you to create a dataset using a file name template. 
        This template is used to generate a list of files that are then associated with the current 
        dataset.
        
        Placeholders within the template, enclosed in curly braces (e.g., '{index}'), are replaced 
        with specific values, allowing you to create a set of files with structured names. For 
        example, if the template is 'file{index}.csv', expanding it, for example, calling 
        `expand(index=list(range(12)))` would result in file names like 'file0.csv', 'file1.csv', ... 
        and 'file11.csv'. After expansion, each expanded placeholder value is stored in 'properties' 
        key entry of each file.
        
        Args:
            template (str): The file name template to be expanded as a list of files.
        
        Returns:
            LocalFiles: The dataset with the template.
        
        Example:
            >>> ds = LocalFiles.from_template('file{index}_{year}.csv')
            >>> print(ds.placeholders)
            {'index', 'year'}
            >>> ds.expand(index=[10, 20, 30])
            >>> ds.expand(year=['2019', '2020'])
            >>> print(len(ds))
            6
                
        """
        files = cls([template])
        files._placeholders = __utils__.find_placeholders(template, None)
        return files
        
    
    @classmethod
    def from_file(cls, file: str) -> LocalFiles:
        """Loads the dataset metadata.
        
        Loads the deposition and the local files metadata on a local file.
        
        Args:
            file (str): The filename to read the dataset.
        
        Returns: 
            LocalFiles: A new object with the dataset loaded from file.
        
        Example:
            >>> ds = LocalFiles.from_file('examples/dataset.json')
            >>> ds.data
        
        """ 
        dataset = _DatasetFile.from_file(file)
        return dataset.files
    
    def __init__(self, files: Optional[List[Union[Dict[str,Any],str]]]=None, 
                 template: Optional[str]=None) -> None:
        if template is not None:
            if not isinstance(template, str):
                raise TypeError('Invalid `template` parameter. Expecting a `str` but got a ' +
                                f'`{type(template)}` instead.')
            template = template.strip()
            if len(template) == 0:
                raise ValueError('Invalid `template` parameter. Value is empty.')
        super().__init__(files)
        self._data: List[LocalFile] = self._data
        self._index: Dict[str, LocalFile] = self._index
        self._file: Optional[str] = None
        self._placeholders = set()
        if template is not None:
            for file in self._data:
                file.properties.update(file.parse_template(template))
        self._deposition = None
    
    def __getitem__(self, key: int) -> LocalFile:
        return super().__getitem__(key)
    
    def __iter__(self) -> Iterator[LocalFile]:
        return super().__iter__()
    
    def _new_file(self, file: Union[Dict[str,Any],str]) -> LocalFile:
        return LocalFile(file)
    
    def _update_metadata(self) -> None:
        for file in self:
            file.update_metadata()
    
    def set_deposition(self, url: str='https://zenodo.org', token: Optional[str]=None,
                       headers: Optional[Dict[str,str]]=None,
                       metadata: Optional[Union[Metadata,Dict[str,Any]]]=None,
                       deposition: Optional[Union[Deposition,Dict[str,Any],int]]=None,
                       create_if_not_exists: bool=True) -> Deposition:
        """Set the dataset deposition.
        
        Set the deposition of the dataset. If the dataset has no linked deposition, the `deposition` 
        parameter is `None` and the `create_if_not_exists` parameter is `True`, it creates a 
        new deposition. The linked deposition is saved into dataset file.
        
        Args:
            url (str): The base URL of the Zenodo API. 
            token (Optional[str]=None): The access token for making authenticated requests to 
                the Zenodo API. 
            headers (Optional[Dict[str,str]]=None): Additional headers to include in API requests. 
            metadata (Optional[Union[MetaGeneric,Dict[str,Any]]]=None): The metadata for the new 
                deposition. Ignored if `deposition` is informed or the dataset already has a 
                deposition.
            deposition (Optional[Union[Deposition,Dict[str,Any],int]]=None): An existing deposition 
                to bind with the current dataset.
            create_if_not_exists (bool=True): If there is no deposition linked to the current
                dataset, it creates a new deposition on Zenodo. Ignored if `deposition` parameter
                is informed.
        
        Returns: 
            Deposition: The deposition associated with the current dataset.
        
        Raises:
            ValueError: If the dataset already has an deposition and a different deposition has 
                been passed to the function.
            ValueError: If the dataset does not have a deposition, no deposition has been passed
                to `deposition` parameter, and parameter `create_if_not_exists` is `False`.
        
        """ 
        if self._file is None:
            raise ValueError('Invalid operation. Please, use `save()` method to save the ' + 
                             'dataset before assigning a deposition.')
        dataset = _DatasetFile.from_file(self._file)
        if deposition is None:
            api = Zenodo(url, token, headers)
            if dataset.deposition is None:
                if not create_if_not_exists:
                    raise ValueError('No deposition is linked with current dataset. Please, ' +
                                     'provide a valid deposition to `deposition` parameter, or ' +
                                     'inform `create_if_not_exists=True` to create a new ' +
                                     'deposition.')
                # check if file is writeable
                dataset.save(self._file)
                deposition = api.depositions.create(metadata)
            else:
                deposition = api.depositions.retrieve(dataset.deposition)
        else:
            if not isinstance(deposition, Deposition):
                api = Zenodo(url, token, headers)
                deposition = api.depositions.retrieve(deposition)
            if dataset.deposition is not None:
                saved_deposition = api.depositions.retrieve(dataset.deposition)
                if saved_deposition.id != deposition.id:
                    raise ValueError('Invalid deposition assignment. The current deposition ' +
                                    f'({saved_deposition.id}) differs from the provided one ' +
                                    f'({deposition.id}). Please, consider creating a new dataset.')
        dataset.deposition = deposition.data
        dataset.save(self._file)
        self._deposition = deposition
        return deposition
    
    def save(self, file: Optional[str]=None) -> LocalFiles:
        """Saves the dataset metadata.
        
        Saves the deposition and the local files metadata on a local file to be loaded 
        later using `LocalFiles.from_file()` class method. 
        
        Args:
            file (Optional[str]=None): The filename to save the dataset.
        
        Returns: 
            LocalFiles: The current dataset object.
        
        Examples:
        
            >>> from zen import LocalFiles, Zenodo
            >>> local_file_paths = ['examples/file1.csv', 'examples/file2.csv']
            >>> ds = LocalFiles(local_file_paths)
            >>> ds.save('examples/dataset.json')
            
        """ 
        if len(self._placeholders) > 0:
            raise ValueError('Cannot save datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        if file is None:
            file = self._file
        if file is None:
            raise TypeError('Invalid `file` parameter. Expecting a `str` but got a ' +
                            f'`{type(file)}` instead.')
        self._file = file
        if os.path.isfile(self._file):
            dataset = _DatasetFile.from_file(self._file)
            # merge files and save
            dataset.files.merge(self, remove_unmatched=True)
            self.merge(dataset.files, remove_unmatched=True)
            deposition = dataset.deposition
        else:
            deposition = None
        # update file date and size
        self._update_metadata()
        dataset = _DatasetFile(self, deposition)
        dataset.save(self._file)
        return self
    
    def filter(self, fn_filter: Callable[[LocalFile], bool]) -> LocalFiles:
        """Filter Files Based on Custom Criteria.
        
        This method filters the files in the dataset based on a filter function (`fn_filter`). Any 
        modifications made to the files using the `fn_filter` function will not have a side effect on 
        the resulting dataset.

        The `filter()` method allows you to filter files in the dataset based on custom criteria. 
        The filter function receives as argument the files to be tested from the current object. If
        the function returns True, the file will be in the returned dataset, otherwise the file will
        be removed from the returned dataset.
        
        Args:
            fn_filter (Callable[[LocalFile], bool]): A matching criteria function 
                that determines whether a file matches the filter or not. The function must be able 
                to receive one argument, a file from the object being filtered, and return a boolean.
        
        Returns:
            LocalFiles: A copy of the dataset with the filtered files.
        
        Example:
        
            >>> from zen import LocalFiles
            >>> def custom_filter(file):
            ...     file.update_metadata()
            ...     return file.filesize > 34250  # Only keep files larger than ~34 KB.
            ...
            >>> ds = LocalFiles(['examples/file1.csv', 'examples/file2.csv'])
            >>> filtered_ds = ds.filter(custom_filter)
            >>> print(len(filtered_ds))
            1
        
        """
        if len(self._placeholders) > 0:
            raise ValueError('Cannot filter datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        return LocalFiles(self._filter(fn_filter))
    
    def merge(self, other: _FileDataset, remove_unmatched: bool=False) -> Self:
        """Merge Files into the Current Dataset.
        
        This method merges files from another dataset into the current dataset. You can choose to 
        remove unmatched files from the current dataset.
        
        The `merge()` method allows you to merge files from another dataset (`other`) into the 
        current dataset. If a file with the same name already exists in the current dataset, it 
        will be updated with the data from the other dataset.
        
        You can choose to remove unmatched files from the current dataset by setting `remove_unmatched` 
        to `True`. This means that any files in the current dataset that do not exist in the `other` 
        dataset will be removed.
        
        If there are placeholders in the dataset that have not been evaluated, merging will not be 
        allowed. Use the `expand()` function to expand placeholders before merging.
        
        Args:
            other (_FileDataset): The _FileDataset object from witch files have to be imported.
            remove_unmatched (bool=False): Should the unmatched files in the current dataset be 
                removed?
        
        Returns:
            LocalFiles: The dataset with the new imported/updated/deleted files.
        
        Example:
        
            >>> ds = LocalFiles(['examples/file1.csv', 'examples/file2.csv'])
            >>> other_ds = LocalFiles(['examples/file2.csv', 'examples/file3.csv'])
            >>> ds.merge(other_ds, remove_unmatched=False)
            >>> print(len(ds))
            3
        
        """
        # TODO: optimize merge() method! Maybe create an internal _merge() where there is 
        # no need to create a copy of file metadata
        if len(self._placeholders) > 0:
            raise ValueError('Cannot merge datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        for file in other._data:
            if file.filename in self._index:
                self._index[file.filename].update(self._new_file(file))
            else:
                self._index[file.filename] = self._new_file(file)
                self._data.append(self._index[file.filename])
        if remove_unmatched:
            for file in self._data:
                if not file.filename in other._index:
                    del self._index[file.filename]
                    self._data.remove(file)
        return self
    
    def add(self, files: List[Union[Dict[str,Any],str]], template: Optional[str]=None) -> Self:
        """Add or Update Files in the Current Dataset.
        
        This method allows you to add new files to the current dataset. If a file with the same name 
        already exists, it will be updated in the dataset. You can also provide a filename template 
        to extract properties from the list of filenames.
        
        The `add()` method is used to add new files to the current dataset. If any of the provided 
        files have the same name as an existing file in the dataset, the existing file is updated 
        with the new data.
        
        You can also specify a `template` to extract properties from the filenames in the list. This 
        template is used to associate properties with the respective files in the dataset.
        
        Args:
            files (List[Union[Dict[str,Any],str]]): The list of files to be added.
            template (Optional[str]=None): The filename template to extract properties from the list 
                of filenames.
        
        Returns:
            LocalFiles: The dataset with the added or updated files.
        
        Example:
        
            >>> ds = LocalFiles(['examples/file1.csv', 'examples/file3.csv'])
            >>> new_file_list = ['examples/file1.csv', 'examples/file2.csv']
            >>> ds.add(new_file_list, template='file{index}.csv')
            >>> print(len(ds))
            3
        
        """
        if len(self._placeholders) > 0:
            raise ValueError('Cannot add files on datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        local = LocalFiles(files, template)
        self.merge(local, remove_unmatched=False)
        return self
    
    def expand(self, **kwargs) -> Self:
        """Expand the Placeholders in the Dataset.
        
        This method expands the dataset by replacing placeholders in the filenames (templates) with 
        provided keyword arguments. Placeholders are special tokens enclosed in curly braces within 
        the template string, e.g., '{placeholder}'. They represent values that can vary, and by 
        replacing them with specific values, you can generate a list of files in the dataset.
        
        The `expand()` method is used to replace placeholders in the dataset with provided values, 
        effectively creating multiple versions of the dataset. Placeholders are identified by their 
        names and should match the keyword arguments provided. If more than one keyword arguments 
        is passed at same time, the expansion is done simultaneously using the first value of each 
        argument, then the second value, and so on. Hence, the number of expanded files is the same 
        as the length of values passed to a keyword argument. In this case, all keywords arguments 
        must have the same length of values.
        
        By calling the `expand()` method multiple times with different sets of values for the 
        placeholders, you take a different approach. Instead of simultaneous expansion, this method 
        focuses on exploring all possible combinations of values for each placeholder. In other 
        words, each time you invoke `expand()`, it systematically combines the values you provide 
        for the placeholders to create a unique set of filenames for the dataset. Once all 
        placeholders in the filename templates are expanded, you arrive at the list of unique files 
        within the dataset. At this point, further expansion is no longer possible.
        
        The `expand()` method is a versatile tool for customizing filenames in the dataset and to 
        associate properties to each file. All expanded placeholder becomes a property in the file 
        object. A list of all properties can be seen by `properties` class member.
        
        Args:
            **kwargs: Keyword arguments that represent the values used to replace placeholders in 
                the file template. Each keyword argument should correspond to a placeholder in the 
                file template, and the value should be a list of replacement values. When providing 
                multiple keyword arguments, all of them must have the same number of elements to 
                ensure consistent replacement across all placeholders.
        
        Raises:
            ValueError: If there are no placeholders to be expanded or if a placeholder is 
                not found.
            ValueError: If input lists have different lengths.
        
        Returns:
            LocalFiles: The expanded LocalFiles object.
        
        Examples:
        
            1. Simultaneously Expanding Placeholders:
            
            >>> from zen import LocalFiles
            >>> template = 'file{index}_{year}.csv'
            >>> ds = LocalFiles.from_template(template)
            >>> ds.expand(index=[10, 20], year=['1990', '2000'])
            >>> # Multiple files: 'file10_1990.csv', 'file20_2000.csv', ...
            >>> len(ds)
            2
            
            2. Sequentially Expanding Placeholders:
            
            >>> ds = LocalFiles.from_template(template)
            >>> ds.expand(index=[10, 20])
            >>> # Multiple files: 'file10_{year}.csv', 'file20_{year}.csv'
            >>> # applies each value to each previously expanded list.
            >>> ds.expand(year=['1990', '2000']) 
            >>> # Multiple files: 'file10_1990.csv', 'file20_1990.csv', 
            >>> #     'file10_2000.csv', 'file20_2000.csv'
            >>> len(ds)
            4

        """
        # Check params
        if not len(self._placeholders):
            raise ValueError('There is no placeholder to be expanded')
        for k in kwargs.keys():
            if k not in self._placeholders:
                raise ValueError(f"Placeholder '{k}' not found.")
            if not isinstance(kwargs[k], list):
                kwargs[k] = [kwargs[k]]
        len_args = list(set(len(arg) for arg in kwargs.values()))
        if len(len_args) > 1:
            raise ValueError('All input lists must have the same length.')
        if len(len_args) == 0 or len_args[0] == 0:
            return self
        # Expand files
        args = [dict(zip(kwargs.keys(), values)) for values in zip(*kwargs.values())]
        files = [LocalFiles._expand(self._new_file(file), **arg) 
                 for file in self._data for arg in args]
        super().__init__(files)
        # Post process
        for k in set(kwargs.keys()):
            self._placeholders.remove(k)
        return self
    
    def modify_url(self, fn_modifier: Optional[Callable[[str],str]]=None, 
                   prefix: Optional[str]=None, suffix: Optional[str]=None) -> Self:
        """Modify URLs in the dataset using various methods.
        
        You can modify URLs in one of the following ways:
        
        - Using a modifier function: Pass a function (`fn_modifier`) that takes a URL as input and 
          returns a modified URL.
        - Adding a prefix: Use the `prefix` parameter to insert a common prefix at the beginning 
          of each URL.
        - Adding a suffix: Utilize the `suffix` parameter to append a common suffix at the end of 
          each URL.
        
        Args:
            fn_modifier (Optional[Callable[[str],str]]=None): A function to modify URLs. If not 
                provided, URLs remain unchanged.
            prefix (Optional[str]=None): The prefix to insert at the beginning of URLs.
            suffix (Optional[str]=None): The suffix to insert at the end of URLs.
        
        Returns:
            LocalFiles: The current LocalFiles with updated URLs based on the 
                specified modifications.
        
        Examples:
        
            >>> from zen import LocalFiles
            >>> ds = LocalFiles(['file1.csv', 'file2.csv'])
            >>> ds.modify_url(prefix='http://example.com/')
            
            This adds the prefix 'https://example.com/' to the beginning of all URLs in the dataset.
            
            >>> def custom_modifier(url):
            ...     return url.replace('http://', 'https://')
            ... 
            >>> ds.modify_url(fn_modifier=custom_modifier)
            
            This example modifies all URLs in the dataset by replacing 'http://' with 'https://'.
            
            >>> ds.modify_url(suffix='/download')
            
            This appends the suffix '/download' to the end of all URLs in the dataset.
        
        """
        if len(self._placeholders) > 0:
            raise ValueError('Cannot change files on datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        if fn_modifier is None:
            fn_modifier = lambda x: x
        for file in self._data:
            file.url = ('' if prefix is None else prefix) + fn_modifier(file.url) + \
                ('' if suffix is None else suffix)
        return self
    
    def upload(self, deposition: Optional[Deposition]=None, progress: bool=True, 
               force: bool=False) -> None:
        """Upload files to a Zenodo deposition and update files' metadata.
        
        This method enables you to upload files to a Zenodo deposition, ensuring that their metadata 
        is up-to-date.
        
        Args:
            deposition (Optional[Deposition]=None): Alternative deposition to upload files.
            progress (bool=True): Show a progress bar?
            force (bool=False): Should all files be uploaded regardless they already been 
                uploaded or not?
        
        Returns:
            None
        
        Examples:
        
            1. Upload files to a Zenodo deposition:
            
            >>> from zen import LocalFiles, Zenodo
            >>> ds = LocalFiles.from_file('examples/dataset.json)
            >>> dep = ds.set_deposition(Zenodo.sandbox_url, token='your_api_token')
            >>> ds.upload(dep)
            
            This example uploads files to the specified Zenodo deposition (`my_deposition`) and 
            shows a progress bar during the upload. It won't re-upload files that already exist 
            in the deposition.
            
            2. Forcefully re-upload all files to a Zenodo deposition:
            
            >>> ds.upload(dep, force=True)
            
            In this case, the `force` parameter is set to `True`, which ensures that all files are 
            re-uploaded, even if they exist in the deposition. A progress bar is displayed during 
            the process.
        
        """
        if len(self._placeholders) > 0:
            raise ValueError('Cannot upload files on datasets with non-evaluated placeholders. ' + 
                             'Please, use `expand()` function to expand all placeholders.')
        
        if not isinstance(deposition, Deposition):
            raise TypeError('Invalid `deposition` value. Expecting a `Deposition` but got a ' +
                            f'{type(deposition)} instead.')
        def _upload(file: LocalFile) -> None:
            file.upload(deposition, force)
        try:
            self._for_each(_upload, progress)
        finally:
            self.save()
        deposition.refresh()
    
    def summary(self, properties: Optional[List[str]]=None, **kwargs):
        """Summarizes the file properties of the current dataset
        
        To list all properties present in the dataset's files, use `properties` class member.
        This method can be used to generated personalized metadata description of the 
        dataset.

        Args:
            properties (Optional[List[str]]=None): A list of properties to be summarized.
            **kwargs: Alternative summarizing functions to generate the resulting dictionary.
                By default, `min` and `max` values are computed. The name of summarizing
                function becomes part of the name of the summarized property value.

        Returns:
            dict: The dictionary with summarized values by property and function.
        
        Examples:
        
            1. Generate file list and summary
            
            >>> from zen import LocalFiles
            >>> ds = LocalFiles.from_template('file{index}.csv')
            >>> ds.expand(index=[1, 2, 3])
            >>> ds.summary()
            {'index_min': '1', 'index_max': '3'}
            
            2. Create a templated metadata and render personalized description
            
            >>> from zen.metadata import Dataset
            >>> meta = Dataset(
            ...     title='My title', 
            ...     description='Dataset index from {index_min} to {index_max}'
            ... )
            >>> meta.render(ds.summary())
            {'upload_type': 'dataset',
             'title': 'My title',
             'description': 'Dataset index from 1 to 3',
             'prereserve_doi': True}
        
        """
        if properties is None:
            properties = list(self.properties)
        def _min(values: List[Any]):
            return min([v for v in values if v is not None and v != ''])
        def _max(values: List[Any]):
            return max([v for v in values if v is not None and v != ''])
        if 'min' not in kwargs:
            kwargs['min'] = _min
        if 'max' not in kwargs:
            kwargs['max'] = _max
        data = dict()
        for p in properties:
            values = [file.properties[p] for file in self._data if p in file.properties]
            for k, fn in kwargs.items():
                data[f'{p}_{k}'] = fn(values)
        return data
    
    @property
    def data(self) -> List[LocalFile]:
        """List of files stored by the dataset.
        """
        return self._data
    
    @property
    def index(self) -> Dict[str, LocalFile]:
        """List of files stored by the dataset.
        """
        return self._index
    
    @property
    def storage_size(self) -> int:
        """Calculates the total data size of the files.
        """
        return sum([file.filesize for file in self._data])
    
    @property
    def placeholders(self) -> Set[str]:
        """List of the placeholders given in the file name template.
        """
        return self._placeholders
    
    @property
    def file(self) -> Union[str,None]:
        """File path of the current dataset.
        """
        return self._file
    
    @file.setter
    def file(self, value: Union[str,None]) -> None:
        if value is not None and not isinstance(value, str):
            raise TypeError('Invalid file path. Expecting `str` but got ' +
                            f'`{type(value)}` instead.')
        if self._file is not None:
            raise ValueError('Invalid file assignment. Please, use `save()` method to ' +
                             'create a dataset with a new file path.')
        self._file = value
    
    @property
    def properties(self) -> Set[str]:
        """Set with all properties present in the dataset's files.
        """
        keys = set()
        for f in self._data:
            keys.update([k for k in f.properties.keys()])
        return keys
    
    @property
    def deposition(self) -> Deposition:
        return self._deposition


class DepositionFiles(_FileDataset):
    """Represents the files associated with a Zenodo deposition.
    
    This class provides methods for managing files, such as listing and refreshing files, creating 
    and deleting files, and querying specific files within the deposition.
    
    Args:
        deposition (Deposition): The Deposition object to which these files are associated.
        files (Optional[List[Dict,str]]=None): Optional initial list of file data or file paths 
            (default is None).
    
    """
    def __init__(self, deposition: Deposition, files: Optional[List[Dict,str]]=None) -> None:
        self._deposition = deposition
        super().__init__(files)
        self._data: List[ZenodoFile] = self._data
    
    def __repr__(self) -> str:
        self._revalidate()
        return super().__repr__()
    
    def __getitem__(self, key: int) -> ZenodoFile:
        self._revalidate()
        return super().__getitem__(key)
    
    def _new_file(self, file: Union[Dict[str,Any],str]) -> ZenodoFile:
        return ZenodoFile(file, self._deposition)
    
    def _revalidate(self) -> None:
        if self._invalidated:
            try:
                self.list()
                super()._revalidate()
            except json.JSONDecodeError as e:
                pass
    
    def list(self) -> Self:
        """Lists and refresh the file list of the Zenodo deposition. 
        
        Args: 
            None
        
        Returns: 
            DepositionFiles: The list of files of the Zenodo deposition.
        
        """ 
        self.__init__(self._deposition, self._deposition.api.api\
            .list_deposition_files(self._deposition.id))
        return self
    
    def create(self, file: str, bucket_filename: Optional[str]=None) -> Self:
        """Uploads a file to the deposition on the Zenodo API. 
        
        Args: 
            file (str): The local file path of the file to upload. 
            bucket_filename (Optional[str]=None): The desired filename for the file in the 
                deposition's bucket. 
        
        Returns: 
            DepositionFiles: The current object.
        
        """ 
        tempfile = None
        if not os.path.isfile(file):
            if not file.startswith(__utils__.valid_schemas):
                raise ValueError(f"Invalid `file` parameter. File '{file}' is invalid.")
        try:
            if file.startswith(__utils__.valid_schemas):
                tempdir = os.path.join(os.getcwd(), '.zen')
                if not os.path.isdir(tempdir):
                    os.makedirs(tempdir)
                tempfile = os.path.join(tempdir, os.path.basename(file))
                file = __utils__.download_file(file, tempfile)
            try:
                self._deposition.api.api.create_deposition_file(self._deposition.id, file, 
                                                                bucket_filename)
            except json.JSONDecodeError as e:
                pass
        finally:
            if tempfile is not None:
                os.remove(tempfile)
            self.invalidate()
    
    def delete(self, file: ZenodoFile) -> None:
        """Deletes a file of the Zenodo deposition. 
        
        Args: 
            file (ZenodoFile): The file to be deleted from Zenodo. 
        
        """ 
        try:
            self._deposition.api.api.delete_deposition_file(file)
        except json.JSONDecodeError as e:
            pass
        finally:
            self.invalidate()
    
    @property
    def data(self) -> List[ZenodoFile]:
        """List of files stored by the dataset.
        """
        return self._data
    
    @property
    def index(self) -> Dict[str, ZenodoFile]:
        """List of files stored by the dataset.
        """
        return self._index
    
    @property
    def storage_size(self) -> int:
        """Calculate the total data size of the files.
        """
        return sum([file.filesize for file in self._data])


class Deposition(_BaseDataset):
    """Represents a Zenodo Deposition.
    
    This class defines a Zenodo deposition, providing methods to create, retrieve, and interact with
    specific Zenodo depositions using the Zenodo API.
    
    Args:
        api (Zenodo): The Zenodo instance used to interact with Zenodo API.
        data (Dict[str,Any]): The deposition data, including 'id', 'metadata', 'files', 
            and 'links' entries.
    
    Examples:
    
        1. Create a new Zenodo deposition:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='your_api_token')
        >>> meta = {
        ...     'title': 'My New Deposition',
        ...     'description': 'A test deposition for demonstration purposes.'
        ... }
        >>> dep = zen.depositions.create(metadata=meta)
        >>> print(dep.id)  # print the deposition id

        2. Retrieve an existing Zenodo deposition by id:

        >>> deposition_id = dep.id
        >>> existing_dep = zen.depositions.retrieve(deposition_id)
        
        3. Modifying deposition metadata
        
        >>> dep.metadata.title = 'New Deposition Title'
        >>> dep.metadata.access_right.set_open('cc-by')
        >>> dep.update()  # Commit changes
        
        Discard the deposition example.
        
        >>> dep.discard()
    
    """ 
    def __init__(self, api: Zenodo, data: Dict[str,Any]) -> None: # type: ignore
        self._api = api
        if 'id' not in data:
            raise ValueError(f"Invalid `data` parameter. Value must have 'id' key.")
        if 'files' not in data:
            raise ValueError(f"Invalid `data` parameter. Value must have 'files' key.")
        super().__init__(data)
        self._data: Dict[str,Any] = data
        self._files = DepositionFiles(self, data['files'])
    
    def __repr__(self) -> str:
        info = dict(id=self._data['id'], title=self._data['title'], state=self._data['state'])
        return f"<Deposition: {info}>"
    
    def __len__(self):
        return len(self._files)
    
    def __getitem__(self, key: int) -> BaseFile:
        return self._files[key]
    
    def __iter__(self) -> Iterator[BaseFile]:
        for file in self._files:
            yield file
    
    def __contains__(self, item: BaseFile):
        return item.filename in self._files._index and \
            (self._files._index[item.filename].checksum is None or \
            (item.checksum is not None and \
                item.checksum == self._files._index[item.filename].checksum))
    
    def refresh(self) -> Self:
        """Refresh the Deposition Data from Zenodo.
         
        This method sends a request to the Zenodo API to fetch the most up-to-date details
        about the deposition, including metadata, files, and links. It then updates the 
        current Deposition object with the refreshed data.
        
        Returns: 
            Deposition: The current refreshed Deposition object. 
        
        """ 
        self.__init__(self._api, self._api.api.retrieve_deposition(self._data['id']))
        return self
    
    def update(self, metadata: Optional[Union[Metadata,Dict[str,Any]]]=None,
               replacements: Optional[Dict[str,Any]]=None) -> Self:
        """Update the metadata of the deposition on Zenodo.
        
        This method allows you to update the metadata of the deposition on the Zenodo platform.
        You can provide new metadata as a dictionary. If no metadata is provided, the existing
        metadata of the deposition will be used. The replacement argument is used to render
        the metadata before updating. For more details, see `Metadata.render()` method.
        
        Args:
            metadata (Optional[Union[Metadata,Dict[str,Any]]]=None): The new metadata to update 
                the deposition.
            replacements (Optional[Dict[str,Any]]=None): A dictionary of placeholder replacements. 
                If not provided, an empty dictionary is used.
        
        Returns: 
            Deposition: The current Deposition object with updated metadata. 
        
        """
        if metadata is None:
            metadata = self.metadata
        if isinstance(metadata, __metadata__.Metadata):
            metadata = metadata.render(replacements)
        try:
            self.__init__(self._api, self._api.api.update_deposition(self._data['id'], metadata))
        except json.JSONDecodeError as e:
            self._files.invalidate()
        return self
    
    def delete(self) -> None:
        """Delete the deposition from Zenodo.
        """ 
        try:
            self._api.api.delete_deposition(self._data['id'])
        except json.JSONDecodeError as e:
            pass
    
    def publish(self) -> Self:
        """Publish the deposition on Zenodo.
        
        Returns: 
            Deposition: The current Deposition object. 
        
        """ 
        try:
            self.__init__(self._api, self._api.api.publish_deposition(self._data['id']))
        except json.JSONDecodeError as e:
            self._files.invalidate()
        return self
    
    def edit(self) -> Self:
        """Set the deposition to the 'edit' state on Zenodo.
        
        Returns: 
            Deposition: The current Deposition object. 
        
        """ 
        try:
            self.__init__(self._api, self._api.api.edit_deposition(self._data['id']))
        except json.JSONDecodeError as e:
            self._files.invalidate()
        return self
    
    def discard(self) -> Self:
        """Discard any edition of the deposition on Zenodo.
        
        Returns: 
            Deposition: The current Deposition object. 
        
        """ 
        try:
            self.__init__(self._api, self._api.api.discard_deposition(self._data['id']))
        except json.JSONDecodeError as e:
            self._files.invalidate()
        return self
    
    def new_version(self) -> Self:
        """Create a new version of the deposition on Zenodo.
        
        Returns: 
            Deposition: The new version of the current Deposition object. 
        
        """ 
        try:
            self.__init__(self._api, self._api.api.new_version_deposition(self._data['id']))
        except json.JSONDecodeError as e:
            self._files.invalidate()
        return self
    
    @property
    def api(self) -> Zenodo: # type: ignore
        """The Zenodo object to interact with Zenodo API.
        """ 
        return self._api
    
    @property
    def id(self) -> int:
        """The ID of the deposition.
        """ 
        return self._data['id']
    
    @property
    def doi(self) -> str:
        """The DOI of the deposition, or None if not available.
        """ 
        if 'doi' in self._data and self._data['doi'] != '':
            return self._data['doi']
        if 'prereserve_doi' in self._data['metadata']:
            return self._data['metadata']['prereserve_doi']['doi']
        return None
    
    @property
    def concept_id(self) -> str:
        """The concept ID of the deposition, or None if not available.
        """ 
        if 'conceptrecid' in self._data and self._data['conceptrecid'] != '':
            return self._data['conceptrecid']
    
    @property
    def title(self) -> str:
        """The title of the deposition.
        """ 
        if 'title' in self._data:
            return self._data['title']
        return ''
    
    @property
    def is_editing(self) -> bool:
        """Determines whether the deposition is currently in an editing state.
        """ 
        return not self._data['submitted'] or self._data['state'] == 'inprogress'
    
    @property
    def is_published(self) -> bool:
        """Determines whether the deposition was already published.
        """ 
        return self._data['submitted']
    
    @property
    def files(self) -> DepositionFiles:
        """The files of the deposition.
        """ 
        return self._files
    
    @property
    def data(self) -> Dict[str,Any]:
        """The data of the deposition as represented by Zenodo.
        """ 
        return self._data
    
    @property
    def metadata(self) -> Metadata:
        """The metadata of the deposition.
        """
        return __metadata__.Metadata(self._data)

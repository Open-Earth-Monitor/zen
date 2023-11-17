"""
This module provides various functions for loading and saving JSON files, downloading files from the web, and 
computing their checksums. It also includes functions for working with string placeholders, which is a useful feature 
for creating basic templates.

Examples:
    The primary purpose of these functions is for internal use by the package, but users can also utilize them::
    
        from zen.api import load_json, save_json, download_file, checksum
        
        # Load JSON data from a file
        data = load_json('data.json')
        
        # Create a dictionary to save as JSON
        data = {'name': 'John', 'age': 30}
        
        # Save the dictionary as JSON to a file
        save_json(data, 'data.json')
        
        # Download a file from a URL and save it locally
        url = 'https://example.com/file1.csv'
        dest_file = 'file1.csv'
        download_file(url, dest_file)
        
        # Calculate the MD5 checksum hash of a local file
        filename = 'file1.csv'
        hash_value = checksum(filename, 'md5')
        print(f"MD5 hash of file '{filename}': {hash_value}")
    
"""
from __future__ import annotations
from typing import List, Set, Dict, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib
import json
import os
import re
import requests


def load_json(file: str) -> Any:
    """
    Load JSON data from a local file.

    Args:
        file (str): The path to the JSON file.

    Returns:
        Any: Any value stored in a JSON file.
    
    """
    with open(file, 'r') as file:
        return json.load(file)

def save_json(data: Any, file: str) -> None:
    """
    Save dictionary data as JSON to a local file.

    Args:
        data (dict): Any data to be saved into a JSON file.
        file (str): The path to the target JSON file.

    Returns:
        None
    
    """
    dirname = os.path.dirname(file)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    with open(file, 'w') as file:
        json.dump(data, file, indent=4)


valid_schemas = ('http://', 'https://')

def download_file(url: str, dest_file: str) -> str:
    """Download a file from a URL and save it locally.
    
    This function downloads a file from the specified URL and saves it locally to the provided 
    destination path. It is designed to work with files accessible via HTTP or HTTPS URLs. The 
    `url` parameter should begin with a valid schema (e.g., 'https://', 'http://') to indicate the 
    location of the file.
    
    After a successful download, the function returns the local path of the downloaded file.
    
    Args:
        url (str): The URL of the file to be downloaded.
        dest_file (str): The path where the downloaded file should be saved.

    Returns:
        str: The path of the downloaded file.
    
    Raises:
        ValueError: If the file's URL doesn't start with a valid schema (e.g. 'https://', 'http://').
    
    Example:
        >>> download_file('https://example.com/file.txt', 'local_file.txt')
        'local_file.txt'
    
    """
    if not url.startswith(valid_schemas):
        raise ValueError(f"Invalid `url` parameter. URL '{url}' is invalid.")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_file, 'wb') as file:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                file.write(chunk)
    return dest_file

def checksum(filename: str, algorithm: str='md5') -> str:
    """Calculate the checksum hash of a file.
    
    This function calculates the checksum hash of a file using the specified hash algorithm. The 
    supported hash algorithms include 'md5', 'sha1', 'sha256', 'sha512', and others available in 
    the hashlib library. You can choose the algorithm by specifying it as the `algorithm` parameter.
    
    If `filename` is a local file, the function reads the file and calculates the checksum. If 
    `filename` is a URL starting with a valid schema (e.g. 'https://', 'http://'), the function 
    retrieves the file content and calculates the checksum.
    
    Args:
        filename (str): The path to the file for which to calculate the checksum. 
        algorithm (str='md5'): The hash algorithm to use.
    
    Returns:
        str: The checksum hash of the file.
    
    Raises:
        ValueError: If the filename is not a local file or not is URL starting with a 
            valid schema (e.g. 'https://', 'http://').
    
    Examples:
    
        >>> from zen.utils import checksum
        >>> checksum('examples/file1.csv', 'sha256')
        'c4cb7ab6022b9020f35efedd58109de4e63005dbc6786645d28dbfdc64dff902'
        
        >>> checksum('examples/file2.csv', 'md5')
        'edc281089341c95484c087c7b0fe8e49'
    
    """
    if not os.path.isfile(filename) and not filename.startswith(valid_schemas):
        raise ValueError(f"Invalid `filename` parameter. File '{filename}' is invalid.")
    hash_object = hashlib.new(algorithm)
    if os.path.isfile(filename):
        with open(filename, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b''):
                hash_object.update(chunk)
    if filename.startswith(valid_schemas):
        response = requests.get(filename, stream=True)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                hash_object.update(chunk)
    return hash_object.hexdigest()


placeholder_name = r'([a-zA-Z_][a-zA-Z0-9_]*)'

def replace(obj: Any, replacements: Dict[str,Any], schema: Optional[str]='zen:') -> Any:
    """Replace Placeholders in a given object
    
    A placeholder is a special identifier used within a text or data structure that serves as a temporary 
    representation. They mark values that need to be replaced with specific content or data during processing.
    This function identifies and lists all string and dictionary placeholders found within the `obj` value.
    A placeholder name must start with a letter or digit [a-zA-Z0-9] and can be followed by letters, digits, or 
    underscore character. For example, valid placeholder names include 'var1', '_age_' and 'full_name', but not
    '9fields'.
    
    There are two types of placeholders that this function can handle:
    
    - String Placeholders: These placeholders are used within strings and the placeholder name is enclosed
      within curly braces {}. For example, '{age}' within a string is a string placeholder with name 'age'.
    - Dictionary Placeholders: These placeholders are inspired by JSON reference. When a '$ref' key is 
      encountered within dictionary, and its value is an URI with schema given by `schema` 
      parameter, the placeholder name is then resolved as the remaining URI. For example, assuming
      `schema` is set to 'zen:', {'$ref': 'zen:age'} defines a dictionary placeholder
      with name 'age'.
    
    This function recursively replaces string and dictionary placeholders inside the given `obj` 
    object using a dictionary of `replacements`. All placeholders present in `obj` must 
    have corresponding values in the `replacements` dictionary. If `obj` is a list or a dictionary,
    `replace()` will recurse through each element, replacing any placeholder occurrences with
    the corresponding value from `replacements`. You can identify all placeholders in `obj` using
    the `find_placeholders()` function.
    
    String placeholder replacements always expand to strings. To expand to a different data type, 
    such as numbers, strings, lists, or dictionaries, use a dictionary placeholder. The dictionary placeholder
    replacements always expand the object containing '$ref' key by the value provided in the entry with the
    same placeholder name in `replacements` dictionary. However, all other properties in the same object 
    that holds '$ref' key are discarded during the replacement process to ensure consistency and prevent 
    unexpected combinations of properties.
    
    Args:
        obj (Any): The data object containing strings or dictionary placeholders to be replaced.
        replacements (Dict[str, Any]): A dictionary mapping placeholder names to their replacement values.
        schema (Optional[str]='zen:'): URI schema to match dictionary placeholders. None value
        disable dictionary placeholders.

    Returns:
        Any: The data object with replaced string placeholders.
    
    Examples:
        Given a dictionary with placeholders and a replacement dictionary:
        
        >>> data = {'name': '{person}', 'age': '{years}'}
        >>> replacements = {'person': 'Alice', 'years': 25}
        
        Calling `replace(data, replacements)` will replace placeholders in the dictionary:
        
        >>> result = replace(data, replacements)
        >>> print(result)
        {'name': 'Alice', 'age': 25}
        
        The function can handle nested dictionaries and lists:
        
        >>> data = {'name': 'Hello, {name}!', 'info': {'age': '{age}'}, 'scores': [85, 90, '{score}']}
        >>> replacements = {'name': 'Alice', 'age': 25, 'score': 95}
        
        Calling `replace(data, replacements)` will recursively replace placeholders:
        
        >>> result = replace(data, replacements)
        >>> print(result)
        {'name': 'Hello, Alice!', 'info': {'age': 25}, 'scores': [85, 90, '95']}

        Note that 'score' placeholder was converted to string as it is a string placeholder, despite the
        replacing value is a number. To replace values to types other than strings, please use 
        dictionary placeholders.
        
        Dictionary placeholder examples:
        
        >>> data = {
            "$ref": "zen:external_ref",
            "name": "John",
            "age": 30
        }
        
        In this example, the '$ref' key replaces the entire object with the content of 'zen:external_ref', 
        and the "name" and "age" properties are discarded.
        
        Dictionary Placeholder Example:
        
        >>> data = {'name': 'Hello, {name}!', 'info': {'$ref': 'zen:info', 'scores': [85, 90, {'$ref': zen:score}]}}
        >>> replacements = {'name': 'Alice', 'info': {'age': 25}, 'score': 95}
        
        Calling `replace(data, replacements)` will recursively replace placeholders. However, 'scores' key
        is discarded on "info" placeholder replacement.
        
        >>> result = replace(data, replacements)
        >>> print(result)
        {'name': 'Hello, Alice!', 'info': {'age': 25}}

    """
    if isinstance(obj, str):
        for placeholder, value in replacements.items():
            obj = obj.replace(f"{{{placeholder}}}", str(value))
    elif isinstance(obj, dict):
        # Treat also dictionary placeholders
        if schema is not None and '$ref' in obj and isinstance(obj['$ref'], str):
            placeholder_dict = schema + placeholder_name
            ref: str = obj['$ref']
            if ref.startswith(schema):
                if not re.fullmatch(placeholder_dict, ref):
                    raise ValueError(f"Invalid placeholder name '{ref}'.")
                ref = ref[len(schema):]
                if ref in replacements:
                    return replacements[ref]
        else:
            for key, value in obj.items():
                obj[key] = replace(value, replacements)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = replace(item, replacements)
    return obj

def find_placeholders(obj: Any, schema: Optional[str]='zen:') -> Set[str]:
    """Find Placeholders in Data Object
    
    A placeholder is a special identifier used within a text or data structure that serves as a temporary 
    representation. They mark values that need to be replaced with specific content or data during processing.
    This function identifies and lists all string and dictionary placeholders found within the `obj` value.
    A placeholder name must start with a letter or digit [a-zA-Z0-9] and can be followed by letters, digits, or 
    underscore character. For example, valid placeholder names include 'var1', '_age_' and 'full_name', but not
    '9fields'.
    
    There are two types of placeholders that this function can handle:
    
    - String Placeholders: These placeholders are used within strings and the placeholder name is enclosed 
      within curly braces {}. For example, '{age}' within a string is a string placeholder with name 'age'.
    - Dictionary Placeholders: These placeholders are inspired by JSON reference. When a '$ref' key is 
      encountered within dictionary, and its value is an URI with schema given by `schema` 
      parameter, the placeholder name is then resolved as the remaining URI. For example, assuming
      `schema` is set to 'zen:', {'$ref': 'zen:age'} defines a dictionary placeholder
      with name 'age'.
    
    This function recursively search string and dictionary placeholders inside the given `obj`. 
    As the result of this function is a Set, it gives just one entry per placeholder even if that specific
    placeholder is used more than once in the `obj`.
    
    Args:
        obj (Any): Any data containing strings placeholders or dictionary placeholders to be identified.
        schema (Optional[str]='zen:'): URI schema to match dictionary placeholders. None value
        disable dictionary placeholders.
    
    Returns:
        Set[str]: A set containing all placeholder names found in the `obj` value.
    
    Examples:
        Given a data object with placeholders:
        
        >>> data = {'message': 'Hello, {name}!', 'info': {'score': '{score}', '$ref': 'zen:var1'}}
        
        Calling `find_placeholders(data)` will identify the placeholders:
        
        >>> placeholders = find_placeholders(data)
        >>> print(placeholders)
        {'name', 'score', 'var1'}
        
        Note that in this example, the expantion of "var1" dictionary placeholder will discard the
        'score' key.
        
        The function can handle nested dictionaries and lists:
        
        >>> data_list = [{'message': 'Greetings, {greet}!'}, 'Great day, {day}!']
        
        Calling `find_placeholders(data_list)` will identify placeholders in nested structures:
        
        >>> placeholders = find_placeholders(data_list)
        >>> print(placeholders)
        {'greet', 'day'}
    
    """
    placeholder_string = r'\{' + placeholder_name + r'\}'
    placeholders = set()
    if isinstance(obj, str):
        placeholders.update(set(re.findall(placeholder_string, obj)))
    elif isinstance(obj, dict):
        # Treat also dictionary placeholders
        if schema is not None and '$ref' in obj and isinstance(obj['$ref'], str):
            placeholder_dict = schema + placeholder_name
            ref: str = obj['$ref']
            if ref.startswith(schema):
                if not re.fullmatch(placeholder_dict, ref):
                    raise ValueError(f"Invalid placeholder name '{ref}'.")
                ref = ref[len(schema):]
                placeholders.update([ref])
        else:
            for _, value in obj.items():
                placeholders.update(find_placeholders(value))
    elif isinstance(obj, list):
        for item in obj:
            placeholders.update(find_placeholders(item))
    return placeholders

def date_seq(start_date: str, end_date: str, delta: relativedelta, date_format: str='%Y%m%d', 
             feb29: bool=True) -> List[str]:
    """Date sequence.
    
    Generates a sequence of dates between the start and end dates with a specified time delta.
    This function takes a start date and an end date, and a time interval (delta) to generate a 
    sequence of dates. It returns a list of formatted dates, with an option to exclude February 
    29th if desired.
    
    Args:
        start_date (str): The start date of the sequence in the format specified by date_format.
        end_date (str): The end date of the sequence in the format specified by date_format.
        delta (relativedelta): The time difference between each date in the sequence.
        date_format (str='%Y%m%d'): The format of the dates in the sequence.
        feb29 (bool=True): Whether to include or exclude February 29th in the sequence.

    Returns:
        list: A list of dates in the format specified by date_format.
    
    Example:
        >>> from dateutil.relativedelta import relativedelta
        >>> start_date = "20230101"
        >>> end_date = "20231231"
        >>> delta = relativedelta(months=1)  # Generates dates 30 days apart
        >>> date_sequence = date_seq(start_date, end_date, delta)
        >>> print(date_sequence)
        ['20230101', '20230201', '20230301', '20230401', '20230501', ...]
    
    """
    if isinstance(start_date, str):
        start_date: datetime = datetime.strptime(start_date, date_format)
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, date_format)
    if not isinstance(start_date, datetime):
        raise TypeError('Invalid `start_date` parameter. Expecting `str` but got a ' +
                        f'`{type(start_date)}` instead.')
    if not isinstance(end_date, datetime):
        raise TypeError('Invalid `end_date` parameter. Expecting `str` but got a ' +
                        f'`{type(end_date)}` instead.')
    date_sequence = []
    current_date = start_date
    steps = 1
    while current_date <= end_date:
        if not feb29 and current_date.month == 2 and current_date.day == 29:
            current_date = current_date.replace(day=28)
        date_sequence.append(current_date.strftime(date_format))
        current_date = start_date + delta * steps
        steps += 1
    return date_sequence

def is_iso8601_date(value: str) -> bool:
    """
    Check if a given string represents a date in ISO 8601 format (YYYY-MM-DD).

    Args:
        value (str): The string to be checked for ISO 8601 date format.

    Returns:
        bool: True if the input string is in ISO 8601 date format, False otherwise.
    """
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def is_iso8601_datetime(value: str) -> bool:
    """
    Check if a given string represents a date time in ISO 8601 format 
    (YYYY-MM-DD HH:MM:SS.mmmmmm-HH:MM).

    Args:
        value (str): The string to be checked for ISO 8601 date time format.

    Returns:
        bool: True if the input string is in ISO 8601 date time format, False otherwise.
    """
    value = value.replace('T', ' ')
    try:
        if len(value) == 19:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        elif len(value) == 19+6:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S%z')
        elif len(value) == 19+7:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        else:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f%z')
        return True
    except ValueError:
        return False

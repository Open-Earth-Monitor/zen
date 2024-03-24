"""
This module was designed to facilitate the management of metadata for various types of content that 
can be deposited on Zenodo. It defines several classes that encapsulate different content types, 
such as datasets, publications, images, posters, presentations, videos, software, lessons, and 
physical objects. These classes provide a structured way to create and manage metadata for Zenodo 
depositions. The module includes methods for creating instances of these metadata classes and 
rendering them with specified replacements for placeholders.

Examples:
    ::
        
        from zen.metadata import Dataset, Creators, Placeholder
        
        # Creating a dataset metadata instance
        meta = Dataset(
            title='My Dataset',
            description='Description of the dataset',
            creators=[Creators.new(name='Doe, John')],
            access_right='Open Access',
            license='cc-by',
            embargo_date='2024-01-01'
        )
        
        # Creating a templated metadata
        meta = Dataset(
            title='My Dataset',
            description='Description of the {the_type} dataset',
            creators=Placeholder('the_authors'),
            access_right='Open Access',
            license='cc-by',
            embargo_date='2024-01-01'
        )
        
        # Show placeholders
        print(meta.placeholders)
        #> {'the_type', 'the_authors'}
        
        # Render metadata
        replacements = {
            'the_authors': [{'name': 'Doe, John'}], 
            'the_type': 'random'
        }
        rendered_metadata = meta.render(replacements)
        
        # Creating Publication metadata from a JSON file
        meta = Dataset.from_file('examples/metadata.json')
    
"""
from __future__ import annotations
from typing import List, Dict, Set, Any, Type, Union, Optional
from typing_extensions import Self
from copy import deepcopy
import zen.utils as __utils__


def _check_instance(value: Any, value_type: Type) -> None:
    if not isinstance(value, Placeholder) and not isinstance(value, value_type):
        raise TypeError(f'Value must be `{value_type.__name__}` but got `{type(value)}`.')


class Placeholder(dict):
    """Represents a dictionary placeholder for Zenodo metadata.
    
    This class defines a placeholder for Zenodo metadata. It is designed to create a dictionary 
    with a specific structure, primarily used for creating dictionary placeholders in Zenodo 
    metadata. When you create an instance of the Placeholder class and provide a placeholder name 
    as an argument, it returns a dictionary with the structure `{'$ref': 'zen:<name>'}`.
    
    Args:
        name (str): The name of the placeholder.
    
    Exemples:
    
        1. Create a metadata for publication with two placeholders ('the_title' and 'the_description')
        
        >>> from zen.metadata import Publication, Placeholder
        >>> meta = Publication(
        ...     publication_type='article',
        ...     title=Placeholder('the_title'), 
        ...     description=Placeholder('the_description')
        ... )
        >>> print(meta.placeholders)
        {'the_title', 'the_description'}
        
        2. Rendering metadata
        
        >>> replacements = {
        ...     'the_title': 'any title', 
        ...     'the_description': 'any description'
        ... }
        >>> meta.render(replacements)
    
    """
    json_key = '$ref'
    schema = 'zen:'
    
    def __init__(self, name: str) -> None:
        super().__init__({Placeholder.json_key: f'{Placeholder.schema}{name}'})


class _MetaBase:
    @classmethod
    def new(cls, *args, **kwargs) -> Any:
        if len(args) > 0:
            return args[0]
        return {k: v for k, v in kwargs.items() if v is not None}
    
    def __init__(self, data: Optional[Dict[str,Any]]=None, key: str=None) -> None:
        if data is None:
            data = dict()
        self._data = data
        self._key = key
    
    def __repr__(self) -> str:
        return str(self.data)
    
    def set(self, value: List[Any]) -> Self:
        self._data[self._key] = value
        return self
    
    @property
    def data(self) -> Dict[str,Any]:
        if self._key not in self._data:
            return None
        return self._data[self._key]


class _MetaBaseList(_MetaBase):
    def __init__(self, data: Optional[Dict[str,List[Any]]]=None, key: str=None) -> None:
        super().__init__(data, key)
        self._data: Dict[str,List[Any]] = self._data
    
    def clear(self) -> Self:
        self.set([])
        return self
    
    def add(self, *args, **kwargs) -> Self:
        if not self._key in self._data:
            self._data[self._key] = list()
        if isinstance(self._data[self._key], Placeholder):
            raise ValueError('Cannot change placeholders values. Please, use `render()` method ' + 
                             'to replace placeholders or `set()` method to redefine the value.')
        entry = self.new(*args, **kwargs)
        self._data[self._key].append(entry)
        return self
    
    def set(self, value: List[Any]) -> Self:
        self._data[self._key] = value
        return self
    
    @property
    def data(self) -> List[Any]:
        if self._key not in self._data:
            return list()
        return super().data


class _MetaBaseObject(_MetaBase):
    def __init__(self, data: Dict[str,Dict[str, Any]], key: str=None) -> None:
        super().__init__(data, key)
        self._data: Dict[str,List[Any]] = data
    
    def set(self, value: Dict[str, Any]) -> Self:
        self._data[self._key] = value
        return self
    
    @property
    def data(self) -> Dict[str, Any]:
        if self._key not in self._data:
            return dict()
        return super().data


class _MetaBaseListString(_MetaBaseList):
    def __init__(self, data: Dict[str,List[str]], key: str=None) -> None:
        super().__init__(data, key, list())
        self._data: Dict[str,List[str]] = self._data
    
    def set(self, value: List[str]) -> Self:
        if not isinstance(value, Placeholder):
            if not isinstance(value, list):
                raise TypeError(f'Value must be `list` but got `{type(value)}`.')
            value = [self.new(*v) for v in value]
        return super().set(value)
    
    @property
    def data(self) -> List[str]:
        return super().data


class _MetaBaseListObject(_MetaBaseList):
    def __init__(self, data: Dict[str,List[Dict[str,Any]]], key: str=None) -> None:
        super().__init__(data, key)
        self._data: Dict[str,List[Dict[str,Any]]] = self._data
    
    def set(self, value: List[Dict[str,Any]]) -> Self:
        if not isinstance(value, Placeholder):
            if not isinstance(value, list):
                raise TypeError(f'Value must be `list` but got `{type(value)}`.')
            value = [self.new(**v) for v in value]
        return super().set(value)
    
    @property
    def data(self) -> List[Dict[str,Any]]:
        return super().data


class Creators(_MetaBaseListObject):
    """Represents a list of creators associated with a Zenodo deposition.
    
    This helper class class provides methods for managing a list of creators, which are individuals 
    or entities who have contributed to a Zenodo deposition. Creators can be associated with names, 
    affiliations, ORCID iDs, and GND identifiers.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    Examples:
    
        1. Create a new Zenodo deposition with default metadata:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='your_api_token')
        >>> dep = zen.depositions.create()
        >>> dep.metadata
        
        2. Add new creators
        
        >>> from zen.metadata import Creators
        >>> dep.metadata.creators.add('Doe, John', 'Zenodo')
        >>> dep.metadata.creators.add('Mae, Anna', 'Zenodo')
        >>> # This will duplicate the first author
        >>> dep.metadata.creators.add('Doe, John', 'Zenodo')
        
        3. Alternative way to set creators
        
        >>> dep.metadata.creators = [
        ...     Creators.new('Doe, John', 'Zenodo'),
        ...     Creators.new('Mae, Anna', 'Zenodo')
        ... ]
        
        This will produce the same result as above.
        
        Discard the deposition example.
        
        >>> dep.discard()
    
    """
    @classmethod
    def new(cls, name: str, affiliation: Optional[str]=None, 
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> Dict[str,str]:
        """Returns a new creator dictionary.
        
        Creates a new creator with the provided information and returns the creator's data as a 
        dictionary.
        
        Args:
            name (str): The name of the creator.
            affiliation (Optional[str]=None): The affiliation of the creator. Default is None.
            orcid (Optional[str]=None): The ORCID identifier of the creator. Default is None.
            gnd (Optional[str]=None): The GND identifier of the creator. Default is None.
        
        Returns:
            Dict[str,str]: A dictionary containing the creator's data.
        
        """
        return super(cls, cls).new(name=name, affiliation=affiliation, orcid=orcid, gnd=gnd)
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'creators')
    
    def clear(self) -> Creators:
        """Clears the creators list.
        
        Starts a new empty creators list.
        
        Returns:
            Creators: An empty Creators object.
        
        """
        return super().clear()
    
    def add(self, name: str, affiliation: Optional[str]=None, 
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> Creators:
        """Adds a new creator to the creators list.
        
        Adds a new creator to the list with the provided information and returns the updated 
        Creators object.
        
        Args:
            name (str): The name of the creator.
            affiliation (Optional[str]): The affiliation of the creator. Default is None.
            orcid (Optional[str]): The ORCID identifier of the creator. Default is None.
            gnd (Optional[str]): The GND identifier of the creator. Default is None.
        
        Returns:
            Creators: An updated Creators object with the new creator added to the list.
        
        """
        return super().add(name=name, affiliation=affiliation, orcid=orcid, gnd=gnd)


class AccessRight(_MetaBase):
    """Represents the access rights of a Zenodo deposition.
    
    This helper class class provides methods to define the access rights of a Zenodo deposition.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
        default_license (str): The default license to be used when access is set to 'open'.
    
    """
    access_rights = [
        'open',
        'embargoed',
        'restricted',
        'closed'
    ]
    
    def __init__(self, data: Dict[str,Any], default_license: str) -> None:
        super().__init__(data)
        self._default_license = default_license
    
    def set_open(self, license: str) -> None:
        """Set the access right to 'open' and specify a license.
        
        Args:
            license (str): The license for the deposition.
        
        """
        access = dict(access_right='open', license=license)
        self._data.update(access)
    
    def set_embargoed(self, license: str, embargo_date: str=None) -> None:
        """Set the access right to 'embargoed' and specify a license and, optionally, an embargo date.
        
        Args:
            license (str): The license for the deposition.
            embargo_date (str, optional): The date when the deposition will become publicly accessible.
        
        """
        access = dict(access_right='embargoed', license=license)
        if not embargo_date is None:
            access['embargo_date'] = embargo_date
        self._data.update(access)
    
    def set_restricted(self, access_conditions: str) -> None:
        """Set the access right to 'restricted' and specify access conditions.
        
        Args:
            access_conditions (str): Access conditions for the deposition.
        
        """
        access = dict(access_right='restricted', access_conditions=access_conditions)
        self._data.update(access)
    
    def set_closed(self) -> None:
        """Set the access right to 'closed'.
        """
        access = dict(access_right='closed')
        self._data.update(access)
    
    def set(self, value: str) -> None:
        """Set the access right to the specified value.
        
        Args:
            value (str): The desired access right value.

        Raises:
            ValueError: If the specified value is not a valid access right.
        
        """
        if not isinstance(value, Placeholder):
            _check_instance(value, str)
            if not value in AccessRight.access_rights:
                raise ValueError('Invalid `access_right` value. Please, see `access_rights` attribute for supported options.')
        self._data['access_right'] = value
    
    @property
    def data(self) -> str:
        """Get the access right data.

        If the 'access_right' is not present in the data, it defaults to 'open' with the default license.
        
        """
        if 'access_right' not in self._data:
            self.set_open(self._default_license)
        return self._data['access_right']


class Keywords(_MetaBaseListString):
    """Represents a list of keywords associated with a Zenodo deposition.

    This helper class provides methods for managing and manipulating keywords.

    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, keyword: str) -> str:
        """Create a new keyword
        
        Args:
            keyword (str): The keyword to create.
        
        Returns:
            str: The keyword.
        
        Raises:
            ValueError: If the provided keyword is not a string.
        
        """
        _check_instance(keyword, str)
        return keyword
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'keywords')
    
    def add(self, keyword: str) -> Keywords:
        """Add a keyword to the list
        
        Args:
            keyword (str): The keyword to add.

        Returns:
            Keywords: The updated Keywords instance.

        Raises:
            ValueError: If the provided keyword is not a string.
        
        """
        return super().add(keyword)


class RelatedIdent(_MetaBaseListObject):
    """Represents a list of related identifiers associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating related identifiers, their 
    relations, and resource types.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    supported_identifiers = [
        'DOI',
        'Handle',
        'ARK',
        'PURL',
        'ISSN',
        'ISBN',
        'PubMed ID',
        'PubMed Central ID',
        'ADS Bibliographic Code',
        'arXiv',
        'Life Science Identifiers (LSID)',
        'EAN-13',
        'ISTC',
        'URNs and URLs'
    ]
    
    relations = [
        'isCitedBy',
        'cites',
        'isSupplementTo',
        'isSupplementedBy',
        'isContinuedBy',
        'continues',
        'isDescribedBy',
        'describes',
        'hasMetadata',
        'isMetadataFor',
        'isNewVersionOf',
        'isPreviousVersionOf',
        'isPartOf',
        'hasPart',
        'isReferencedBy',
        'references',
        'isDocumentedBy',
        'documents',
        'isCompiledBy',
        'compiles',
        'isVariantFormOf',
        'isOriginalFormof',
        'isIdenticalTo',
        'isAlternateIdentifier',
        'isReviewedBy',
        'reviews',
        'isDerivedFrom',
        'isSourceOf',
        'requires',
        'isRequiredBy',
        'isObsoletedBy',
        'obsoletes'
    ]
    
    @classmethod
    def new(cls, identifier: str, relation: str, resource_type: str) -> Dict[str,str]:
        """Create a new related identifier entry.

        Args:
            identifier (str): The related identifier (e.g., DOI, Handle, ARK, etc.).
            relation (str): The relation between the identifier and the deposition.
            resource_type (str): The type of the related resource.

        Returns:
            Dict[str,str]: A dictionary representing the related identifier entry.

        Raises:
            ValueError: If the provided identifier, relation, or resource type is not supported.
        
        """
        if not identifier in RelatedIdent.supported_identifiers:
            raise ValueError('Invalid `identifier` parameter. Please, see `supported_identifiers` ' +
                             'attribute for supported options.')
        if not relation in RelatedIdent.relations:
            raise ValueError('Invalid `relation` parameter. Please, see `relations` attribute for ' + 
                             'supported options.')
        return super(cls, cls).new(identifier=identifier, relation=relation, resource_type=resource_type)
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'related_identifiers')
    
    def clear(self) -> RelatedIdent:
        """Clears the related identifier list.
        
        Starts a new empty related idenfier list.
        
        Returns:
            RelatedIdent: An empty RelatedIdent object.
        
        """
        return super().clear()
    
    def add(self, identifier: str, relation: str, resource_type: str) -> RelatedIdent:
        """Add a new related identifier entry to the list.

        Args:
            identifier (str): The related identifier (e.g., DOI, Handle, ARK, etc.).
            relation (str): The relation between the identifier and the deposition.
            resource_type (str): The type of the related resource.

        Returns:
            RelatedIdent: The updated RelatedIdent instance.

        Raises:
            ValueError: If the provided identifier, relation, or resource type is not supported.
        
        """
        return super().add(identifier=identifier, relation=relation, resource_type=resource_type)


class Contributors(_MetaBaseListObject):
    """Represents a list of contributors associated with a Zenodo deposition.

    This helper class provides methods for managing and manipulating contributor information, 
    including name, type, affiliation, ORCID, and GND.

    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    contributor_types = [
        'ContactPerson',
        'DataCollector',
        'DataCurator',
        'DataManager,Distributor',
        'Editor',
        'HostingInstitution',
        'Producer',
        'ProjectLeader',
        'ProjectManager',
        'ProjectMember',
        'RegistrationAgency',
        'RegistrationAuthority',
        'RelatedPerson',
        'Researcher',
        'ResearchGroup',
        'RightsHolder,Supervisor',
        'Sponsor',
        'WorkPackageLeader',
        'Other'
    ]
    
    @classmethod
    def new(cls, name: str, type: str, affiliation: Optional[str]=None,
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> Dict[str,str]:
        """Create a new contributor entry.
        
        Args:
            name (str): The name of the contributor.
            type (str): The type of contributor (e.g., 'ContactPerson', 'DataCollector', etc.).
            affiliation (Optional[str]): The affiliation of the contributor.
            orcid (Optional[str]): The ORCID identifier of the contributor.
            gnd (Optional[str]): The GND identifier of the contributor.
        
        Returns:
            Dict[str,str]: A dictionary representing the contributor entry.
        
        Raises:
            ValueError: If the provided contributor type is not supported.
        
        """
        if not type in Contributors.contributor_types:
            raise ValueError('Invalid `type` parameter. Please, see `contributor_types` ' + 
                             'attribute for supported options.')
        return super(cls, cls).new(name=name, type=type, affiliation=affiliation, orcid=orcid, gnd=gnd)
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'contributors')
    
    def clear(self) -> Contributors:
        """Clears the contributors list.
        
        Starts a new empty contributors list.
        
        Returns:
            Contributors: An empty Contributors object.
        
        """
        return super().clear()
    
    def add(self, type: str, name: str, affiliation: Optional[str]=None, 
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> Contributors:
        """Add a new contributor entry to the list.
        
        Args:
            type (str): The type of contributor (e.g., 'ContactPerson', 'DataCollector', etc.).
            name (str): The name of the contributor.
            affiliation (Optional[str]=None): The affiliation of the contributor.
            orcid (Optional[str]=None): The ORCID identifier of the contributor.
            gnd (Optional[str]=None): The GND identifier of the contributor.
        
        Returns:
            Contributors: The updated Contributors instance.
        
        Raises:
            ValueError: If the provided contributor type is not supported.
        
        """
        return super().add(name=name, type=type, affiliation=affiliation, orcid=orcid, gnd=gnd)


class References(_MetaBaseListString):
    """Represents a list of references associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating references.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, reference: str) -> str:
        """Create a new reference entry.
        
        Args:
            reference (str): The reference to create.
        
        Returns:
            str: The reference.
        
        Raises:
            ValueError: If the provided reference is not a string.
        
        """
        _check_instance(reference, str)
        return reference
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'references')
    
    def add(self, reference: str) -> References:
        """Add a reference to the list.
        
        Args:
            reference (str): The reference to add.
        
        Returns:
            References: The updated References instance.
        
        Raises:
            ValueError: If the provided reference is not a string.
        
        """
        return super().add(reference)


class Communities(_MetaBaseListObject):
    """Represents a list of communities associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating community identifiers.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, identifier: str) -> Dict[str,str]:
        """Create a new community entry.
        
        Args:
            identifier (str): The community identifier to create.
        
        Returns:
            Dict[str,str]: A dictionary representing the community entry.
        
        """
        return super(cls, cls).new(identifier=identifier)
        
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'communities')
    
    def clear(self) -> Communities:
        """Clears the community identifier list.
        
        Starts a new empty community identifier list.
        
        Returns:
            Communities: An empty Communities object.
        
        """
        return super().clear()
    
    def add(self, identifier: str) -> Communities:
        """Add a community identifier entry to the list.
        
        Args:
            identifier (str): The community identifier to add.
        
        Returns:
            Communities: The updated Communities instance.
        
        """
        return super().add(identifier=identifier)


class Grants(_MetaBaseListObject):
    """Represents a list of grants associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating grant identifiers.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, id: str) -> Dict[str,str]:
        """Create a new grant entry.
        
        Args:
            id (str): The grant identifier to create.
        
        Returns:
            Dict[str,str]: A dictionary representing the grant entry.
        
        """
        return super(cls, cls).new(id=id)
        
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'grants')
    
    def clear(self) -> Grants:
        """Clears the grant identifier list.
        
        Starts a new empty grant identifier list.
        
        Returns:
            Grants: An empty Grants object.
        
        """
        return super().clear()
    
    def add(self, id: str) -> Grants:
        """Add a grant identifier entry to the list
        
        Args:
            id (str): The grant identifier to add.
        
        Returns:
            Grants: The updated Grants instance.
        
        """
        return super().add(id=id)


class Subjects(_MetaBaseListObject):
    """Represents a list of subjects associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating subject information, including term, 
    identifier, and scheme.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, term: str, identifier: str, scheme: Optional[str]=None) -> Dict[str,str]:
        """Create a new subject entry.
        
        Args:
            term (str): The subject term.
            identifier (str): The subject identifier.
            scheme (Optional[str]=None): The subject scheme (if available).
        
        Returns:
            Dict[str,str]: A dictionary representing the subject entry.
        
        """
        return super(cls, cls).new(term=term, identifier=identifier, scheme=scheme)
        
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'subjects')
    
    def clear(self) -> Subjects:
        """Clears the subject list.
        
        Starts a new empty subject list.
        
        Returns:
            Subjects: An empty Subjects object.
        
        """
        return super().clear()
    
    def add(self, term: str, identifier: str, scheme: Optional[str]=None) -> Subjects:
        """Add a subject entry to the list.
        
        Args:
            term (str): The subject term.
            identifier (str): The subject identifier.
            scheme (Optional[str]=None): The subject scheme (if available).
        
        Returns:
            Subjects: The updated Subjects instance.
        
        """
        return super().add(term=term, identifier=identifier, scheme=scheme)


class Locations(_MetaBaseListObject):
    """Represents a list of locations associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating location information, 
    including place, latitude, longitude, and description.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, place: str, lat: Optional[float]=None, lon: Optional[float]=None, 
            description: Optional[str]=None) -> Dict[str,Union[str,float]]:
        """Create a new location entry.
        
        Args:
            place (str): The location's name or description.
            lat (Optional[float]=None): The latitude coordinate of the location.
            lon (Optional[float]=None): The longitude coordinate of the location.
            description (Optional[str]=None): A description of the location.
        
        Returns:
            Dict[str,Union[str,float]]: A dictionary representing the location entry.
        
        """
        return super(cls, cls).new(place=place, lat=lat, lon=lon, description=description)
        
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'locations')
    
    def clear(self) -> Locations:
        """Clears the location list.
        
        Empty location list.
        
        Returns:
            Locations: An empty Locations object.
        
        """
        return super().clear()
    
    def add(self, place: str, lat: Optional[float]=None, lon: Optional[float]=None, 
            description: Optional[str]=None) -> Locations:
        """Add a location entry to the list
        
        Args:
            place (str): The location's name or description.
            lat (Optional[float]=None): The latitude coordinate of the location.
            lon (Optional[float]=None): The longitude coordinate of the location.
            description (Optional[str]=None): A description of the location.
        
        Returns:
            Locations: The updated Locations instance.
        
        """
        return super().add(place=place, lat=lat, lon=lon, description=description)


class Dates(_MetaBaseListObject):
    """Represents a list of dates associated with a Zenodo deposition.
    
    This helper class provides methods for managing and manipulating dates, such as collection dates, 
    valid dates, and withdrawal dates.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    date_types = [
        'Collected',
        'Valid',
        'Withdrawn'
    ]
    
    @classmethod
    def new(cls, type: str, start: Optional[str]=None, end: Optional[str]=None, 
            description: Optional[str]=None) -> Dict[str,str]:
        """Create a new date entry.
        
        Args:
            type (str): The type of the date entry (e.g., 'Collected', 'Valid', 'Withdrawn').
            start (Optional[str]=None): The start date in ISO 8601 format (e.g., 'YYYY-MM-DD').
            end (Optional[str]=None): The end date in ISO 8601 format (e.g., 'YYYY-MM-DD').
            description (Optional[str]=None): A description of the date entry.
        
        Returns:
            Dict[str,str]: A dictionary representing the date entry.
        
        Raises:
            ValueError: If the provided type is not a supported date type or if date formats are invalid.
        
        """
        if not type in Dates.date_types:
            raise ValueError('Invalid `type` parameter. Please, see `date_types` attribute ' + 
                             'for supported options.')
        if start is not None:
            if not __utils__.is_iso8601_date(start):
                raise ValueError("Invalid `start` parameter. Format must be 'YYYY-MM-DD'.")
        if end is not None:
            if not __utils__.is_iso8601_date(end):
                raise ValueError("Invalid `end` parameter. Format must be 'YYYY-MM-DD'.")
        return super(cls, cls).new(type=type, start=start, end=end, description=description)
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'dates')
    
    def clear(self) -> Dates:
        """Clears the date list.
        
        Starts a new empty date list.
        
        Returns:
            Dates: An empty Dates object.
        
        """
        return super().clear()
    
    def add(self, type: str, start: Optional[str]=None, end: Optional[str]=None, 
            description: Optional[str]=None) -> Dates:
        """Add a new date entry to the list.
        
        Args:
            type (str): The type of the date entry (e.g., 'Collected', 'Valid', 'Withdrawn').
            start (Optional[str]=None): The start date in ISO 8601 format (e.g., 'YYYY-MM-DD').
            end (Optional[str]=None): The end date in ISO 8601 format (e.g., 'YYYY-MM-DD').
            description (Optional[str]=None): A description of the date entry.
        
        Returns:
            Dates: The updated Dates instance.
        
        Raises:
            ValueError: If the provided type is not a supported date type or if date formats are invalid.
        
        """
        return super().add(type=type, start=start, end=end, description=description)


class ThesisSupervisors(_MetaBaseListObject):
    """Represents a list of thesis supervisors associated with a Zenodo deposition.
    
    This helper class provides methods for managing a list of thesis supervisors.
    
    Args:
        data (Dict[str,Any]): The dictionary representing the deposition metadata.
    
    """
    @classmethod
    def new(cls, name: str, affiliation: Optional[str]=None, 
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> Dict[str,str]:
        """Creates a new supervisor dictionary.
        
        Creates a new supervisor with the provided information and returns the supervisor's 
        data as a dictionary.
        
        Args:
            name (str): The name of the supervisor.
            affiliation (Optional[str]): The affiliation of the supervisor. Default is None.
            orcid (Optional[str]): The ORCID identifier of the supervisor. Default is None.
            gnd (Optional[str]): The GND identifier of the supervisor. Default is None.
        
        Returns:
            Dict[str,str]: A dictionary containing the supervisor's data.
        """
        return super(cls, cls).new(name=name, affiliation=affiliation, orcid=orcid, gnd=gnd)
    
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data, 'thesis_supervisors')
    
    def clear(self) -> ThesisSupervisors:
        """Clears the supervisor list.
        
        Starts a new empty supervisor list.
        
        Returns:
            ThesisSupervisors: An empty ThesisSupervisors object.
        
        """
        return super().clear()
    
    def add(self, name: str, affiliation: Optional[str]=None, 
            orcid: Optional[str]=None, gnd: Optional[str]=None) -> ThesisSupervisors:
        """Adds a new supervisor to the list.
        
        Adds a new supervisor to the list with the provided information and returns the 
        updated ThesisSupervisors object.
        
        Args:
            name (str): The name of the supervisor.
            affiliation (Optional[str]): The affiliation of the supervisor. Default is None.
            orcid (Optional[str]): The ORCID identifier of the supervisor. Default is None.
            gnd (Optional[str]): The GND identifier of the supervisor. Default is None.
        
        Returns:
            ThesisSupervisors: An updated ThesisSupervisors object with the new supervisor added 
                to the list.
        """
        return super().add(name=name, affiliation=affiliation, orcid=orcid, gnd=gnd)


class Metadata(_MetaBaseObject):
    """Represents a Zenodo deposition metadata.
    
    Create a deposition metadata instance.
    
    Args:
        data (Optional[Dict[str,Any]]=None): The deposition dictionary where the 'metadata' key entry belongs.
    
    """
    upload_types = [
        'publication',
        'poster',
        'presentation',
        'dataset',
        'image',
        'video',
        'software',
        'lesson',
        'physicalobject',
        'other'
    ]
    
    @classmethod
    def _check_data(cls, data: Optional[Dict[str,Any]]=None) -> None:
        if data is not None and not isinstance(data, dict):
            raise TypeError(f'Invalid `data` parameter. Value must be `dict` but got `{type(data)}`.')
        if 'metadata' not in data:
            raise ValueError("Invalid `data` parameter. Value must have 'metadata' key entry.")
        metadata = data['metadata']
        if 'upload_type' in metadata and metadata['upload_type'] not in Metadata.upload_types:
            raise ValueError("Invalid 'metadata.upload_type' value. Please, see `upload_types` " + 
                             "attribute for supported options.")
        if 'embargo_date' in metadata:
            if not __utils__.is_iso8601_date(metadata['embargo_date']):
                raise ValueError("Invalid 'metadata.embargo_date' value. Format must be 'YYYY-MM-DD'.")
        if 'publication_date' in metadata:
            if not __utils__.is_iso8601_date(metadata['publication_date']):
                raise ValueError("Invalid 'metadata.publication_date' value. Format must be 'YYYY-MM-DD'.")
        
    @classmethod
    def from_file(cls, file: str) -> Metadata:
        """Create a metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Metadata: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(data)
    
    def __init__(self, data: Optional[Dict[str,Any]]=None) -> Metadata:
        Metadata._check_data(data)
        return super().__init__(data, 'metadata')
    
    def render(self, replacements: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
        """Render the metadata by replacing placeholders with provided values.
        
        This method is renders metadata with specific values by replacing placeholders with the values 
        provided in the replacements dictionary. It ensures that all required placeholders have 
        corresponding replacements and returns the updated metadata as a dictionary.
        
        Args:
            replacements (Optional[Dict[str,Any]]=None): A dictionary of placeholder replacements. 
                If not provided, an empty dictionary is used.

        Raises:
            ValueError: If any required placeholders are missing from the replacements dictionary.

        Returns:
            Dict[str,Any]: The rendered metadata with placeholders replaced by their corresponding values.
        
        """
        if replacements is None:
            replacements = dict()
        # Check if all placeholders have replacements
        placeholders = self.placeholders
        missing_placeholders = placeholders - set(replacements.keys())
        if missing_placeholders:
            raise ValueError(f"Missing replacements for placeholders: {', '.join(missing_placeholders)}")
        data = __utils__.replace(dict(**deepcopy(self.data)), replacements, Placeholder.schema)
        return data
    
    @property
    def placeholders(self) -> Set[str]:
        """List of the placeholders in the metadata.
        """
        return __utils__.find_placeholders(self.data, Placeholder.schema)
    
    @property
    def upload_type(self) -> str:
        """Type of the deposition (required field).
        
        Controlled vocabulary:
            * publication: Publication
            * poster: Poster
            * presentation: Presentation
            * dataset: Dataset
            * image: Image
            * video: Video/Audio
            * software: Software
            * lesson: Lesson
            * physicalobject: Physical object
            * other: Other
        
        """
        return self.data['upload_type']
    
    @upload_type.setter
    def upload_type(self, value: str) -> None:
        _check_instance(value, str)
        if value not in Metadata.upload_types:
            raise ValueError('Invalid `upload_type` parameter. Please, see `Metadata.upload_type` ' +
                             'attribute for supported options.')
        self.data['upload_type'] = value
    
    @property
    def publication_type(self) -> str:
        """Type of the publication (required field, if upload_type='publication').
        
        Controlled vocabulary:
            * annotationcollection: Annotation collection
            * book: Book
            * section: Book section
            * conferencepaper: Conference paper
            * datamanagementplan: Data management plan
            * article: Journal article
            * patent: Patent
            * preprint: Preprint
            * deliverable: Project deliverable
            * milestone: Project milestone
            * proposal: Proposal
            * report: Report
            * softwaredocumentation: Software documentation
            * taxonomictreatment: Taxonomic treatment
            * technicalnote: Technical note
            * thesis: Thesis
            * workingpaper: Working paper
            * other: Other
        
        """
        return self.data['publication_type']
    
    @upload_type.setter
    def publication_type(self, value: str) -> None:
        _check_instance(value, str)
        if value not in Publication.publication_types:
            raise ValueError('Invalid `publication_type` parameter. Please, see `Publication.publication_types` ' +
                             'attribute for supported options.')
        self.data['publication_type'] = value
    
    @property
    def image_type(self) -> str:
        """Type of the image (required field, if upload_type='image').
        
        Controlled vocabulary:
            * figure: Figure
            * plot: Plot
            * drawing: Drawing
            * diagram: Diagram
            * photo: Photo
            * other: Other
        
        """
        return self.data['image_type']
    
    @upload_type.setter
    def image_type(self, value: str) -> None:
        _check_instance(value, str)
        if value not in Image.image_types:
            raise ValueError('Invalid `image_type` parameter. Please, see `Image.image_types` ' +
                             'attribute for supported options.')
        self.data['image_type'] = value
    
    @property
    def title(self) -> str:
        """Title of deposition (required field).
        """
        if 'title' not in self.data:
            self.data['title'] = ''
        return self.data['title']
    
    @title.setter
    def title(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['title'] = value
    
    @property
    def description(self) -> str:
        """Abstract or description for deposition (allows HTML) (required field).
        """
        if 'description' not in self.data:
            self.data['description'] = ''
        return self.data['description']
    
    @description.setter
    def description(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['description'] = value
    
    @property
    def creators(self) -> Creators:
        """The creators/authors of the deposition (required field).
        
        Each array element is an object with the attributes:
            * name: Name of creator in the format Family name, Given names.
            * affiliation: Affiliation of creator (optional).
            * orcid: ORCID identifier of creator (optional).
            * gnd: GND identifier of creator (optional).
        
        Uses the helper class `Creators`.
        
        """
        return Creators(self.data)
    
    @creators.setter
    def creators(self, value: Union[List[Dict[str,str]],Placeholder]) -> None:
        self.creators.set(value)
        
    @property
    def access_right(self) -> AccessRight:
        """The access rights of the deposition (required field).
        
        Controlled vocabulary:
            * open: Open Access
            * embargoed: Embargoed Access
            * restricted: Restricted Access
            * closed: Closed Access
        
        Defaults to open.
        Uses the helper class `AccessRight`.
        
        """
        return AccessRight(self.data, default_license='cc-by')
    
    @access_right.setter
    def access_right(self, value: Union[str,Placeholder]) -> None:
        self.access_right.set(value)
    
    @property
    def license(self) -> Union[str,None]:
        """The deposition license.
        
        License of the data (required field if `access_right` is 'open' or 'embargoed'). The selected 
        license applies to all files in this deposition, but not to the metadata which is licensed 
        under Creative Commons Zero. 
        
        You can find the available license IDs via `Zenodo.licenses()` method. 
        
        Defaults to 'cc-zero' for datasets and 'cc-by' for everything else.
        
        """
        if 'license' in self.data:
            return self.data['license']
    
    @license.setter
    def license(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['license'] = value
    
    @property
    def embargo_date(self) -> str:
        """Date of public availability of the deposition.
        
        Date when the deposition will be made publicly available (required field if `access_right` 
        is 'embargoed').
        
        Defaults to current date.
        
        """
        if 'embargo_date' in self.data:
            return self.data['embargo_date']
    
    @embargo_date.setter
    def embargo_date(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['embargo_date'] = value
    
    @property
    def access_conditions(self) -> str:
        """Conditions under which users can access the deposition files.
        
        Specify the conditions under which you grant users access to the files in your upload. User 
        requesting access will be asked to justify how they fulfil the conditions. Based on the 
        justification, you decide who to grant/deny access. You are not allowed to charge users 
        for granting access to data hosted on Zenodo.
        
        """
        if 'access_conditions' in self.data:
            return self.data['access_conditions']
    
    @access_conditions.setter
    def access_conditions(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['access_conditions'] = value
    
    @property
    def prereserve_doi(self) -> bool:
        """Reserve a Digital Object Identifier (DOI).
        
        Set to true, to reserve a Digital Object Identifier (DOI). The DOI is automatically generated 
        by our system and cannot be changed. Also, The DOI is not registered with DataCite until you 
        publish your deposition, and thus cannot be used before then. Reserving a DOI is useful, if 
        you need to include it in the files you upload, or if you need to provide a dataset DOI to 
        your publisher but not yet publish your dataset. The response from the REST API will include 
        the reserved DOI.
        
        Defaults to True.
        
        """
        if 'prereserve_doi' in self.data:
            return self.data['prereserve_doi']
    
    @prereserve_doi.setter
    def prereserve_doi(self, value: Union[bool,Placeholder]) -> None:
        _check_instance(value, bool)
        self.data['prereserve_doi'] = value
    
    @property
    def keywords(self) -> Keywords:
        """The keywords associated with the deposition.
        
        Example: ['Keyword 1', 'Keyword 2']
        
        Uses the helper class `Keywords`
        
        """
        return Keywords(self.data)
    
    @keywords.setter
    def keywords(self, value: Union[List[str],Placeholder]) -> None:
        self.keywords.set(value)
    
    @property
    def notes(self) -> str:
        """Additional notes (allows HTML).
        """
        if 'notes' not in self.data:
            self.data['notes'] = ''
        return self.data['notes']
    
    @notes.setter
    def notes(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['notes'] = value
    
    @property
    def related_identifiers(self) -> RelatedIdent:
        """Persistent identifiers of related publications and datasets.
        
        Supported identifiers include: 
        DOI, Handle, ARK, PURL, ISSN, ISBN, PubMed ID, PubMed Central ID, ADS Bibliographic Code, arXiv, 
        Life Science Identifiers (LSID), EAN-13, ISTC, URNs and URLs. 
        
        Each array element is an object with the attributes:
            * identifier: The persistent identifier
            * relation: Relationship. Controlled vocabulary (Please, see 
              `RelatedIdent.supported_identifiers`).
            * resource_type: Type of the related resource (based on the 'upload_type', 
              'publication_type', and 'image_type' fields).

        Example: [{'relation': 'isSupplementTo', 'identifier':'10.1234/foo'},
                  {'relation': 'cites', 'identifier':'https://doi.org/10.1234/bar', 
                   'resource_type': 'image-diagram'}]. 
        
        Note the identifier type (e.g. DOI) is automatically detected, and used to validate and 
        normalize the identifier into a standard form.
        
        """
        return RelatedIdent(self.data)
    
    @related_identifiers.setter
    def related_identifiers(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.related_identifiers.set(value)
    
    @property
    def contributors(self) -> Contributors:
        """The contributors of the deposition.
        
        Lists all the contributors of the deposition (e.g. editors, data curators, etc.).
        
        Each array element is an object with the attributes:
        * name: Name of creator in the format Family name, Given names
        * type: Contributor type. Controlled vocabulary (Please, see `Contributors.contributor_types`)
        * affiliation: Affiliation of creator (optional).
        * orcid: ORCID identifier of creator (optional).
        * gnd: GND identifier of creator (optional).

        Example: [{'name':'Doe, John', 'affiliation': 'Zenodo', 'type': 'Editor' }, ...]
        
        Uses the helper class `Contributors`

        """
        return Contributors(self.data)
    
    @contributors.setter
    def contributors(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.contributors.set(value)
    
    @property
    def references(self) -> References:
        """List of references.
        
        Example: ["Doe J (2014). Title. Publisher. DOI", "Smith J (2014). Title. Publisher. DOI"]
        
        Uses the helper class `References`.
        
        """
        return References(self.data)
    
    @references.setter
    def references(self, value: Union[List[str],Placeholder]) -> None:
        self.references.set(value)
    
    @property
    def communities(self) -> Communities:
        """List of communities associated with the deposition.
        
        The owner of the community will be notified, and can either accept or reject your request. 
        
        Each array element is an object with the attributes:
            * identifier: Community identifier
        
        Example: [{'identifier':'ecfunded'}]
        
        Uses the helper class `Communities`.
        
        """
        return Communities(self.data)
    
    @communities.setter
    def communities(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.communities.set(value)
    
    @property
    def grants(self):
        """List of OpenAIRE-supported grants, which have funded the research for this deposition.
        
        Each array element is an object with the attributes:
            * id: grant ID.
        
        Example: [{'id':'283595'}] (European Commission grants only) or 
            funder DOI-prefixed: [{'id': '10.13039/501100000780::283595'}] (All grants, recommended)
        
        Accepted funder DOI prefixes:
            - Australian Research Council: 10.13039/501100000923
            - Austrian Science Fund: 10.13039/501100002428
            - European Commission: 10.13039/501100000780
            - European Environment Agency: 10.13039/501100000806
            - Academy of Finland: 10.13039/501100002341
            - Agence Nationale de la Recherche: 10.13039/501100001665
            - Aligning Science Across Parkinson's: 10.13039/100018231
            - Hrvatska Zaklada za Znanost: 10.13039/501100004488
            - Fundação para a Ciência e a Tecnologia: 10.13039/501100001871
            - Ministarstvo Prosvete, Nauke i Tehnološkog Razvoja: 10.13039/501100004564
            - Ministarstvo Znanosti, Obrazovanja i Sporta: 10.13039/501100006588
            - National Health and Medical Research Council: 10.13039/501100000925
            - National Institutes of Health: 10.13039/100000002
            - National Science Foundation: 10.13039/100000001
            - Nederlandse Organisatie voor Wetenschappelijk Onderzoek: 10.13039/501100003246
            - Research Councils: 10.13039/501100000690
            - UK Research and Innovation: 10.13039/100014013
            - Schweizerischer Nationalfonds zur Förderung der wissenschaftlichen 
              Forschung: 10.13039/501100001711
            - Science Foundation Ireland: 10.13039/501100001602
            - Social Science Research Council: 10.13039/100001345
            - Türkiye Bilimsel ve Teknolojik Araştırma Kurumu: 10.13039/501100004410
            - Wellcome Trust: 10.13039/100004440
        
        Uses the helper class `Grants`.
        
        """
        return Grants(self.data)
    
    @grants.setter
    def grants(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.grants.set(value)
    
    @property
    def subjects(self) -> Subjects:
        """The subjects associated with the deposition.
        
        Specify subjects from a taxonomy or controlled vocabulary. Each term must be uniquely 
        identified (e.g. a URL). For free form text, use the keywords field. 
        
        Each array element is an object with the attributes:
            * term: Term from taxonomy or controlled vocabulary.
            * identifier: Unique identifier for term.
            * scheme: Persistent identifier scheme for id (automatically detected).
        
        Example: [{"term": "Astronomy", "identifier": "http://id.loc.gov/authorities/subjects/sh85009003", 
                   "scheme": "url"}]
        
        Uses the helper class `Subjects`.
        
        """
        return Subjects(self.data)
    
    @subjects.setter
    def subjects(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.subjects.set(value)
    
    @property
    def version(self) -> str:
        """The version of the resource.
        
        Any Type of string will be accepted, however the suggested format is a semantically versioned 
        tag (see more details on semantic versioning at semver.org)
        
        Example: '2.1.5'
        
        """
        if 'version' in self.data:
            return self.data['version']
    
    @version.setter
    def version(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['version'] = value
    
    @property
    def language(self) -> str:
        """The main language of the record.
        
        Specify the main language of the record as ISO 639-2 or 639-3 code see Library of Congress 
        ISO 639 codes list.
        
        Example: eng
        
        """
        if 'language' in self.data:
            return self.data['language']
    
    @language.setter
    def language(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['language'] = value
    
    @property
    def locations(self) -> Locations:
        """List of locations associated with the deposition.
        
        List of locations
            * lat (double): latitude
            * lon (double): longitude
            * place (Type: string): place's name (required)
            * description (Type: string): place's description (optional)
        
        Example: [{"lat": 34.02577, "lon": -118.7804, "place": "Los Angeles"}, 
                  {"place": "Mt.Fuji, Japan", 
                   "description": "Sample found 100ft from the foot of the mountain."}]
        
        Uses the helper class `Locations`
        
        """
        return Locations(self.data)
    
    @locations.setter
    def locations(self, value: Union[List[Dict[str, Any]],Placeholder]) -> None:
        self.locations.set(value)
    
    @property
    def dates(self) -> Dates:
        """List of dates associated with the deposition.
        
        List of date intervals
            * start (ISO date Type: string): start date (*)
            * end (ISO date Type: string): end date (*)
            * type (Collected, Valid, Withdrawn): The interval's type (required)
            * description (Type: string): The interval's description (optional)
        
        Note that you have to specify at least a start or end date. For an exact date, use the 
        same value for both start and end.
        
        Example: [{"start": "2018-03-21", "end": "2018-03-25", "type": "Collected", 
                   "description": "Specimen A5 collection period."}]
        
        """
        return Dates(self.data)
    
    @dates.setter
    def dates(self, value: Union[List[Dict[str,str]],Placeholder]) -> None:
        self.dates.set(value)
    
    @property
    def method(self) -> str:
        """The methodology employed for the study or research.
        """
        if 'method' in self.data:
            return self.data['method']
    
    @method.setter
    def method(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['method'] = value
    
    @property
    def journal_title(self) -> str:
        """Journal title, if deposition is a published article.
        """
        if 'journal_title' in self.data:
            return self.data['journal_title']
    
    @journal_title.setter
    def journal_title(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['journal_title'] = value
    
    @property
    def journal_volume(self) -> str:
        """Journal volume, if deposition is a published article.
        """
        if 'journal_volume' in self.data:
            return self.data['journal_volume']
    
    @journal_volume.setter
    def journal_volume(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['journal_volume'] = value
    
    @property
    def journal_issue(self) -> str:
        """Journal issue, if deposition is a published article.
        """
        if 'journal_issue' in self.data:
            return self.data['journal_issue']
    
    @journal_issue.setter
    def journal_issue(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['journal_issue'] = value
    
    @property
    def journal_pages(self) -> str:
        """Journal pages, if deposition is a published article.
        """
        if 'journal_pages' in self.data:
            return self.data['journal_pages']
    
    @journal_pages.setter
    def journal_pages(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['journal_pages'] = value
    
    @property
    def conference_title(self) -> str:
        """Title of conference.
        
        Example: '20th International Conference on Computing in High Energy and Nuclear Physics'.
        
        """
        if 'conference_title' in self.data:
            return self.data['conference_title']
    
    @conference_title.setter
    def conference_title(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_title'] = value
    
    @property
    def conference_acronym(self) -> str:
        """Acronym of conference.
        
        Example: "CHEP'13"
        
        """
        if 'conference_acronym' in self.data:
            return self.data['conference_acronym']
    
    @conference_acronym.setter
    def conference_acronym(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_acronym'] = value
    
    @property
    def conference_dates(self) -> str:
        """Dates of conference.
        
        Conference title or acronym must also be specified if this field is specified.
        
        Example: '14-18 October 2013'
        
        """
        if 'conference_dates' in self.data:
            return self.data['conference_dates']
    
    @conference_dates.setter
    def conference_dates(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_dates'] = value
    
    @property
    def conference_place(self) -> str:
        """Place of conference in the format city, country.
        
        Conference title or acronym must also be specified if this field is specified.
        
        Example: 'Amsterdam, The Netherlands'
        
        """
        if 'conference_place' in self.data:
            return self.data['conference_place']
    
    @conference_place.setter
    def conference_place(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_place'] = value
    
    @property
    def conference_url(self) -> str:
        """URL of conference.
        
        Example: 'http://www.chep2013.org/'
        
        """
        if 'conference_url' in self.data:
            return self.data['conference_url']
    
    @conference_url.setter
    def conference_url(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_url'] = value
    
    @property
    def conference_session(self) -> str:
        """Number of session within the conference.
        
        Example: 'VI'
        
        """
        if 'conference_session' in self.data:
            return self.data['conference_session']
    
    @conference_session.setter
    def conference_session(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_session'] = value
    
    @property
    def conference_session_part(self) -> str:
        """Number of part within a session.
        
        Example: '1'
        
        """
        if 'conference_session_part' in self.data:
            return self.data['conference_session_part']
    
    @conference_session_part.setter
    def conference_session_part(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['conference_session_part'] = value
    
    @property
    def imprint_publisher(self) -> str:
        """Publisher of a book/report/chapter.
        """
        if 'imprint_publisher' in self.data:
            return self.data['imprint_publisher']
    
    @imprint_publisher.setter
    def imprint_publisher(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['imprint_publisher'] = value
    
    @property
    def imprint_isbn(self) -> str:
        """ISBN of a book/report.
        """
        if 'imprint_isbn' in self.data:
            return self.data['imprint_isbn']
    
    @imprint_isbn.setter
    def imprint_isbn(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['imprint_isbn'] = value
    
    @property
    def imprint_place(self) -> str:
        """Place of publication of a book/report/chapter in the format city, country.
        """
        if 'imprint_place' in self.data:
            return self.data['imprint_place']
    
    @imprint_place.setter
    def imprint_place(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['imprint_place'] = value
    
    @property
    def partof_title(self) -> str:
        """Title of book for chapters.
        """
        if 'partof_title' in self.data:
            return self.data['partof_title']
    
    @partof_title.setter
    def partof_title(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['partof_title'] = value
    
    @property
    def partof_pages(self) -> str:
        """Pages numbers of book.
        """
        if 'partof_pages' in self.data:
            return self.data['partof_pages']
    
    @partof_pages.setter
    def partof_pages(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['partof_pages'] = value
    
    @property
    def thesis_supervisors(self) -> str:
        """Supervisors of the thesis.
        
        Same format as for creators.
        
        Uses the helper class `ThesisSupervisors`
        
        """
        return ThesisSupervisors(self.data)
    
    @thesis_supervisors.setter
    def thesis_supervisors(self, value: Union[List[Dict[str,str]],Placeholder]) -> None:
        ThesisSupervisors.set(value)
    
    @property
    def thesis_university(self) -> str:
        """Awarding university of thesis.
        """
        if 'thesis_university' in self.data:
            return self.data['thesis_university']
    
    @thesis_university.setter
    def thesis_university(self, value: Union[str,Placeholder]) -> None:
        _check_instance(value, str)
        self.data['thesis_university'] = value


class Dataset(Metadata):
    """Represents metadata for a Dataset deposition on Zenodo.
    
    Create a Dataset metadata instance (`upload_type='dataset'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Dataset metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Dataset: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Dataset:
        data = kwargs
        data['upload_type'] = 'dataset'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))
    
    @property
    def access_right(self) -> AccessRight:
        """Get the access right for the dataset (The default is 'cc-zero').
        """
        return AccessRight(self.data, default_license='cc-zero')


class Publication(Metadata):
    """Represents metadata for a Publication deposition on Zenodo.
    
    Create a Publication metadata instance (`upload_type='publication'`).
    
    Args:
        publication_type (str): Type of the publication. One of `Publication.publication_types`.
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    publication_types = [
        'annotationcollection',
        'book',
        'section',
        'conferencepaper',
        'datamanagementplan',
        'article',
        'patent',
        'preprint',
        'deliverable',
        'milestone',
        'proposal',
        'report',
        'softwaredocumentation',
        'taxonomictreatment',
        'technicalnote',
        'thesis',
        'workingpaper',
        'other'
    ]
    
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Publication metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Publication: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, publication_type: str, 
                 title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Publication:
        if not publication_type in Publication.publication_types:
            raise ValueError('Invalid `publication_type` parameter. Please, see `publication_types` attribute for supported options.')
        data = kwargs
        data['upload_type'] = 'publication'
        data['publication_type'] = publication_type
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Image(Metadata):
    """Represents metadata for an Image deposition on Zenodo.
    
    Create an Image metadata instance (`upload_type='image'`).
    
    Args:
        image_type (str): Type of the image. One of `Image.image_types`.
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    image_types = [
        'figure',
        'plot',
        'drawing',
        'diagram',
        'photo',
        'other'
    ]
    
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create an Image metadata instance from a JSON file
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Image: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, image_type: str, 
                 title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Image:
        if not image_type in Image.image_types:
            raise ValueError('Invalid `image_type` parameter. Please, see `image_types` attribute for supported options.')
        data = kwargs
        data['upload_type'] = 'image'
        kwargs['image_type'] = image_type
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Poster(Metadata):
    """Represents metadata for a Poster deposition on Zenodo.
    
    Create a Poster metadata instance (`upload_type='poster'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Poster:
        """Create a Poster metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Poster: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Poster:
        data = kwargs
        data['upload_type'] = 'poster'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Presentation(Metadata):
    """Represents metadata for a Presentation deposition on Zenodo.
    
    Create a Presentation metadata instance (`upload_type='presentation'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Presentation metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Presentation: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Presentation:
        data = kwargs
        data['upload_type'] = 'presentation'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Video(Metadata):
    """Represents metadata for a Video deposition on Zenodo.
    
    Create a Video metadata instance (`upload_type='video'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Video metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Video: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Video:
        data = kwargs
        data['upload_type'] = 'video'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Software(Metadata):
    """Represents metadata for a Software deposition on Zenodo.
    
    Create a Software metadata instance (`upload_type='software'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Software metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Software: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Software:
        data = kwargs
        data['upload_type'] = 'software'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Lesson(Metadata):
    """Represents metadata for a Lesson deposition on Zenodo.
    
    Create a Lesson metadata instance (`upload_type='lesson'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a Lesson metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Lesson: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Lesson:
        data = kwargs
        data['upload_type'] = 'lesson'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class PhysicalObject(Metadata):
    """Represents metadata for a PhysicalObject deposition on Zenodo.
    
    Create a PhysicalObject metadata instance (`upload_type='physicalobject'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create a PhysicalObject metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            PhysicalObject: An instance of the metadata class populated with the data from 
            the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> PhysicalObject:
        data = kwargs
        data['upload_type'] = 'physicalobject'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))


class Other(Metadata):
    """Represents metadata for Other deposition on Zenodo.
    
    Create an Other metadata instance (`upload_type='other'`).
    
    Args:
        title (Optional[Union[str,Placeholder]]=None): The title of the deposition.
        description (Optional[Union[str,Placeholder]]=None): Description of the deposition (allows HTML).
        creators (Optional[Union[List[Dict[str,str]],Placeholder]]=None): List of deposition creators.
        access_right (Optional[Union[str,Placeholder]]=None): Access rights for the deposition.
        license (Optional[Union[str,Placeholder]]=None): License information for the deposition.
        embargo_date (Optional[Union[str,Placeholder]]=None): Date when the deposition will become 
            publicly accessible.
        access_conditions (Optional[Union[str,Placeholder]]=None): Custom access conditions.
        publication_date (Optional[Union[str,Placeholder]]=None): Date of publication.
        **kwargs: Additional custom metadata parameters that can be set when creating an instance 
            of this metadata class. Users can provide any extra metadata fields they need, 
            but it is recommended to consult the Zenodo API reference for a complete list 
            of allowed metadata parameters. Consult the Zenodo API reference for a comprehensive 
            list of supported metadata fields and their descriptions.
    
    """
    @classmethod
    def from_file(cls, file: str) -> Self:
        """Create an Other metadata instance from a JSON file.
        
        Args:
            file (str): The path to a JSON file containing metadata.
        
        Returns:
            Other: An instance of the metadata class populated with the data from the JSON file.
        
        Raises:
            TypeError: If the JSON file has an invalid format.
            ValueError: If the `upload_type` in the metadata is not supported.
        
        """
        data = __utils__.load_json(file)
        if not isinstance(data, dict):
            raise TypeError(f'Invalid metadata value. Value must be `dict` but got {type(data)}.')
        if 'metadata' not in data:
            data = dict(metadata=data)
        return cls(**data)
    
    def __init__(self, title: Optional[Union[str,Placeholder]]=None, 
                 description: Optional[Union[str,Placeholder]]=None, 
                 creators: Optional[Union[List[Dict[str,str]],Placeholder]]=None, 
                 access_right: Optional[Union[str,Placeholder]]=None, 
                 license: Optional[Union[str,Placeholder]]=None, 
                 embargo_date: Optional[Union[str,Placeholder]]=None, 
                 access_conditions: Optional[Union[str,Placeholder]]=None, 
                 publication_date: Optional[Union[str,Placeholder]]=None, 
                 **kwargs) -> Other:
        data = kwargs
        data['upload_type'] = 'other'
        if title is not None:
            data['title'] = title
        if description is not None:
            data['description'] = description
        if creators is not None:
            data['creators'] = creators
        if access_right is not None:
            data['access_right'] = access_right
        if license is not None:
            data['license'] = license
        if embargo_date is not None:
            data['embargo_date'] = embargo_date
        if access_conditions is not None:
            data['access_conditions'] = access_conditions
        if publication_date is not None:
            data['publication_date'] = publication_date
        if 'prereserve_doi' not in data:
            data['prereserve_doi'] = True
        return super().__init__(dict(metadata=data))

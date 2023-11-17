import unittest
from unittest.mock import patch, Mock
from zen.dataset import BaseFile, LocalFile, ZenodoFile, Dataset

class TestBaseFile(unittest.TestCase):
    @patch('zen.dataset.os.path.isdir')
    @patch('zen.dataset.download_file')
    def test_download(self, download_file_mock, os_path_isdir_mock):
        os_path_isdir_mock.return_value = True
        download_file_mock.return_value = None
        base_file = BaseFile('http://example.com/example.txt')
        base_file.download('/download_dir')
        os_path_isdir_mock.assert_called_with('/download_dir')

    def test_init_with_remote_file(self):
        data = {
            'filename': 'example.txt',
            'links': {'download': 'http://example.com/example.txt'},
            'properties': {'key1': 'value1'}
        }
        base_file = BaseFile(data)
        self.assertEqual(base_file['filename'], 'example.txt')
        self.assertEqual(base_file['links']['download'], 'http://example.com/example.txt')
        self.assertEqual(base_file['properties']['key1'], 'value1')

    def test_init_with_local_file(self):
        data = 'localfile.txt'
        base_file = BaseFile(data)
        self.assertEqual(base_file['filename'], 'localfile.txt')
        self.assertEqual(base_file['links']['download'], 'localfile.txt')
        self.assertEqual(base_file['properties'], {})

    def test_init_with_invalid_data(self):
        with self.assertRaises(TypeError):
            BaseFile(123)  # Invalid data type

    @patch('zen.dataset.os.path.isfile')
    def test_is_local(self, os_path_isfile_mock):
        os_path_isfile_mock.return_value = True
        base_file = BaseFile('localfile.txt')
        self.assertTrue(base_file.is_local)

    @patch('zen.dataset.os.path.isfile')
    def test_is_remote(self, os_path_isfile_mock):
        os_path_isfile_mock.return_value = False
        base_file = BaseFile('http://example.com/example.txt')
        self.assertTrue(base_file.is_remote)


if __name__ == '__main__':
    unittest.main()

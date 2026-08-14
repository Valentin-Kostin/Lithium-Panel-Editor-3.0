"""
Тесты для модуля xml_utils.
"""

import pytest
from pathlib import Path
from lxml import etree

from src.core.xml_utils import XMLUtils


class TestXMLUtils:
    """Тесты утилит XML."""
    
    def test_safe_parse_valid(self, sample_valid_file):
        """Тест парсинга валидного файла."""
        tree, error = XMLUtils.safe_parse(sample_valid_file, 'utf-8')
        
        assert tree is not None
        assert error is None
        assert tree.getroot() is not None
    
    def test_safe_parse_invalid(self, sample_broken_file):
        """Тест парсинга невалидного файла."""
        tree, error = XMLUtils.safe_parse(sample_broken_file, 'utf-8')
        
        assert tree is None
        assert error is not None
        assert "Ошибка синтаксиса" in error or "XML" in error
    
    def test_get_namespaces(self, sample_namespace_file):
        """Тест извлечения namespace."""
        tree, _ = XMLUtils.safe_parse(sample_namespace_file, 'utf-8')
        root = tree.getroot()
        
        namespaces = XMLUtils.get_namespaces(root)
        
        assert 'ns' in namespaces
        assert namespaces['ns'] == 'http://www.nanxing.com/scx'
    
    def test_find_elements(self, sample_valid_file):
        """Тест поиска элементов."""
        tree, _ = XMLUtils.safe_parse(sample_valid_file, 'utf-8')
        
        elements = XMLUtils.find_elements(tree, '//Material')
        
        assert len(elements) == 1
        assert elements[0].tag == 'Material'
    
    def test_validate_xml_valid(self, sample_valid_file):
        """Тест валидации валидного XML."""
        with open(sample_valid_file, 'rb') as f:
            content = f.read()
        
        is_valid, error = XMLUtils.validate_xml(content, 'utf-8')
        
        assert is_valid is True
        assert error is None
    
    def test_save_and_load(self, tmp_path, sample_valid_file):
        """Тест сохранения и загрузки."""
        tree, _ = XMLUtils.safe_parse(sample_valid_file, 'utf-8')
        
        output_path = tmp_path / "output.scx"
        success = XMLUtils.save_tree(tree, output_path, 'utf-8')
        
        assert success is True
        assert output_path.exists()
        
        loaded_tree, error = XMLUtils.safe_parse(output_path, 'utf-8')
        assert loaded_tree is not None
        assert error is None


@pytest.fixture
def sample_valid_file():
    """Фикстура с путём к валидному файлу."""
    return Path(__file__).parent / 'samples' / 'sample_valid.scx'


@pytest.fixture
def sample_broken_file():
    """Фикстура с путём к битому файлу."""
    return Path(__file__).parent / 'samples' / 'sample_broken.scx'


@pytest.fixture
def sample_namespace_file():
    """Фикстура с путём к файлу с namespace."""
    return Path(__file__).parent / 'samples' / 'sample_namespace.scx'

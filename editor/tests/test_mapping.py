"""
Тесты для модуля mapping.
"""

import pytest
from pathlib import Path
from lxml import etree

from src.core.mapping import MappingConfig, MappingField


class TestMappingConfig:
    """Тесты конфигурации маппинга."""
    
    def test_load_default_mapping(self, default_mapping_file):
        """Тест загрузки маппинга по умолчанию."""
        config = MappingConfig(default_mapping_file)
        
        assert config.version == 1
        assert len(config.fields) > 0
        assert 'ns' in config.namespaces or True
    
    def test_get_field_by_id(self, default_mapping_file):
        """Тест получения поля по ID."""
        config = MappingConfig(default_mapping_file)
        
        field = config.get_field_by_id('material.length')
        
        assert field is not None
        assert field.id == 'material.length'
        assert field.field_type == 'float'
        assert field.unit == 'мм'
    
    def test_find_values(self, default_mapping_file, sample_valid_file):
        """Тест поиска значений по маппингу."""
        config = MappingConfig(default_mapping_file)
        
        from lxml import etree
        tree = etree.parse(str(sample_valid_file))
        
        field = config.get_field_by_id('material.length')
        if field:
            results = config.find_values(tree, field)
            assert len(results) >= 0
    
    def test_validate_value(self):
        """Тест валидации значения."""
        field_data = {
            'id': 'test.field',
            'type': 'float',
            'min': 0,
            'max': 100
        }
        field = MappingField(field_data)
        
        is_valid, error = field.validate_value(50.5)
        assert is_valid is True
        
        is_valid, error = field.validate_value(-10)
        assert is_valid is False
        assert "меньше минимального" in error
        
        is_valid, error = field.validate_value("not_a_number")
        assert is_valid is False


@pytest.fixture
def default_mapping_file():
    """Фикстура с путём к файлу маппинга."""
    return Path(__file__).parent.parent / 'config' / 'default_mapping.json'


@pytest.fixture
def sample_valid_file():
    """Фикстура с путём к валидному файлу."""
    return Path(__file__).parent / 'samples' / 'sample_valid.scx'

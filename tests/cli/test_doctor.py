import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import yamlr.core.k8s_versions
from yamlr.cli.commands.doctor import handle_doctor_command

def test_k8s_matrix_strict_success(tmpdir):
    mock_args = MagicMock()
    mock_args.k8s_matrix = False
    mock_args.k8s_matrix_strict = True

    from yamlr.core.k8s_versions import K8sSupportMatrix
    fake_matrix = K8sSupportMatrix(supported_versions=['1.31'], default_recommended='1.31')

    with patch('yamlr.cli.commands.doctor.MATRIX', fake_matrix):
        
        with patch('yamlr.core.catalog_manager.CatalogManager') as MockCatalog:
            instance = MockCatalog.return_value
            instance.list_installed_versions.return_value = ['1.31']
            
            bundle_file = Path(str(tmpdir)) / "k8s_1.31.json"
            instance.get_catalog_path.return_value = bundle_file
            bundle_file.write_text("{}")
            
            console_mock = MagicMock()
            try:
                handle_doctor_command(mock_args, MagicMock(), console_mock)
            except SystemExit as sys_exit:
                assert sys_exit.code == 0
                
            calls_str = str(console_mock.print.call_args_list)
            assert "Yamlr Doctor" in calls_str

def test_k8s_matrix_strict_failure(tmpdir):
    mock_args = MagicMock()
    mock_args.k8s_matrix = False
    mock_args.k8s_matrix_strict = True

    from yamlr.core.k8s_versions import K8sSupportMatrix
    fake_matrix = K8sSupportMatrix(supported_versions=['1.30', '1.31'], default_recommended='1.31')

    with patch('yamlr.cli.commands.doctor.MATRIX', fake_matrix):
        
        with patch('yamlr.core.catalog_manager.CatalogManager') as MockCatalog:
            instance = MockCatalog.return_value
            instance.list_installed_versions.return_value = ['1.31']
            
            bundle_file = Path(str(tmpdir)) / "k8s_1.31.json"
            instance.get_catalog_path.return_value = bundle_file
            bundle_file.write_text("{}")
            
            console_mock = MagicMock()
            with pytest.raises(SystemExit) as sys_exit:
                handle_doctor_command(mock_args, MagicMock(), console_mock)
                
            assert sys_exit.value.code == 1
            calls_str = str(console_mock.print.call_args_list)
            assert "Strict matrix validation failed" in calls_str

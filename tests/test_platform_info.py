import builtins
import unittest
from unittest.mock import patch

import modules.platform_info as platform_info


class TestPlatformInfo(unittest.TestCase):
    def test_detect_torch_cuda_returns_false_when_torch_missing(self):
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'torch':
                raise ImportError('No module named torch')
            return original_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=fake_import):
            self.assertFalse(platform_info._detect_torch_cuda())

    def test_detect_onnx_providers_returns_empty_when_onnxruntime_missing(self):
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'onnxruntime':
                raise ImportError('No module named onnxruntime')
            return original_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=fake_import):
            self.assertEqual(platform_info._detect_onnx_providers(), [])


if __name__ == '__main__':
    unittest.main()

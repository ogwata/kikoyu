#!/usr/bin/env python3
"""
check_deps.py の純粋関数のオフライン単体テスト（ネットワーク不要）。
実行: python -m unittest discover -s .github/scripts
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_deps as cd  # noqa: E402


class TestCudaMajorFromRequires(unittest.TestCase):
    def test_detects_cu13(self):
        reqs = [
            "numpy",
            "nvidia-cublas-cu13==13.0.0; platform_machine == 'x86_64'",
            "nvidia-cuda-runtime-cu13",
        ]
        self.assertEqual(cd.cuda_major_from_requires(reqs), "13")

    def test_detects_cu12(self):
        reqs = ["nvidia-cublas-cu12==12.4.5.8", "filelock"]
        self.assertEqual(cd.cuda_major_from_requires(reqs), "12")

    def test_none_when_no_nvidia_dep(self):
        reqs = ["numpy", "pyyaml>=5.3"]
        self.assertIsNone(cd.cuda_major_from_requires(reqs))

    def test_handles_none_input(self):
        self.assertIsNone(cd.cuda_major_from_requires(None))

    def test_cu13_takes_precedence_over_cu12(self):
        reqs = ["nvidia-cublas-cu12", "nvidia-cudnn-cu13"]
        self.assertEqual(cd.cuda_major_from_requires(reqs), "13")


class TestHasAarch64Wheel(unittest.TestCase):
    def test_true_when_aarch64_wheel_present(self):
        urls = [
            {"filename": "ctranslate2-4.8.0-cp312-cp312-manylinux_2_28_x86_64.whl"},
            {"filename": "ctranslate2-4.8.0-cp312-cp312-manylinux_2_28_aarch64.whl"},
        ]
        self.assertTrue(cd.has_aarch64_wheel(urls))

    def test_false_when_only_x86(self):
        urls = [
            {"filename": "ctranslate2-4.8.0-cp312-cp312-manylinux_2_28_x86_64.whl"},
            {"filename": "ctranslate2-4.8.0.tar.gz"},
        ]
        self.assertFalse(cd.has_aarch64_wheel(urls))

    def test_false_on_empty(self):
        self.assertFalse(cd.has_aarch64_wheel([]))
        self.assertFalse(cd.has_aarch64_wheel(None))


class TestGrepCuda13(unittest.TestCase):
    def test_matches_space_form(self):
        text = "## v4.9.0\n- Add CUDA 13 support for Linux\n- other change\n"
        hits = cd.grep_cuda13(text)
        self.assertEqual(len(hits), 1)
        self.assertIn("CUDA 13", hits[0])

    def test_matches_hyphen_and_nospace(self):
        text = "support cuda-13 here\nand cuda13 there\n"
        self.assertEqual(len(cd.grep_cuda13(text)), 2)

    def test_no_match_for_cuda12(self):
        text = "Install CUDA 12.x to use the GPU\n"
        self.assertEqual(cd.grep_cuda13(text), [])

    def test_no_match_for_cuda133_is_still_match_prefix(self):
        # "cuda 13.0" のようにバージョン続きでもヒット扱い（言及あり、で十分）
        text = "built against CUDA 13.0 toolkit\n"
        self.assertEqual(len(cd.grep_cuda13(text)), 1)

    def test_empty(self):
        self.assertEqual(cd.grep_cuda13(""), [])
        self.assertEqual(cd.grep_cuda13(None), [])


if __name__ == "__main__":
    unittest.main()

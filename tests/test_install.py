import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def source(self,path):
        path.mkdir()
        (path/'SKILL.md').write_text('skill')
        (path/'requirements.txt').write_text('')
        (path/'local-settings.json').write_text('{"private":"do not copy"}')
        (path/'.venv').mkdir()
        return path

    def test_fresh_copy_excludes_local_state_and_installed_copy_repeats(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=self.source(p/'source');skills=p/'skills'
            r=installer.install(source,skills,True);target=Path(r['skill'])
            self.assertTrue((target/'SKILL.md').is_file())
            self.assertFalse((target/'.venv').exists())
            self.assertFalse((target/'local-settings.json').exists())
            r=installer.install(target,skills,True)
            self.assertEqual(r['dependencies'],'not checked (--skip-deps)')

    def test_preserves_existing_unrelated_install(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=self.source(p/'source');target=p/'skills/video-gif-studio';target.mkdir(parents=True)
            (target/'mine.txt').write_text('keep')
            with self.assertRaises(ValueError):installer.install(source,p/'skills',True)
            self.assertEqual((target/'mine.txt').read_text(),'keep')

    def test_same_source_symlink_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=self.source(p/'source');skills=p/'skills';skills.mkdir();target=skills/'video-gif-studio';target.symlink_to(source,target_is_directory=True)
            installer.install(source,skills,True)
            self.assertTrue(target.is_symlink())


if __name__=='__main__':unittest.main()

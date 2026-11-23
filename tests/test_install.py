"""Installation tests use isolated directories and do not install system services."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('migu_install',ROOT/'scripts/install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.skills=self.root/'installed'
        (self.root/'dependencies.json').write_text((ROOT/'dependencies.json').read_text())
        shutil.copytree(ROOT/'skills',self.root/'skills',ignore=shutil.ignore_patterns('__pycache__'))

    def test_plan_does_not_write(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),'--skills-dir',str(self.skills)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['mode'],'PLAN_ONLY')
        self.assertFalse(self.skills.exists())

    def test_analysis_install_and_idempotent_repeat(self):
        instance=installer.Installer(self.root,self.skills,'analyze')
        self.assertEqual(instance.execute(),0)
        config=json.loads((self.skills/'migu/installation.json').read_text())
        self.assertEqual(config['distribution_root'],str(self.root.resolve()))
        second=installer.Installer(self.root,self.skills,'analyze')
        self.assertEqual(second.execute(),0)
        self.assertFalse((self.root/'.runtime/backups').exists())

    def test_skill_upgrade_backs_up_and_preserves_config(self):
        dest=self.skills/'migu';dest.mkdir(parents=True)
        (dest/'SKILL.md').write_text('old user changes')
        (dest/'installation.json').write_text('{"schema_version":1,"custom":"keep"}')
        backups=self.root/'backup'
        installer.install_skill(self.root/'skills/migu',dest,backups)
        self.assertEqual(json.loads((dest/'installation.json').read_text())['custom'],'keep')
        saved=list(backups.glob('*/SKILL.md'))
        self.assertEqual(len(saved),1)
        self.assertEqual(saved[0].read_text(),'old user changes')

    def test_existing_config_paths_preserved(self):
        p=self.skills/'migu/installation.json';p.parent.mkdir(parents=True)
        data={'schema_version':1,'collection_root':str(self.root/'custom'),'other':'preserve'}
        p.write_text(json.dumps(data))
        installer.Installer(self.root,self.skills,'analyze').execute()
        saved=json.loads(p.read_text())
        self.assertEqual(saved['collection_root'],data['collection_root'])
        self.assertEqual(saved['other'],'preserve')

    def test_failure_records_error_not_success(self):
        instance=installer.Installer(self.root,self.skills,'generate')
        with patch.object(instance,'python_tools',side_effect=RuntimeError('synthetic failure')), \
             patch.object(instance,'node'),patch.object(instance,'media_tools'),patch.object(instance,'hypit'):
            self.assertEqual(instance.execute(),1)
        self.assertEqual(json.loads(instance.report_path.read_text())['status'],'FAILED')

    def test_pending_is_not_success(self):
        instance=installer.Installer(self.root,self.skills,'generate')
        with patch.object(instance,'python_tools'),patch.object(instance,'node'), \
             patch.object(instance,'media_tools'),patch.object(instance,'hypit',side_effect=lambda:instance.pending('Login required')):
            self.assertEqual(instance.execute(),2)
        self.assertEqual(instance.report['status'],'ACTION_REQUIRED')

    @unittest.skipIf(os.name=='nt','symlink creation needs host privileges on Windows')
    def test_refuses_symlink_skill(self):
        target=self.root/'target';target.mkdir()
        self.skills.mkdir();(self.skills/'migu').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install_skill(self.root/'skills/migu',self.skills/'migu',self.root/'backup')

    def test_invalid_config_not_overwritten(self):
        dest=self.skills/'migu/installation.json';dest.parent.mkdir(parents=True);dest.write_text('{')
        with self.assertRaises(ValueError):installer.Installer(self.root,self.skills,'full')
        self.assertEqual(dest.read_text(),'{')

    def test_windows_refresh_preserves_custom_path_and_adds_docker(self):
        instance=installer.Installer(self.root,self.skills,'full')
        instance.env.update(PATH='custom-path', ProgramFiles='C:/Program Files', LOCALAPPDATA='C:/Users/Test/AppData/Local')
        with patch.object(installer.platform,'system',return_value='Windows'):
            instance.refresh_path()
        self.assertIn('custom-path',instance.env['PATH'])
        self.assertIn('Docker',instance.env['PATH'])
        self.assertIn('WinGet',instance.env['PATH'])

    def test_hypit_reuses_configured_launcher(self):
        instance=installer.Installer(self.root,self.skills,'generate')
        launcher=self.root/'custom-hypit';launcher.write_text('fixture')
        instance.config['hypit_path']=str(launcher)
        skill=self.skills/'hypit/SKILL.md';skill.parent.mkdir(parents=True);skill.write_text('fixture')
        with patch.object(instance,'which',return_value=None),patch.object(instance,'run') as run:
            instance.hypit()
        run.assert_called_once_with([str(launcher),'version'])

    def test_node_engine_rejects_unsupported_odd_major(self):
        self.assertFalse(installer.supported_node('23.1.0'))
        self.assertTrue(installer.supported_node('22.15.0'))
        self.assertTrue(installer.supported_node('24.0.0'))
        self.assertFalse(installer.supported_node('22.1.0'))

    def test_healthy_evil_still_runs_credential_repair(self):
        instance=installer.Installer(self.root,self.skills,'discover')
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value.status=200
        with patch.object(installer.urllib.request,'urlopen',return_value=response), \
             patch.object(instance,'repair_evil') as repair:
            instance.evil()
        repair.assert_called_once_with('http://127.0.0.1:8000')


if __name__=='__main__':unittest.main()

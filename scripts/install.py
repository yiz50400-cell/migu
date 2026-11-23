#!/usr/bin/env python3
"""Install Migu and bundled toolkits. Default is a read-only plan; --apply installs."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def read_config(path):
    if not path.exists(): return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict): raise ValueError('Configuration must be an object')
    return data


def install_skill(source, destination, backups):
    """Merge distributed files, preserving local-only config; back up changed installs."""
    if destination.is_symlink(): raise ValueError('Refusing to replace a symlink skill: '+destination.name)
    files = [p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'installation.json']
    changed = any(not (destination/p.relative_to(source)).is_file() or
                  (destination/p.relative_to(source)).read_bytes()!=p.read_bytes() for p in files)
    if not changed: return False
    if destination.exists():
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copytree(destination, backups/(destination.name+'-'+str(time.time_ns())))
    destination.mkdir(parents=True, exist_ok=True)
    for p in files:
        if p.is_symlink(): raise ValueError('Symlink in skill source')
        dest=destination/p.relative_to(source)
        if dest.is_symlink(): raise ValueError('Symlink in installed skill')
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, temp=tempfile.mkstemp(dir=dest.parent)
        os.close(fd)
        shutil.copy2(p,temp)
        os.replace(temp,dest)
    return True


def runtime_python(root):
    return root/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')


def supported_node(version):
    parts=tuple(map(int,version.strip().split('.')[:3]))
    return (parts[0]==22 and parts>=(22,15,0)) or parts[0]>=24


def plan(route):
    return {
        'route': route, 'mode': 'PLAN_ONLY',
        'steps': ['Install/update Migu and companion skill with backups',
                  'Reuse tools; prepare uv-managed Python and route dependencies',
                  'Install official Hypit CLI/skill for generation' if route in ('generate','full') else 'No generation installation',
                  'Install bundled collector and yt-dlp' if route in ('discover','full') else 'No discovery installation',
                  'Install bundled editor and locked Remotion dependencies' if route in ('edit','full') else 'No editor installation',
                  'Write local paths and installation report'],
        'service_boundary': 'No generation or model spending. Desktop sign-in and required host installation clicks remain real user actions.'}


class Installer:
    def __init__(self, root, skills_dir, route):
        self.root=root.resolve(); self.skills_dir=skills_dir.expanduser().resolve(); self.route=route
        self.runtime=self.root/'.runtime'; self.runtime.mkdir(exist_ok=True)
        self.lock=read_config(self.root/'dependencies.json')
        self.report={'status':'INSTALLING','route':route,'completed':[], 'pending':[], 'errors':[]}
        self.env=os.environ.copy()
        self.env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        self.config=read_config(self.skills_dir/'migu/installation.json')
        self.config.setdefault('schema_version',1)
        self.config['distribution_root']=str(self.root)
        self.report_path=self.runtime/'install-report.json'
        self.uv=None

    def save(self): atomic_json(self.report_path,self.report)
    def pending(self, item):
        if item not in self.report['pending']: self.report['pending'].append(item)
        self.save()
    def run(self, args, cwd=None, capture=False):
        # Commands contain program paths only, never credentials. No shell interpolation.
        print('Running: '+' '.join(str(x) for x in args[:5]),flush=True)
        result=subprocess.run([str(x) for x in args],cwd=cwd,env=self.env,
                              text=True,encoding='utf-8',errors='replace',capture_output=capture,timeout=1800)
        if result.returncode: raise RuntimeError('Command failed with exit '+str(result.returncode)+': '+str(args[0]))
        return result.stdout.strip() if capture else ''
    def stage(self, name, fn):
        try:
            fn();self.report['completed'].append(name)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
            self.report['errors'].append({'stage':name,'error':str(exc)})
        self.save()
    def which(self, name): return shutil.which(name,path=self.env.get('PATH'))
    def prepend(self, folder): self.env['PATH']=str(folder)+os.pathsep+self.env.get('PATH','')

    def refresh_path(self):
        if platform.system()!='Windows': return
        paths=[self.env.get('PATH','')]
        try:
            import winreg
            for hive,key in ((winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
                             (winreg.HKEY_CURRENT_USER,r'Environment')):
                try:
                    with winreg.OpenKey(hive,key) as handle:
                        value=winreg.QueryValueEx(handle,'Path')[0]
                        paths.append(os.path.expandvars(value))
                except OSError: pass
        except ImportError: pass
        program=Path(self.env.get('ProgramFiles','C:/Program Files'))
        local=Path(self.env.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))
        paths.extend(str(p) for p in (program/'Docker/Docker/resources/bin',program/'nodejs',
                                     local/'Microsoft/WinGet/Links'))
        self.env['PATH']=os.pathsep.join(paths)

    def skills(self):
        for name in ('migu','tiktok-product-video-editor'):
            install_skill(self.root/'skills'/name,self.skills_dir/name,self.runtime/'backups')

    def python_tools(self):
        exe=self.which('uv')
        if exe: self.uv=[exe]
        else:
            target=self.runtime/'bootstrap'
            self.run([sys.executable,'-m','pip','install','--target',target,'uv=='+self.lock['uv']])
            self.env['PYTHONPATH']=str(target)+(os.pathsep+self.env['PYTHONPATH'] if self.env.get('PYTHONPATH') else '')
            self.uv=[sys.executable,'-m','uv']
        self.run(self.uv+['python','install',self.lock['python']])

    def node(self):
        node=self.which('node');npm=self.which('npm')
        if node and npm:
            version=self.run([node,'-p','process.versions.node'],capture=True)
            if supported_node(version): return
        # Existing package managers own system-level installations. Otherwise agent-guided setup.
        brew=self.which('brew');winget=self.which('winget')
        if brew:
            self.run([brew,'install','node@22'])
            prefix=self.run([brew,'--prefix','node@22'],capture=True);self.prepend(Path(prefix)/'bin')
        elif winget:
            self.run([winget,'install','--id','OpenJS.NodeJS.LTS','--exact','--source','winget'])
            self.refresh_path()
        else:
            raise RuntimeError('Node.js >=22.15 is missing. Continue the Node setup section in docs/INSTALL.md; do not stop at telling the customer to install it.')
        if not self.which('node') or not self.which('npm'): raise RuntimeError('Node/npm installation needs PATH refresh')
        if not supported_node(self.run([self.which('node'),'-p','process.versions.node'],capture=True)):
            raise RuntimeError('Selected Node is incompatible; resolve PATH to Node 22.15+ (22.x) or >=24.')

    def media_tools(self):
        ffmpeg=self.config.get('ffmpeg_path')
        if not ffmpeg or not Path(ffmpeg).is_file(): ffmpeg=self.which('ffmpeg')
        probe=self.which('ffprobe')
        if not (ffmpeg and probe):
            if self.which('brew'):
                self.run([self.which('brew'),'install','ffmpeg'])
            elif self.which('winget'):
                self.run([self.which('winget'),'install','--id','Gyan.FFmpeg','--exact','--source','winget'])
                self.refresh_path()
            else:
                self.pending('FFmpeg/FFprobe system installation: follow docs/INSTALL.md media section automatically within deployment scope.')
        ffmpeg=ffmpeg or self.which('ffmpeg')
        if ffmpeg: self.config['ffmpeg_path']=str(Path(ffmpeg).resolve())
        if not self.which('ffprobe'): self.pending('FFprobe not found; technical editor deployment is incomplete.')

    def checkout(self, name, spec):
        target=self.runtime/'upstream'/(name+'-'+spec['commit'][:12])
        git=self.which('git')
        if not git: raise RuntimeError('Git is required for official upstream dependencies')
        if target.exists():
            sha=self.run([git,'-C',target,'rev-parse','HEAD'],capture=True)
            if sha!=spec['commit']: raise RuntimeError('Existing upstream checkout differs: '+name)
            return target
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix=name+'-',dir=target.parent))
        self.run([git,'init',temp])
        # Docker entrypoint shell scripts must retain LF on Windows checkouts.
        self.run([git,'-C',temp,'config','core.autocrlf','false'])
        self.run([git,'-C',temp,'remote','add','origin',spec['repository']])
        self.run([git,'-C',temp,'fetch','--depth','1','origin',spec['commit']])
        self.run([git,'-C',temp,'checkout','--detach','FETCH_HEAD'])
        if self.run([git,'-C',temp,'rev-parse','HEAD'],capture=True)!=spec['commit']: raise RuntimeError('Upstream commit mismatch')
        temp.rename(target)
        return target

    def hypit(self):
        exe=self.config.get('hypit_path')
        if not exe or not Path(exe).is_file(): exe=self.which('hypit')
        if exe:
            self.run([exe,'version'])
        else:
            npm=self.which('npm')
            if not npm: raise RuntimeError('npm unavailable; finish Node stage first')
            prefix=self.runtime/'hypit'
            self.run([npm,'install','--prefix',prefix,'--no-audit','--no-fund','@hypit/hypit@'+self.lock['hypit']])
            exe=str(prefix/'node_modules/.bin'/('hypit.cmd' if os.name=='nt' else 'hypit'))
            self.run([exe,'version'])
        self.config['hypit_path']=exe
        if not (self.skills_dir/'hypit/SKILL.md').is_file():
            source=self.checkout('hypit',self.lock['hypit_skill'])
            install_skill(source/self.lock['hypit_skill']['path'],self.skills_dir/'hypit',self.runtime/'backups')
            shutil.copy2(source/'LICENSE',self.skills_dir/'hypit/UPSTREAM-LICENSE')
        self.pending('Verify existing video Runtime/account; images reuse the customer-selected Key/URL. Ask only for genuinely missing configuration; no generation during deployment.')

    def collector(self):
        if not self.uv: raise RuntimeError('uv setup incomplete')
        root=Path(self.config.get('collection_root') or self.root/'toolkits/collector').expanduser()
        if not (root/'workflow/collection/collector.py').is_file(): raise RuntimeError('Configured collector missing; existing path preserved')
        if not runtime_python(root).is_file(): self.run(self.uv+['venv','--python',self.lock['python'],root/'.venv'])
        self.run(self.uv+['pip','install','--python',runtime_python(root),'-r',root/'requirements-collect.txt','imageio-ffmpeg==0.6.0'])
        self.run([runtime_python(root),'-c','from workflow.collection import collector; from workflow.unattended import evil_discovery; import yt_dlp; print("collector imports OK")'],cwd=root)
        self.config['collection_root']=str(root.resolve())

    def evil(self):
        # Reuse a running endpoint; never replace another stack or its credentials.
        base=os.environ.get('VW_EVIL_API_BASE','http://127.0.0.1:8000').rstrip('/')
        try:
            with urllib.request.urlopen(base+'/readyz',timeout=5) as response:
                healthy=response.status==200
            if healthy:
                self.repair_evil(base)
                return
        except (OSError,ValueError):
            pass
        docker=self.which('docker')
        if not docker:
            if self.which('brew'):
                self.run([self.which('brew'),'install','--cask','docker'])
            elif self.which('winget'):
                self.run([self.which('winget'),'install','--id','Docker.DockerDesktop','--exact','--source','winget'])
                self.refresh_path()
            else:
                self.pending('Docker is missing: continue its official OS-specific install in docs/INSTALL.md, then rerun this installer.')
                return
            docker=self.which('docker')
        if not docker:
            self.pending('Docker Desktop installed; finish its first-run system prompt, then rerun to build Evil.')
            return
        probe=subprocess.run([docker,'info'],env=self.env,capture_output=True,timeout=20)
        if probe.returncode:
            self.pending('Docker engine is not running; open Docker Desktop and finish first-run prompts, then rerun.')
            return
        if self.run([docker,'info','--format','{{.OSType}}'],capture=True)!='linux':
            self.pending('Evil requires Linux containers. Enable Docker Desktop Linux/WSL2 backend and finish any required host permission/restart, then resume.')
            return
        if base!='http://127.0.0.1:8000':
            self.pending('Configured Evil endpoint is unavailable; recover that endpoint without silently replacing it.')
            return
        target=self.checkout('evil',self.lock['evil'])
        if not (target/'docker/compose.yml').is_file(): raise RuntimeError('Pinned Evil compose file missing')
        envfile=target/'.env'
        if not envfile.exists():
            postgres=secrets.token_hex(24);redis=secrets.token_hex(24)
            values={'DTK_SECRET_KEY':secrets.token_urlsafe(48), 'POSTGRES_PASSWORD':postgres,
                    'REDIS_PASSWORD':redis,
                    'DTK_DATABASE_URL':'postgresql+asyncpg://dtk:'+postgres+'@postgres:5432/dtk',
                    'DTK_REDIS_URL':'redis://:'+redis+'@redis:6379/0',
                    'DTK_BROWSER_RPC_URL':'http://browser-rpc:9000'}
            fd=os.open(envfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:
                f.write(''.join(k+'='+v+'\n' for k,v in values.items()))
        self.run([docker,'compose','--env-file',envfile,'-p','migu-evil','-f',target/'docker/compose.yml',
                  '--profile','browser','up','-d','--build','--wait','--wait-timeout','600'],cwd=target)
        self.repair_evil(base)

    def repair_evil(self, base):
        # Load by path so this works from tests, installed skills and any cwd.
        import importlib.util
        spec=importlib.util.spec_from_file_location('migu_evil_repair',self.root/'scripts/repair_evil.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        try:
            report=module.locked_repair(base=base,docker=self.which('docker'),env=self.env,apply=True)
        except module.RepairError as error:
            self.pending(str(error)+' Follow docs/WINDOWS-REPAIR.md; do not send the customer to the setup wizard by default.')
            return
        atomic_json(self.runtime/'evil-repair-report.json',report)
        for message in report.get('pending',[]): self.pending(message)

    def editor(self):
        if not self.uv: raise RuntimeError('uv setup incomplete')
        root=Path(self.config.get('editor_toolkit_root') or self.root/'toolkits/editor').expanduser()
        if not (root/'pyproject.toml').is_file(): raise RuntimeError('Configured editor missing; existing path preserved')
        self.run(self.uv+['sync','--frozen','--project',root])
        npm=self.which('npm')
        if not npm: raise RuntimeError('npm unavailable; finish Node stage first')
        self.run([npm,'--prefix',root/'remotion','ci','--no-audit','--no-fund'])
        self.run([runtime_python(root),root/'scripts/package_remotion.py','templates'],cwd=root)
        self.config['editor_toolkit_root']=str(root.resolve())
        p=self.skills_dir/'tiktok-product-video-editor/installation.json'
        data=read_config(p);data['toolkit_root']=str(root.resolve());atomic_json(p,data)
        self.pending('Check ChatCut MCP list_projects; if missing use official reconnect, then host-approved Desktop install only when actually absent (docs/INSTALL.md).')

    def execute(self):
        self.stage('skills',self.skills)
        if self.report['errors']:
            self.report['status']='FAILED';self.save()
            print(json.dumps(self.report,ensure_ascii=False,indent=2));return 1
        if self.route!='analyze':
            self.stage('python',self.python_tools)
            if self.route in ('generate','edit','full'): self.stage('node',self.node)
            self.stage('media',self.media_tools)
            if self.route in ('generate','full'):self.stage('hypit',self.hypit)
            if self.route in ('discover','full'):
                self.stage('collector',self.collector)
                self.stage('evil',self.evil)
            if self.route in ('edit','full'):self.stage('editor',self.editor)
        atomic_json(self.skills_dir/'migu/installation.json',self.config)
        self.report['status']='FAILED' if self.report['errors'] else ('ACTION_REQUIRED' if self.report['pending'] else 'LOCAL_INSTALLED')
        self.save()
        print(json.dumps(self.report,ensure_ascii=False,indent=2))
        return 1 if self.report['errors'] else (2 if self.report['pending'] else 0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--route',choices=('analyze','generate','discover','edit','full'),default='full')
    parser.add_argument('--skills-dir',type=Path,default=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills')
    args=parser.parse_args()
    if not args.apply:
        print(json.dumps(plan(args.route),ensure_ascii=False,indent=2));return 0
    return Installer(ROOT,args.skills_dir,args.route).execute()


if __name__=='__main__':
    sys.exit(main())

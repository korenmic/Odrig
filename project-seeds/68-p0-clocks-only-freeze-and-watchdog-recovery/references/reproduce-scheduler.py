import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path.cwd()))
from tests.firmware.compiler import compiled

def command(args):
    wrapped=['rtk','proxy',*map(str,args)]
    print('RTK CHECK:\n- original command: '+subprocess.list2cmdline(list(map(str,args)))+'\n- rtk equivalent: '+subprocess.list2cmdline(wrapped)+'\n- decision: Reconfirm the actual old and repaired task with a bounded scheduler stand-in.',flush=True)
    return subprocess.check_output(wrapped).decode('utf-8')

fixed='317eca0c23586038772f07936f3abddef6458a65'
old='9b64f48b117f70febfe08f459064725f2a315a8b'
fixture=ast.parse(command(['git','show',fixed+':tests/firmware/test_refresh_fairness.py']))
program=next(ast.literal_eval(node.value) for node in fixture.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROGRAM' for t in node.targets))
result=dict(beforeRef=old,candidateRef=fixed,kind='Production function compiled with a portable scheduler model; no physical board reproduction',cases=[])
with tempfile.TemporaryDirectory(prefix='clock-task-',dir=Path('build').resolve()) as folder:
    root=Path(folder).resolve(); assert root.parent==Path('build').resolve()
    for label,ref in [('before',old),('candidate',fixed)]:
        source=command(['git','show',ref+':firmware/usermod/odrig_usermod.cpp'])
        start=source.index('void requestRefreshes(void *) {'); end=source.index('\n}\n',start)+3
        path=root/(label+'.cpp');path.write_text(program.replace('@TASK@',source[start:end]),encoding='utf-8',newline='\n')
        executable=compiled([path],root/label)
        for mode in (0,1):
            stats=json.loads(command([str(executable),str(mode)]))
            assert stats['polls']==200
            assert (stats['longest']>=5000 and stats['ticks']==0) if label=='before' else (stats['longest']<5000 and stats['ticks']>=200)
            result['cases'].append(dict(variant=label,consumer='immediate' if mode==0 else 'queued-notification',**stats))
Path('build/seed68-evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))

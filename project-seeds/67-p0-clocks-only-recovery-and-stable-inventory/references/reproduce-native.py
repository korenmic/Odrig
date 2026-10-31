import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()))
from emulator import binding,host
from tests.core.test_mini import files_for
from tests.core.test_clocks import clock_of
from tests.emulator.support import LIBRARY

root=Path('build/seed67-native-lab');root.mkdir(exist_ok=False)
source=files_for();source['clocks.txt']='odrig-clocks 2\nmode only\nmessage off\n'
results={}
for faulty in (False,True):
    case=root/('read-error' if faulty else 'healthy');show=case/'show';show.mkdir(parents=True)
    for name,data in source.items():(show/name).write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'))
    card=case/'odrig/clocks';card.mkdir(parents=True)
    (card/'face.odrgx').write_bytes(clock_of(canvas=(60,60)))
    before=(show/'clocks.txt').read_bytes()
    class Files(host.FolderHost):
        def read_at(self,name,offset,capacity):
            if faulty and name=='clocks.txt':return None
            return super().read_at(name,offset,capacity)
    files=Files(show,drive=host.Drive(case))
    try:
        core=binding.Core(LIBRARY,files)
        for now in range(0,6001,20):core.poll(now)
        state=json.loads(core.command(6000,b'status'))
        results['read-error' if faulty else 'healthy']=dict(mode=state['clock_mode'],file=state['file'],
             settingsBytesUnchanged=(show/'clocks.txt').read_bytes()==before,logs=list(files.logged))
    finally:files.close()
assert results['healthy']['mode']=='only' and results['healthy']['file'].startswith('clocks/')
assert results['read-error']['mode']=='off' and results['read-error']['file']=='picture.odrg'
Path('build/seed67-native-reproduction.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results,indent=2))

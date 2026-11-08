"""One-command local reproduction; missing network downloads remain explicit.
Run: python scripts/run_all.py [--download]
"""
from pathlib import Path
import sys,subprocess,argparse,os,json,time,platform,hashlib
ROOT=Path(__file__).resolve().parents[1]
def run_commands(root, commands, env):
    """Persist the current attempt and reported failures, replacing previous status."""
    root=Path(root);out=root/'results';out.mkdir(exist_ok=True)
    record={'status':'running','python':sys.version,'platform':platform.platform(),'commands':[]}
    def save():
        temp=out/'reproduction.json.tmp';temp.write_text(json.dumps(record,indent=2))
        temp.replace(out/'reproduction.json')
    save()
    try:
        record['raw_manifest_sha256']=hashlib.sha256((root/'data/download_manifest.json').read_bytes()).hexdigest()
    except OSError as exc:
        record.update(status='failed',error_type=type(exc).__name__,stage='source_manifest')
        save();raise
    for i,args in enumerate(commands):
        label=Path(args[0]).stem if args[0]!='-m' else 'tests'
        log=out/f'reproduce_{i+1}_{label}.log';print('Running',label,flush=True);start=time.monotonic()
        entry={'command':[sys.executable,*args],'status':'running','log':str(log.relative_to(root))}
        record['commands'].append(entry);save()
        try:
            with log.open('w') as f:
                code=subprocess.call(entry['command'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
        except BaseException as exc:
            entry.update(status='failed',error_type=type(exc).__name__)
            record['status']='failed';save();raise
        entry.update(exit_code=code,elapsed_seconds=round(time.monotonic()-start,3),status='completed' if code==0 else 'failed')
        if code:
            record['status']='failed';save()
            raise RuntimeError(f'{label} failed; see {log}')
        save()
    record['status']='completed';save()
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--download',action='store_true');a=ap.parse_args()
    env=os.environ.copy();env.update(MPLCONFIGDIR=str(ROOT/'.mplconfig'),XDG_CACHE_HOME=str(ROOT/'tmp/cache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',LOKY_MAX_CPU_COUNT='1')
    (ROOT/'results').mkdir(exist_ok=True);(ROOT/'results/figures').mkdir(exist_ok=True);(ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    commands=[['scripts/download_data.py']+([] if a.download else ['--verify-only']),['src/analyze_voice.py'],['src/analyze_cocreation.py'],['src/analyze_latency.py'],['src/compare_information.py'],['src/bootstrap_voice_training.py'],['review_text/analyze_lexical.py'],['-m','unittest','discover','-s','tests','-v'],['scripts/build_manuscript.py']]
    run_commands(ROOT,commands,env)
    print('Reproduction complete. See output/research_paper.pdf',flush=True)
if __name__=='__main__':main()

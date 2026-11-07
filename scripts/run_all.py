"""One-command local reproduction; missing network downloads remain explicit.
Run: python scripts/run_all.py [--download]
"""
from pathlib import Path
import sys,subprocess,argparse,os,json,time,platform,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--download',action='store_true');a=ap.parse_args()
    env=os.environ.copy();env.update(MPLCONFIGDIR=str(ROOT/'.mplconfig'),XDG_CACHE_HOME=str(ROOT/'tmp/cache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',LOKY_MAX_CPU_COUNT='1')
    (ROOT/'results').mkdir(exist_ok=True);(ROOT/'results/figures').mkdir(exist_ok=True);(ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    commands=[['scripts/download_data.py']+([] if a.download else ['--verify-only']),['src/analyze_voice.py'],['src/analyze_cocreation.py'],['src/analyze_latency.py'],['src/compare_information.py'],['src/bootstrap_voice_training.py'],['-m','unittest','discover','-s','tests','-v'],['scripts/build_manuscript.py']]
    runs=[]
    for i,args in enumerate(commands):
        label=Path(args[0]).stem if args[0]!='-m' else 'tests'
        log=ROOT/'results'/f'reproduce_{i+1}_{label}.log';print('Running',label,flush=True);start=time.monotonic()
        with log.open('w') as f:code=subprocess.call([sys.executable,*args],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        runs.append({'command':[sys.executable,*args],'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(ROOT))})
        if code:raise RuntimeError(f'{label} failed; see {log}')
    record={'python':sys.version,'platform':platform.platform(),'commands':runs,'raw_manifest_sha256':hashlib.sha256((ROOT/'data/download_manifest.json').read_bytes()).hexdigest()}
    (ROOT/'results/reproduction.json').write_text(json.dumps(record,indent=2));print('Reproduction complete. See output/research_paper.pdf',flush=True)
if __name__=='__main__':main()

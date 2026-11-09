#!/usr/bin/env python3
"""Download the pinned public study files, verify SHA256, and extract SPSS CSVs.
Run from any directory: python scripts/download_data.py [--verify-only].
--verify-only forbids downloads; derived SPSS CSVs are still rebuilt from verified originals.
Source rights remain with original authors; this does not relicense the raw data.
"""
import argparse, hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');args=p.parse_args()
    manifest=json.loads((ROOT/'data/download_manifest.json').read_text())
    for item in manifest['files']:
        target=ROOT/item['path']
        if not target.exists():
            if args.verify_only: raise FileNotFoundError(target)
            request=urllib.request.Request(item['url'],headers={'User-Agent':'Reproducible-secondary-research/1.0'})
            with urllib.request.urlopen(request,timeout=120) as response: payload=response.read()
            if hashlib.sha256(payload).hexdigest()!=item['sha256']: raise RuntimeError('Source changed: '+item['path'])
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if digest!=item['sha256']: raise RuntimeError('Checksum mismatch: '+item['path'])
        print('verified',item['path'])
    # The analyses consume CSV derivatives. Hashing the SAV without rebuilding
    # the CSV would allow stale or modified input to pass an offline replay.
    import pyreadstat
    for study in (1,2):
        target=ROOT/f'data/raw/beyond_voice/experiment{study}.sav'
        df,_=pyreadstat.read_sav(target)
        csv_target=pathlib.Path(str(target)+'.csv')
        temporary=csv_target.with_suffix('.csv.tmp')
        df.to_csv(temporary,index=False)
        temporary.replace(csv_target)
    print('All pinned files verified.')

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Time the existing collector callback → durable commit on the selected live source.
No model turn is started. This is not provider-emission or browser latency.
"""
import argparse
import json
import statistics
import time
from pathlib import Path
from waypoint.collector import Collector
from waypoint.client import Client


class MeasuredCollector(Collector):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.received={};self.measurements=[]
    def snapshot(self,thread,state,historical,change=None):
        self.received.setdefault(thread,(time.monotonic(),bool(historical)))
        super().snapshot(thread,state,historical,change)
    def flush(self,thread=None,force=False):
        pending=list(self.pending) if thread is None else [thread]
        super().flush(thread,force)
        for native in pending:
            if native not in self.pending and native in self.received:
                start,historical=self.received.pop(native)
                self.measurements.append({'ms':(time.monotonic()-start)*1000,'initial_hydration':historical})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--project',required=True);p.add_argument('--thread',required=True)
    p.add_argument('--ipc',type=Path,required=True);p.add_argument('--rollouts',type=Path,required=True)
    p.add_argument('--duration',type=float,default=3);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    observer=MeasuredCollector(Client(args.data),args.project,args.thread,args.ipc,args.rollouts)
    observer.run(args.duration)
    values=[r['ms'] for r in observer.measurements]
    result={'status':'MEASURED' if values else 'NOT_MEASURED','fixture':False,'method':'time.monotonic from actual Follower callback entry through normalizer/coalescing to completed HTTP durable receipt','scope':'selected existing Codex family; actual product Collector','samples':observer.measurements,'n':len(values),'median_ms':statistics.median(values) if values else None,'max_ms':max(values) if values else None,'provider_emission_to_browser_latency_measured':False,'native_execution_commands':0}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if values else 1

if __name__=='__main__':raise SystemExit(main())

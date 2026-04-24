#!/usr/bin/env python3

"""Submit a small Bell-state example job to an AQDrop queue."""

import argparse
import aqdrop
import numpy as np
from pprint import pprint
from qiskit import QuantumCircuit
from Util_AQDrop import print_circuit_table, submit_job


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-q", "--queue", required=True, help="The name of the queue to submit the Bell state job to.")
    parser.add_argument("-n", "--shots", type=int, default=1024, help="The number of shots to submit with the job.")
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use values >1 for extra output.")
    parser.add_argument( "-E","--execJob", action='store_true', default=False, help="may take long time, test before use ")



def circ_bell():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc

def circ_tens2(th0,th1):
    qc = QuantumCircuit(2)
    qc.rx(th0,0)
    qc.ry(th1,1)
    qc.measure_all()
    return qc

def main(args):
    for arg in vars(args):   print( arg, getattr(args, arg))
      
    if args.verb > 1:
        print(circ_bell())
        print(circ_tens2(0.3,-0.2))

    # prepare list of circuist to be executed
    # this example:  Bell-state, 4 SPAM circ,  2 random angles circ
    circL = [circ_bell(),circ_tens2(0,0),circ_tens2(0,np.pi),circ_tens2(np.pi,0),circ_tens2(np.pi,np.pi), circ_tens2(0.8, -2.5)]
    
    shotL=[args.shots]+4*[10*args.shots]+[args.shots]
    nCirc=len(circL)
    job_meta = {"shots": shotL, 'comment':'bell job and SPAM measurement'}
    
    print('M: execution-ready %d circuits  to AQDrop queue=%s'%(nCirc,args.queue))
    if not args.execJob:
        print_circuit_table(circL, job_meta)
        pprint(job_meta)
        print('\nNO execution of circuits, use -E to execute the job\n')
        exit(0)

    client = aqdrop.AqdropClient()
    submit_job(queue=args.queue, circ=circL, meta=job_meta, verb=args.verb, client=client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)

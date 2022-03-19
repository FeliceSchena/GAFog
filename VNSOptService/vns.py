import argparse
import json
import time
from random import randint

import numpy.random

from optsolution import OptSolution

from VNSOptService.problem import Problem

"""
:parameter K: coefficiente moltiplicativo di tsla
:parameter mu: tempo di risposta ovvero funzione obiettivo tr
:parameter delta: delay medio della network
:return tsla:
"""
def compute_sla(problem):
    k = problem.get_SLA()
    delta = problem.network.get("F1-F2").get("delay")
    #compute service time agreement
    t_sla = k
    return t_sla

def compute_sensorfog_delay(problem):
    t_sf=0
    la_vect=problem.get_sensor_lambda()
    t_sf = sum(la_vect)
    #for i in len(problem.sensor):
        #for j in problem.get_nfog():




def compute_fogcloud_delay():
    pass


def compute_proc_time():
    pass


def fobj_func(tnet_sf, tnet_fc, tproc):
    if tnet_sf is None:
        tnet_sf = compute_sensorfog_delay()
    if tnet_fc is None:
        tnet_fc = compute_fogcloud_delay()
    if tproc is None:
        tproc = compute_proc_time()
    return float(tnet_sf + tnet_fc + tproc)


def sobj_func(E, c):
    pass


def init_vns(problem):
    c_solution = [None] * problem.get_nfog()
    for z in range(len(c_solution)):
        c_solution[z]= [None] * problem.get_nsensor()
    for i in range(len(c_solution[0])):
        c_solution[randint(0,problem.get_nsensor())][i]=1
    print(str(c_solution))



def solve_problem(data):
    problem = Problem(data)
    ts = time.time()
    compute_sla(problem)
    compute_sensorfog_delay(problem)
    init_vns(problem)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
        solve_problem(data)

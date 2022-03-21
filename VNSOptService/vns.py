import argparse
import json
import re
import time
import warnings
from random import randint
import numpy as np

from optsolution import OptSolution

from VNSOptService.problem import Problem

"""
:parameter K: coefficiente moltiplicativo di tsla
:parameter mu: tempo di risposta ovvero funzione obiettivo tr
:parameter delta: delay medio della network
:return tsla:
"""


class Vns:
    def __init__(self, problem, x_ij, y_jk):
        self.problem = problem
        self.x_ij = x_ij
        self.y_jk = y_jk

    def compute_sla(self):
        k = self.problem.get_SLA()
        delta = self.problem.network.get("F1-F2").get("delay")
        # compute service time agreement
        t_sla = k
        return t_sla

    """ Compute the t_net_sf time
        Parameters:
        :param problem: the current problem loaded from json
    :param c_solution: the current solution of the problem that on first iteration is random
    :return t_net_sf:

"""

    def compute_sensorfog_delay(self):
        t_sf = 0
        la_vect = self.problem.get_sensor_lambda()
        delay_list = self.problem.get_sensor_delay()
        t_sf = sum(la_vect)
        sum_of_product = float(0)
        for i in range(len(self.x_ij)):
            for j in range(len(self.x_ij[0])):
                sum_of_product += la_vect[j] * self.x_ij[i][j] * delay_list[j][i]
        return (1 / t_sf) * sum_of_product

    def get_fog_lambda(self, i):
        sum = 0
        keys = self.problem.sensor.keys()
        z = 0
        for j in keys:
            sum += self.problem.sensor.get(j).get("lambda") * self.x_ij[i-1][z]
            z += 1
        return float(sum)

    def compute_fogtime(self):
        t_fc = 0
        la_vect = []
        for i in self.problem.fog.keys():
            var = int("".join(filter(str.isdigit, i)))
            la_vect.append(self.get_fog_lambda(var))
            t_fc += self.get_fog_lambda(var)
        return t_fc, la_vect

    def compute_fogcloud_delay(self):
        sf = 0
        t_fc, la_vect = self.compute_fogtime()
        delay_vect = self.problem.get_fog_delay()
        for i in range(len(self.problem.fog.keys())):
            for k in range(len(self.problem.clouds.keys())):
                sf += la_vect[i] * self.y_jk[k][i] * delay_vect[i][k]
        return sf * (1 / t_fc)

    def compute_proc_time(self):
        t_fc, la_vect = self.compute_fogtime()
        mu_vect = self.problem.get_mu()
        sf = 0
        for i in range(len(la_vect)):
            try:
                sf += la_vect[i] * (1 / (mu_vect[i] - la_vect[i]))
            except:
                warnings.warn("Divisione per zero")
        return (1 / t_fc) * sf

    def fobj_func(self, tnet_sf, tnet_fc, tproc):
        if tnet_sf is None:
            tnet_sf = self.compute_sensorfog_delay()
        if tnet_fc is None:
            tnet_fc = self.compute_fogcloud_delay()
        if tproc is None:
            tproc = self.compute_proc_time()
        return tnet_sf, tnet_fc, tproc

    def sobj_func(E, c):
        pass


def allocate(i, dim, solution):
    for z in range(i):
        solution[z] = [0] * dim
    for k in range(dim):
        solution[randint(0, dim) % i][k] = 1
    return solution


def allocate_cloud(i, dim, solution):
    for z in range(i):
        solution[z] = [0] * dim
    for k in range(dim):
        a = randint(0, i)
        b = randint(0, dim)
        while solution[a % i][b % dim] == 1:
            a = randint(0, i)
            b = randint(0, dim)
        solution[a % i][b % dim] = 1
    return solution


def init_decision_variable(problem):
    sf_solution = [None] * problem.get_nfog()
    fc_solution = [None] * problem.get_ncloud()
    allocate(len(sf_solution), problem.get_nsensor(), sf_solution)
    allocate_cloud(len(fc_solution), problem.get_nfog(), fc_solution)
    return sf_solution, fc_solution


def solve_problem(data):
    tnet_sf = tnet_fc = t_proc = None
    problem = Problem(data)
    x_ij, y_ij = init_decision_variable(problem)
    vns = Vns(problem, x_ij, y_ij)
    ts = time.time()
    vns.compute_sla()
    tnet_sf, tnet_fc, t_proc = vns.fobj_func(tnet_sf, tnet_fc, t_proc)
    t_r=tnet_sf+tnet_fc+t_proc
    print(t_r)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
        solve_problem(data)

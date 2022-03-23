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
        """

        :param problem: the problem to analyze loaded from Problem class
        :param x_ij: decision variable for fog & sensor
        :param y_jk: decision variable for fog & cloud
        """
        self.problem = problem
        self.x_ij = x_ij
        self.y_jk = y_jk

    def compute_sla(self):
        """
            Compute de Service Level Agreement at response time
            :return t_SLA:
            """
        k = self.problem.get_SLA()
        delta = self.problem.network.get("F1-F2").get("delay")
        # compute service time agreement
        t_sla = k
        return t_sla


    def compute_sensorfog_delay(self):
        """ Compute the t_net_sf time
                :return t_net_sf:
            """
        r, c = self.x_ij.shape
        t_sf = 0
        la_vect = self.problem.get_sensor_lambda()
        delay_list = self.problem.get_sensor_delay()
        t_sf = sum(la_vect)
        sum_of_product = float(0)
        for i in range(r):
            for j in range(c):
                sum_of_product += la_vect[j] * self.x_ij[i][j] * delay_list[j][i]
        return (1 / t_sf) * sum_of_product

    def get_fog_lambda(self, i):
        """ Compute the incoming request rate at fog node i
               :param i: fog node number
               :return: sum of the outcoming request rate from sensor assigned to node
           """
        sum = 0
        keys = self.problem.sensor.keys()
        z = 0
        for j in keys:
            sum += self.problem.sensor.get(j).get("lambda") * self.x_ij[i - 1][z]
            z += 1
        return float(sum)

    def compute_fogtime(self):
        """Compute the fog time
           :returns t_fc, la_vect: Fog cloud time and lamba incoming rqst vector
           """
        t_fc = 0
        la_vect = []
        for i in self.problem.fog.keys():
            var = int("".join(filter(str.isdigit, i)))
            la_vect.append(self.get_fog_lambda(var))
            t_fc += self.get_fog_lambda(var)
        return t_fc, la_vect

    def compute_fogcloud_delay(self):
        """
        Compute the delay from fog to cloud
        :return t_fc: fog to cloud latency
        """
        sf = 0
        r, c = self.y_jk.shape
        t_fc, la_vect = self.compute_fogtime()
        delay_vect = self.problem.get_fog_delay()
        for i in range(r):
            for k in range(c):
                sf += la_vect[i] * self.y_jk[i][k] * delay_vect[i][k]
        return sf * (1 / t_fc)

    def compute_proc_time(self):
        """
        Computing processing time for the actual configuration of network
        :return tproc: Time for processing
        """
        t_fc, la_vect = self.compute_fogtime()
        mu_vect = self.problem.get_mu()
        sf = 0
        for i in range(len(la_vect)):
            try:
                sf += la_vect[i] * (1 / (mu_vect[i] - la_vect[i]))
            except:
                warnings.warn("Divisione per zero")
        return (1 / t_fc) * sf

    def sobj_func(self, tnet_sf, tnet_fc, tproc):
        """
          Compute the second obj function of the math problem.
          :param tnet_sf: computed from sensorfog_delay() represents the time from sensor to fog
          :param tnet_fc: computed from fogcloud_delay() represents the time from fog to cloud
          :param tproc: computed from proc_time() represents the processing time of the network
          :return t_r: sum of the tnet_sf,tnet_fc,tproc
          """
        if tnet_sf is None:
            tnet_sf = self.compute_sensorfog_delay()
        if tnet_fc is None:
            tnet_fc = self.compute_fogcloud_delay()
        if tproc is None:
            tproc = self.compute_proc_time()
        return tnet_sf + tnet_fc + tproc

    def fobj_func(self, e, c):
        """
        Compute the first obj function
        :param e: Location of fog nodes
        :param c: cost of Fog_j
        :return: sum of product between costs of Fog_j and location of fog node
        """
        return sum(np.multiply(e, self.problem.get_costs()))



def allocate(solution):
    """
    Initiate the solution matrix passed by arguments with at most 1 elements for column
    :param solution: the initialized solution for the first iteration
    :return solution: return solution matrix with the assignement updated
    """
    i, dim = solution.shape
    for k in range(i):
        solution[k][randint(0, dim) % dim] = 1
    return solution


def set_ej(solution,e):
    """
    function that calculate the sum of the turned on fog
    :param solution: current assignement of the fog to the cloud
    :param e: the vector of Ej
    :return: For all cells of e the rows sum of the solution
    """
    r, c = solution.shape
    for i in range(r):
        e[i]=sum(solution[i])
    return e

def init_decision_variable(problem):
    """
    :param problem: the problem to analyze loaded from Problem class
    :return: xij,yij,ej
    """
    e_j = np.zeros(problem.get_nfog())
    sf_solution = np.zeros((problem.get_nsensor(), problem.get_nfog()))
    fc_solution = np.zeros((problem.get_nfog(), problem.get_ncloud()))
    allocate(sf_solution)
    allocate(fc_solution)
    e_j = set_ej(fc_solution,e_j)
    return sf_solution, fc_solution, e_j


def solve_problem(data):
    tnet_sf = tnet_fc = t_proc = None
    problem = Problem(data)
    x_ij, y_ij, e_j = init_decision_variable(problem)
    print("Initiate variable \n Sensori ai Fog: \n" + str(x_ij) + "\n Fog ai cloud: \n" + str(y_ij) +"\n Fog accesi: \n"+str(e_j))
    vns = Vns(problem, x_ij, y_ij)
    vns.compute_sla()
    t_r = vns.sobj_func(tnet_sf, tnet_fc, t_proc)
    c=vns.fobj_func(e_j,problem.get_costs())
    print("Costs: \n"+str(c)+"\nResponse time: \n"+str(t_r))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
        solve_problem(data)

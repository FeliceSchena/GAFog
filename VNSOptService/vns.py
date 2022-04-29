import argparse
import json
from operator import index
from random import randint
import numpy as np

from optsolution import OptSolution

from VNSOptService.problem import Problem


class VNS:
    def __init__(self, problem):
        self.problem = problem
        self.optsolution = OptSolution(problem)
        self.solution = self.initialize_solution()

    def get_sensor_latency(self):
        rv = []
        #
        vect = []
        for i in range(self.problem.get_nsnsr()):
            vect.append(self.problem.get_sensor_delay("S" + str(i + 1)))
        rv = np.array(vect)
        # debugging print
        return rv

    def VND(self):
        pass

    # variation of neighborhood search algorithm for minimize opt_sol.fobj
    def vns(self):
        iter = 0
        # initialize best solution
        while iter < 2:
            neighbor_sel = randint(0, 1)
            if neighbor_sel == 0:
                self.structure1()
                iter += 1
            else:
                self.structure2()
                iter += 1
            if self.VND()==1:
                iter=0


    # swap the two sensors
    def swap_sensors(self, f1, f2, idx_snsr_f1, idx_snsr_f2):
        self.solution[idx_snsr_f1, f1] = 0
        self.solution[idx_snsr_f1, f2] = 1
        self.solution[idx_snsr_f2, f2] = 0
        self.solution[idx_snsr_f2, f1] = 1

    # select randomly a fog node f1, pick the farthest sensor from f1, swap with the closest sensor inside the
    def structure1(self):
        snsr_latency = self.get_sensor_latency()
        # delay of allocated sensors
        snsr_latency_on = np.multiply(self.get_sensor_latency(), self.solution)
        # randomly select a fog node f1
        f1 = randint(0, (self.problem.get_nfog() - 1))
        while (np.sum(snsr_latency_on[:, f1]) == 0):
            f1 = randint(0, (self.problem.get_nfog() - 1))
        # the fartest sensor allocated to f1
        idx_snsr_f1 = np.argmax(snsr_latency_on[:, f1])
        # find index of the fog node f2 with the closest sensor that is different from from idx_snsr_f1
        masked_b = np.ma.masked_equal(snsr_latency[idx_snsr_f1, :], snsr_latency[idx_snsr_f1, f1], copy=False)
        f2 = np.argmin(masked_b)
        # find the closest sensor inside f2
        temp = []
        for i in range(len(snsr_latency_on[:, f2])):
            if snsr_latency_on[i, f2] != 0:
                temp.append(snsr_latency[i, f1])
            else:
                temp.append(0)
        masked_a = np.ma.masked_equal(temp, 0.0, copy=False)
        idx_snsr_f2 = np.argmin(masked_a)
        # swap the two sensors
        self.swap_sensors(f1, f2, idx_snsr_f1, idx_snsr_f2)

    def structure2(self):
        load = []
        incoming = []
        snsr_latency_on = np.multiply(self.get_sensor_latency(), self.solution)
        for i in self.problem.get_fog_list():
            load.append(self.problem.fog[i]["capacity"])
        nfog = self.problem.get_nfog()
        for j in self.problem.sensor:
            incoming.append(self.problem.sensor[j]["lambda"])
        for i in range(nfog):
            load[i] = sum(self.solution[:, i] * incoming[i]) / load[i]
        r = sum(load) / nfog
        if max(load) > r:
            idx_1 = randint(0, nfog - 1)
            f1 = load[idx_1]
        while f1 < r:
            idx_1 = randint(0, nfog - 1)
            f1 = load[idx_1]
        idx_snsr_f1 = np.argmax(snsr_latency_on[:, idx_1])
        # choose f2 with  min load
        masked_a = np.ma.masked_equal(self.get_sensor_latency()[idx_snsr_f1, :],
                                      self.get_sensor_latency()[idx_snsr_f1, idx_1], copy=False)
        f2 = np.argmin(masked_a)
        self.solution[idx_snsr_f1, f2] = 1
        self.solution[idx_snsr_f1, idx_1] = 0

    def find_closest(self):

        max = np.argmax()

    def initialize_solution(self):
        """
        :param problem: the problem to analyze loaded from Problem class
        :return: xij
        """
        sf_solution = np.zeros((self.problem.get_nsnsr(), self.problem.get_nfog()))
        # allocate the sensor to fog nodes with the minimum delay
        for i in range(self.problem.get_nsnsr()):
            vect = self.problem.get_sensor_delay("S" + str(i + 1))
            sf_solution[i][np.where(vect == np.min(vect))] = 1
        return sf_solution


def solve_problem(data):
    tnet_sf = tnet_fc = t_proc = None
    problem = Problem(data)
    vns = VNS(problem)
    vns.structure1()
    print(vns.solution)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
    solve_problem(data)

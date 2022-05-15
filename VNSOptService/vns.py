import argparse
import json
from random import randint
import itertools
import numpy as np

from optsolution import OptSolution
from problem import Problem


class VNS:
    def __init__(self, problem):
        self.problem = problem
        self.optsolution = OptSolution(problem)
        self.solution = self.initialize_solution()

    def allocate_sensor(self, f, s):
        """
        Allocate a sensor to a fog node.
        :param f: fog node index
        :param s: sensor index
        :return: the vns.solution updated
        """
        # check if the sum of the 1 inside the matrix is less than the number of sensors
        if np.sum(self.solution[:, f]) < self.problem.get_nsnsr():
            self.solution[s, f] = 1
        else:
            # randomly allocate a sensor to the fog node and remove randomly the sensor from the solution
            r = randint(0, self.problem.get_nsnsr() - 1)
            self.solution[r, f] = 0
            self.solution[s, f] = 1

    def swap_sensors(self, f1, f2, idx_snsr_f1, idx_snsr_f2):
        """
        Swap sensors between two fog nodes.
        :param f1: fog node 1 index
        :param f2: fog node 2 index
        :param idx_snsr_f1: sensor index of fog node 1
        :param idx_snsr_f2: sensor index of fog node 2
        :return: vns.solution updated
        """
        self.solution[idx_snsr_f1, f1] = 0
        self.solution[idx_snsr_f1, f2] = 1
        self.solution[idx_snsr_f2, f2] = 0
        self.solution[idx_snsr_f2, f1] = 1

    def Neigborhood_change(self, c_sol, k):
        if c_sol.obj_func() < self.optsolution.obj_func():
            self.solution = c_sol
            k = 1
        else:
            k = k + 1
        return k

    def VND(self):
        c_solution = OptSolution(self.problem)
        k = 1
        while k < 3:
            if k == 1:
                # all possible permutation of self.solution
                perm = itertools.permutations(self.solution)
                for i in perm:
                    c_solution = i
                    k = k + 1
                    # k = self.Neigborhood_change(c_solution,k)

            else:
                count = self.problem.get_nsnsr()
                # perform all possible allocating sensors to fog nodes
                for i in range(self.problem.get_nfog()):
                    for j in range(self.problem.get_nsnsr()):
                        if self.solution[i, j] == 0:
                            if count > 0:
                                self.allocate_sensor(i, j)
                                count -= 1
                        k = self.Neigborhood_change(c_solution, k)
                        k = k + 1
        return 0

    # variation of neighborhood search algorithm for minimize opt_sol.fobj
    def GVNS(self):
        iter = 0
        # initialize best solution
        while iter < 2:
            if randint(0, 1) == 0:
                print("\n Struttura utilizzata: 1-Swap sensors \n")
                self.structure1()
                iter += 1
            else:
                print("\n Struttura utilizzata: 2-allocation sensors \n")
                self.structure2()
                iter += 1
            if self.VND() == 1:
                iter = 0
        return self.solution


    # select randomly a fog node f1, pick the farthest sensor from f1, swap with the closest sensor inside the
    def structure1(self):
        """
        @:param self: the object vns
        :return: swap the closest sensor with the farthest sensor
        """
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

    """
    def structure2(self):
        """"""
        The structure2 use the load of each fog node to select the fog node with the highest load
        @:param self: the object vns
        :return:
        """"""
        load = []
        incoming = []
        snsr_latency_on = np.multiply(self.get_sensor_latency(), self.solution)
        # vector of load of each fog node
        for i in self.problem.get_fog_list():
            load.append(self.problem.fog[i]["capacity"])
        nfog = self.problem.get_nfog()
        # vector of incoming requests of each fog node
        for j in self.problem.sensor:
            incoming.append(self.problem.sensor[j]["lambda"])
        #calulate the R of each fog node
        for i in range(nfog):
            load[i] = sum(self.solution[:, i] * incoming[i]) / load[i]
        r = sum(load) / nfog
        # find the fog node with the highest load
        if max(load) > r:
            idx_1 = randint(0, nfog - 1)
            f1 = load[idx_1]
        # find the fog node with the lowest load and the farthest sensor from the selected fog node
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
        """

    def initialize_solution(self):
        """
        Initialize the solution of the VNS allocating service to fog nodes
        :param problem: the problem to analyze loaded from Problem class
        :return: sf_solution
        """
        servicechain = self.problem.get_servicechain_list()
        nservice = len(servicechain)
        sf_solution = [None] * nservice
        for i in range(nservice):
            sf_solution[i] = [None] * len(self.problem.get_microservice_list(servicechain[i]))
        # allocate the microservice to fog nodes with the minimum delay
        for i in range(nservice):
            for j in range(len(self.problem.get_microservice_list(servicechain[i]))):
                fog_choosed=randint(0, self.problem.get_nfog() - 1)
                sf_solution[i][j] = "F" + str(fog_choosed+1)
        return sf_solution


def solve_problem(data):
    problem = Problem(data)
    vns = VNS(problem)
    print("Solution: \n" + str(vns.solution))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
    solve_problem(data)

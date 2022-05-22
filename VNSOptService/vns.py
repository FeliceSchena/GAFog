import argparse
import json
from random import randint
import itertools
import numpy as np
import re
import time
import requests

from optsolution import OptSolution
from problem import Problem


class VNS:
    def __init__(self, problem):
        self.problem = problem
        self.solution = self.initialize_solution()
        self.best = None
        self.fog_list = self.load_fog_service()
        self.optsolution = OptSolution(self.solution, self.fog_list, problem)
        self.c_solution = OptSolution(self.solution, self.fog_list, problem)

    def swap_microservice(self, f1, f2, idx_microservice_f1, idx_microservice_f2):
        """
        Swap microservice between two fog nodes.
        :param f1: fog node 1 index
        :param f2: fog node 2 index
        :param idx_microservice_f1: microservice index of fog node 1
        :param idx_microservice_f2: microservice index of fog node 2
        :return: vns.solution updated
        """
        if len(self.fog_list[f2]) != 0:
            index = re.findall(r'\d+', str(self.fog_list[f1][idx_microservice_f1]))
            self.solution["SC" + index[0]]["MS" + index[0] + "_" + index[1]] = "F" + str(f2 + 1)
            index = re.findall(r'\d+', str(self.fog_list[f2][idx_microservice_f2]))
            self.solution["SC" + index[0]]["MS" + index[0] + "_" + index[1]] = "F" + str(f1 + 1)
            self.fog_list = self.load_fog_service()
        else:
            index = re.findall(r'\d+', str(self.fog_list[f1][idx_microservice_f1]))
            self.solution["SC" + index[0]]["MS" + index[0] + "_" + index[1]] = "F" + str(f2 + 1)
            self.fog_list = self.load_fog_service()

    def neigborhood_change(self, check):
        if self.c_solution.obj_func() < self.optsolution.obj_func():
            self.optsolution = self.c_solution
            self.best = self.solution
            check = 1
        return check

    def vnd(self):
        k = 1
        altered = 0
        check = 0
        while k < 3:
            check = 0
            if k == 1:
                microservices = self.problem.get_microservice_list()
                combinations = itertools.combinations(microservices, 2)
                for i in combinations:
                    self.find_fog(i)
                    self.c_solution = OptSolution(self.solution, self.fog_list, self.problem)
                    k += 1
                    check = self.neigborhood_change(check)
            if k == 2:
                microservices = self.problem.get_microservice_list()
                fog = self.problem.get_fog_list()
                for i in microservices:
                    for j in fog:
                        self.find_fog(i, str(j))
                        self.c_solution = OptSolution(self.fog_list, self.problem)
                        k += 1
                        check = self.neigborhood_change(check)
            if check == 1:
                k = 1
                altered = 1
        return altered

    # variation of neighborhood search algorithm for minimize opt_sol.fobj
    def gvns(self):
        iter = 0
        # initialize best solution
        while iter < 2:
            if iter == 0:
                self.structure1()
                iter += 1
            else:
                self.structure2()
                iter += 1
            if self.vnd() == 1:
                iter = 0

    def structure1(self):
        """
        @:param self: the object vns
        :return: swap the closest sensor with the farthest sensor
        """
        latency = []
        # the next while loop is used to change the random selected fog node and microservice if is the first of the servicechain
        while True:
            # randomly select a fog node f1
            f1 = randint(0, (self.problem.get_nfog() - 1))
            # check if the fog node f1 has microservices
            while len(self.fog_list[f1]) == 0:
                f1 = randint(0, (self.problem.get_nfog() - 1))
            # the fartest sensor allocated to f1
            temp = np.ma.masked_equal(self.get_microservice_latency(f1), -1, copy=False)
            if len(temp) == 0:
                idx_microservice_f1 = 0
            else:
                idx_microservice_f1 = np.argmax(temp)
            index = re.findall(r'\d+', self.fog_list[f1][idx_microservice_f1])
            if index[1] != "1":
                break
        # the fog idx of the previous microservice in the service chain
        prev_idx = self.find_previous_microservice(index)
        # the next for loop is used to find the closest fog to the previous microservice
        for i in self.problem.get_fog_list():
            latency.append(self.problem.get_delay("F" + str(prev_idx + 1), str(i)))
            latency[len(latency) - 1] = float(re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(latency[len(latency) - 1]))[0])
        masked_latency = np.ma.masked_equal(latency, 0.0, copy=False)
        idx_f2 = np.argmin(masked_latency)
        # find microservice inside f2 that is closest to the fog node f1
        latency.clear()
        if self.fog_list[idx_f2].__len__() != 0:
            latency = self.get_microservice_latency(idx_f2, f1)
            masked_latency = np.ma.masked_equal(latency, -1, copy=False)
            idx_microservice_f2 = np.argmin(masked_latency)
            # swap the two sensors
            self.swap_microservice(f1, idx_f2, idx_microservice_f1, idx_microservice_f2)
        else:
            self.swap_microservice(f1, idx_f2, idx_microservice_f1, 0)
        self.c_solution = OptSolution(self.solution, self.fog_list, self.problem)

    def structure2(self):
        """
        The structure2 use the load of each fog node to select the fog node with the highest load
        @:param self: the object vns
        :return:
        """
        load = []
        # vector of load of each fog node
        for i in range(self.problem.get_nfog()):
            if self.optsolution.fog[i]["mu"] != 0:
                load.append(self.optsolution.fog[i]["lambda"] / self.optsolution.fog[i]["mu"])
            else:
                load.append(0)
        nfog = self.problem.get_nfog()
        r = sum(load) / nfog

        # find the fog node with the highest load to check if one exists
        try:
            np.max(load)
        except ValueError:
            print("\n No fog node with load")
        # the next three methods are used to random choose fog with load higher than r
        while True:
            masked_load = np.ma.masked_less(load, r, copy=False)
            pos = np.random.choice(masked_load.count(), size=1)
            f1_idx = tuple(np.take((~masked_load.mask).nonzero(), pos, axis=1))
            f1_idx = f1_idx[0][0]
            if len(self.fog_list[f1_idx]) != 0:
                break
        # the fartest sensor allocated to f1
        temp = np.ma.masked_equal(self.get_microservice_latency(f1_idx), -1, copy=False)
        if len(temp) != 0:
            idx_microservice_f1 = np.argmax(temp)
        else:
            idx_microservice_f1 = 0

        # find the fog node with the lowest load and the closest from the selected fog node
        index = self.find_previous_microservice(re.findall(r'\d+', self.fog_list[f1_idx][idx_microservice_f1]))
        masked_load = np.ma.masked_greater(load, r, copy=False)
        latency = []
        for i in range(nfog):
            if masked_load[i] is np.ma.masked:
                latency.append(-1)
            else:
                latency.append(float(
                    re.findall(r"\d+\.\d+", str(self.problem.get_delay("F" + str(index + 1), "F" + str(i + 1))))[0]))
        # choose f2 with  min load
        masked_latency = np.ma.masked_equal(latency, -1, copy=False)
        idx_f2 = self.find_best(masked_load, masked_latency)
        index = re.findall(r'\d+', str(self.fog_list[f1_idx][idx_microservice_f1]))
        self.solution["SC" + index[0]]["MS" + index[0] + "_" + index[1]] = "F" + str(idx_f2 + 1)
        self.fog_list = self.load_fog_service()
        self.c_solution = OptSolution(self.solution, self.fog_list, self.problem)

    def find_fog(self, idx_microservice, fog=None):
        if len(idx_microservice) == 2:
            ms1 = re.findall(r'\d+', str(idx_microservice[0]))
            temp = self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]]
            ms2 = re.findall(r'\d+', str(idx_microservice[1]))
            self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]] = self.solution["SC" + ms2[0]][
                "MS" + ms2[0] + "_" + ms2[1]]
            self.solution["SC" + ms2[0]]["MS" + ms2[0] + "_" + ms2[1]] = temp
        else:
            ms1 = re.findall(r'\d+', str(idx_microservice[0]))
            print(ms1)
            self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]] = fog
        self.fog_list = self.load_fog_service()

    def find_best(self, load, latency):
        r = -1
        d = -1
        idx = 0
        for i in range(len(load)):
            if load[i] is np.ma.masked:
                continue
            else:
                if (r == -1) and (d == -1):
                    r = load[i]
                    d = latency[i]
                    idx = i
                else:
                    if load[i] < r and latency[i] < d:
                        r = load[i]
                        d = latency[i]
                        idx = i
                    else:
                        if load[i] < r and latency[i] > d or load[i] > r and latency[i] < d:
                            if d == 0:
                                d = 0.00000000000000000000000000000000000001
                            if r == 0:
                                r = 0.00000000000000000000000000000000000001
                            if load[i] / r * 100 >= load[i] / d * 100:
                                r = load[i]
                                d = latency[i]
                                idx = i
                            else:
                                continue
        return idx

    def initialize_solution(self):
        """
        Initialize the solution of the VNS allocating service to fog nodes
        :param problem: the problem to analyze loaded from Problem class
        :return: sf_solution
        """
        sf_solution = {}
        temp = {}
        servicechain = self.problem.get_servicechain_list()
        for i in servicechain:
            temp.clear()
            for j in self.problem.get_microservice_list(i):
                fog_choosed = randint(0, self.problem.get_nfog() - 1)
                temp[j] = "F" + str(fog_choosed + 1)
            sf_solution[i] = dict(temp)
        return sf_solution

    def load_fog_service(self):
        """
        For each fog nodes, it stores the name of the microservice in a two-dimensional list
        :return:
        """
        # create empty two-dimensional list
        fog_service = [[] for i in range(self.problem.get_nfog())]
        for i in self.solution:
            for j in self.solution[i]:
                index = re.findall(r'\d+', self.solution[i][j])
                fog_service[int(index[0]) - 1].append(j)
        return fog_service

    def find_previous_microservice(self, index):
        if index[1] != "1":
            for j in range(self.problem.get_nfog()):
                try:
                    p_index = self.fog_list[j].index("MS" + str(index[0]) + "_" + str(int(index[1]) - 1))
                except ValueError:
                    p_index = None
                else:
                    return j
        else:
            return int(index[0])

    def get_microservice_latency(self, fog_column, fog=None):
        """
        Get the latency of a microservice from previous to next microservice in the service chain
        :param fog_column: the index of the microservice
        :return: latency of the microservice
        """
        latency = list()
        for i in range(len(self.fog_list[fog_column])):
            index = re.findall(r'\d+', self.fog_list[fog_column][i])
            if index[1] != '1':
                p_service = self.find_previous_microservice(index)
                if fog is None:
                    latency.append(float(re.findall(r"\d+\.\d+", str(self.problem.get_delay("F" + str(fog_column + 1),
                                                                                            "F" + str(p_service + 1))))[
                                             0]))
                else:
                    latency.append(float(
                        re.findall(r"\d+\.\d+",
                                   str(self.problem.get_delay("F" + str(p_service + 1), "F" + str(fog + 1))))[
                            0]))
            else:
                latency.append(-1.0)

        return latency


def dump_solution(gaout, sol, deltatime):
    with open(gaout, "w+") as f:
        json.dump(sol.dump_solution(deltatime), f, indent=2)


def solve_problem(data):
    problem = Problem(data)
    vns = VNS(problem)
    ts = float(time.time())
    vns.gvns()
    deltatime = float(time.time() - ts)
    resp = data['response']
    if resp.startswith('file://'):
        dump_solution(resp.lstrip('file://'), vns.optsolution, deltatime)
    else:
        # use requests package to send results
        requests.post(data['response'], json=vns.optsolution.dump_solution(deltatime))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
    solve_problem(data)

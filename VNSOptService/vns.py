import argparse
import json
from decimal import Decimal
from random import randint
import itertools
import numpy as np
import re
import time
import requests
from optsolution import OptSolution
from problem import Problem
from itertools import starmap
import copy

__author__ = "Felice Schena"
__copyright__ = "Copyright 2022 Felice Schena"
__credits__ = ["Felice Schena", "Riccardo Lancellotti", "Claudia Canali", "Manuel Iori", "Thiago Alves de Queiroz"]
__license__ = "GPL"
__version__ = "3.0.0"
__maintainer__ = "Felice Schena"
__email__ = "246240@studenti.unimore.it"
__status__ = "Production"

"""
    This file is part of VNSOptService.

    VNSOptService is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    VNSOptService is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with VNSOptService.  If not, see <http://www.gnu.org/licenses/>.
"""


class VNS:
    def __init__(self, problem):
        """
        Initialize the VNS class.
        """
        self.problem = problem
        self.solution = self.initialize_solution()
        self.fog_list = self.load_fog_service()
        self.optsolution = OptSolution(copy.deepcopy(self.solution), copy.deepcopy(self.fog_list), problem)
        self.c_solution = OptSolution(copy.deepcopy(self.solution), copy.deepcopy(self.fog_list), problem)
        self.count = 0
        self.best_count = 0

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

    def neigborhood_change(self):
        """
        Check if the current solution is better than the best solution.
        """
        self.count += 1
        self.c_solution.resptimes = None
        self.optsolution.resptimes = None
        self.c_solution.compute_fog_status()
        self.optsolution.compute_fog_status()
        tr_tot_c = self.c_solution.obj_func()
        tr_tot_o = self.optsolution.obj_func()
        if tr_tot_c < tr_tot_o:
            self.best_count = self.count
            self.optsolution.mapping = copy.deepcopy(self.c_solution.mapping)
            self.optsolution.loaded_fog = copy.deepcopy(self.c_solution.loaded_fog)
            self.optsolution.compute_fog_status()
            self.optsolution.resptimes = None
            self.optsolution.obj_func()
            return True

    def perform_swap(self, element, element2):
        temp = copy.deepcopy(self.solution)
        self.find_fog([element, element2])
        self.fog_list = self.load_fog_service()
        self.c_solution.mapping = copy.deepcopy(self.solution)
        self.c_solution.loaded_fog = copy.deepcopy(self.fog_list)
        if self.neigborhood_change():
            ret = True
        else:
            self.undo(temp)
            ret = False
        return ret

    def undo(self, temp):
        self.solution = copy.deepcopy(temp)
        self.fog_list = self.load_fog_service()
        self.c_solution.mapping = copy.deepcopy(self.solution)
        self.c_solution.loaded_fog = copy.deepcopy(self.fog_list)
        self.c_solution.compute_fog_status()
        self.c_solution.resptimes = None
        self.c_solution.obj_func()

    def perform_allocation(self, element, element2):
        temp = copy.deepcopy(self.solution)
        self.find_fog(element, element2)
        self.fog_list = self.load_fog_service()
        for i in self.solution.keys():
            self.c_solution.mapping[i] = self.solution[i].copy()
        self.c_solution.loaded_fog = self.fog_list.copy()
        if self.neigborhood_change():
            ret = True
        else:
            self.undo(temp)
            ret = False
        return ret

    def vnd(self):
        """
        Variable Neighborhood Descent function.
        :return: 1 if the solution is improved, 0 otherwise
        """
        """
        Variable Neighborhood Descent function.
        :return: 1 if the solution is improved, 0 otherwise
        """
        k = 1
        check = 0
        altered = 0
        while k < 3:
            check = 0
            if k == 1:
                microservices = self.problem.get_microservice_list()
                combinations = list(itertools.combinations(microservices, 2))
                ret = list(starmap(self.perform_swap, combinations))
                k += 1
            if k == 2:
                microservices = self.problem.get_microservice_list()
                fog = self.problem.get_fog_list()
                unique_combinations = list(itertools.product(microservices, fog))
                ret1 = list(starmap(self.perform_allocation, unique_combinations))
                k += 1
            if True in ret or True in ret1:
                k = 1
                altered = 1
        return altered

    # variation of neighborhood search algorithm for minimize opt_sol.fobj
    def gvns(self):
        """
        Variable Neighborhood Search function.
        """
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
                self.optsolution.resptimes = None
                self.optsolution.compute_fog_status()
                self.optsolution.obj_func()
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
        self.c_solution.mapping = copy.deepcopy(self.solution)
        self.fog_list = self.load_fog_service()
        self.c_solution.loaded_fog = copy.deepcopy(self.fog_list)
        self.c_solution.compute_fog_status()
        self.c_solution.resptimes = None
        self.c_solution.obj_func()

    def structure2(self):
        """
        The structure2 use the load of each fog node to select the fog node with the highest load
        @:param self: the object vns
        :return:
        """
        self.c_solution.compute_fog_status()
        load = []  # vector of load of each fog node
        for i in range(self.problem.get_nfog()):
            if self.c_solution.fog[i]['mu'] != 0:
                load.append(self.c_solution.fog[i]["lambda"] / self.c_solution.fog[i]["mu"])
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
        masked_load = np.ma.masked_less(load, r, copy=False)
        pos = np.random.choice(masked_load.count(), size=1)
        f1_idx = tuple(np.take((~masked_load.mask).nonzero(), pos, axis=1))
        f1_idx = f1_idx[0][0]
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
        self.c_solution.mapping = copy.deepcopy(self.solution)
        self.fog_list = self.load_fog_service()
        self.c_solution.loaded_fog = copy.deepcopy(self.fog_list)
        self.c_solution.compute_fog_status()
        self.c_solution.resptimes = None
        self.c_solution.obj_func()

    def find_best(self, load, latency):
        """
        find the fog node with the lowest load and the closest from the selected fog node
        :param load: load of each fog node
        :param latency: latency of each fog node
        :return: the index of the fog node with the lowest load and the closest from the selected fog node
        """
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

    def find_fog(self, idx_microservice, fog=None):
        if len(idx_microservice) == 2:
            ms1 = re.findall(r'\d+', str(idx_microservice[0]))
            temp = self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]]
            ms2 = re.findall(r'\d+', str(idx_microservice[1]))
            self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]] = self.solution["SC" + ms2[0]][
                "MS" + ms2[0] + "_" + ms2[1]]
            self.solution["SC" + ms2[0]]["MS" + ms2[0] + "_" + ms2[1]] = temp
        else:
            ms1 = re.findall(r'\d+', idx_microservice)
            ret = self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]]
            self.solution["SC" + ms1[0]]["MS" + ms1[0] + "_" + ms1[1]] = fog
            return ret, ms1[0], ms1[1]
        self.fog_list = self.load_fog_service()

    def find_previous_microservice(self, index):
        """
        Find the index of the previous microservice in the fog variable
        :param index: the index of the microservice in the fog variable
        :return: the index of the previous microservice in the fog variable
        """
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
        :param fog: the index of the fog node if default value is None. If is not None, the index of the fog node is used to get the latency from that fog node
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


def dump_solution(gaout, sol, deltatime, conv):
    """
    Dump the solution of the vns to a file
    """
    with open(gaout, "w+") as f:
        json.dump(sol.dump_solution(deltatime, conv), f, indent=2)


def solve_problem(data):
    problem = Problem(data)
    vns = VNS(problem)
    ts = Decimal(time.time())
    vns.gvns()
    deltatime = Decimal(Decimal(time.time()) - ts)
    resp = data['response']
    if resp.startswith('file://'):
        if vns.best_count != 0:
            dump_solution(resp.lstrip('file://'), vns.optsolution, float(deltatime), float(vns.count / vns.best_count))
        else:
            dump_solution(resp.lstrip('file://'), vns.optsolution, float(deltatime), 0)
    else:
        if vns.best_count != 0:
            requests.post(data['response'],json=vns.optsolution.dump_solution(float(deltatime), float(vns.count / vns.best_count)))
        else:
            requests.post(data['response'],json=vns.optsolution.dump_solution(float(deltatime), 0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file. Default sample_input1.json')
    args = parser.parse_args()
    fname = args.file if args.file is not None else 'sample_input.json'
    with open(fname, ) as f:
        data = json.load(f)
    solve_problem(data)

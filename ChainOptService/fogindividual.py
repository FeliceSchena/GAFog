from math import sqrt
import json
import sys
sys.path.append('../FogProblem')
from problem import Problem
from solution import Solution

class FogIndividual(Solution):

    def __init__(self, individual, problem):
        super().__init__(individual, problem)
        self.deltatime=None
        self.conv_gen=None

    def get_convergence_gen(self):
        return self.get_extra_param('conv_gen')

    def set_convergence_gen(self, convgen):
        self.set_extra_param('conv_gen', convgen)
    
    def registertime(self, deltatime):
        self.set_extra_param('deltatime', deltatime)
        
if __name__ == "__main__":
    with open('sample_input.json',) as f:
        data = json.load(f)
    print('problem objct')
    p=Problem(data)
    print(p)
    for mapping in [[0, 1, 1], [1, 1, 0]]:
        print('individual objct ', mapping)
        i=FogIndividual(mapping, p)
        # print('obj_func= ' + str(i.obj_func()))
        print(json.dumps(i.dump_solution(), indent=2))


import statistics
import json
import numpy as np



class Problem:
    def __init__(self, problem):
        self.fog = dict(problem['fog'])
        self.sensor = dict(problem['sensor'])
        self.servicechain = dict(problem['servicechain'])
        self.microservice = dict(problem['microservice'])
        if 'network' in problem:
            self.network_is_fake = False
            self.network = problem['network']
        else:
            self.network_is_fake = True
            self.network = self.fake_network(self.fog)
        self.maxrho = 0.999
        self.compute_service_params()
        self.compute_chain_params()

    def fake_network(self, fognodes):
        rv = {}
        for f1 in fognodes:
            for f2 in fognodes:
                rv[self.get_network_key(f1, f2)] = {'delay': 0.0}
        return rv

    def get_capacity(self, f):
        if f in self.fog:
            return self.fog[f]['capacity']
        else:
            return 0

    def __str__(self):
        return 'services: %s' % str(list(self.microservice.keys()))

    def get_network_key(self, f1, f2):
        return '%s-%s' % (f1, f2)

    def network_as_matrix(self):
        rv=[]
        for f1 in self.get_fog_list():
            l=[]
            for f2 in self.get_fog_list():
                l.append(self.get_delay(f1, f2)['delay'])
            rv.append(l)
        return rv

    def get_delay(self, f1, f2):
        k = self.get_network_key(f1, f2)
        # search (f1, f2)
        if k in self.network:
            return self.network[k]
        else:
            # if not, create automatically an entry with delay=0 for f1, f1
            if f1 == f2:
                k = self.get_network_key(f1, f1)
                rv = {'delay': 0.0}
                self.network[k] = rv
                return rv
            else:
                # otherwise look for reverse mapping
                k = self.get_network_key(f2, f1)
                if k in self.network:
                    self.network[self.get_network_key(f1, f2)] = self.network[k]
                    return self.network[k]
                else:
                    # distance not found!
                    return None

    def compute_service_params(self):
        for ms in self.microservice:
            self.microservice[ms]['rate'] = 1.0 / self.microservice[ms]['meanserv']
            self.microservice[ms]['cv'] = self.microservice[ms]['stddevserv'] / self.microservice[ms]['meanserv']

    def get_servicechain_list(self):
        return list(self.servicechain.keys())

    def get_fog_list(self):
        return list(self.fog.keys())

    def get_service_for_sensor(self, s):
        sc = self.sensor[s]['servicechain']
        return self.servicechain[sc]['services'][0]

    def get_sensor_list(self):
        return list(self.sensor.keys())

    def get_chain_for_sensor(self, s):
        return self.sensor[s]['servicechain']

    def compute_chain_params(self):
        tot_weight = 0.0
        for sc in self.servicechain:
            lam = 0.0
            for s in self.sensor:
                if self.sensor[s]['servicechain'] == sc:
                    lam += self.sensor[s]['lambda']
            self.servicechain[sc]['lambda'] = lam
            # intialize also lambda for each microservice
            for s in self.servicechain[sc]['services']:
                self.microservice[s]['lambda'] = lam
            # initilize weight of service chain if missing
            if 'weight' not in self.servicechain[sc]:
                self.servicechain[sc]['weight'] = lam
            tot_weight += self.servicechain[sc]['weight']
        # normalize weights
        for sc in self.servicechain:
            self.servicechain[sc]['weight'] /= tot_weight

    def get_microservice_list(self, sc=None):
        if sc is None:
            return list(self.microservice.keys())
        else:
            return self.servicechain[sc]['services']

    def get_microservice(self, ms):
        if ms in self.microservice:
            return self.microservice[ms]
        else:
            return None

    def get_fog(self, f):
        if f in self.fog:
            return self.fog[f]
        else:
            return None

    def get_nfog(self):
        return len(self.fog)

    def get_nservice(self):
        return len(self.microservice)


if __name__ == '__main__':
    with open('sample_input.json', ) as f:
        data = json.load(f)
    p = Problem(data)
    print(p)
    for ms in p.get_microservice_list():
        print(ms, p.get_microservice(ms))

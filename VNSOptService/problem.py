import statistics
import json


class Problem:

    def __init__(self, problem):
        self.fog = problem['fog']
        self.sensor = problem['sensor']
        self.servicechain = problem['servicechain']
        self.microservice = problem['microservice']
        if 'network' in problem:
            self.network = problem['network']
            self.K=int(self.get_SLA())
        else:
            self.network = self.fake_network(self.fog)
            self.K = 10
        self.maxrho = 0.999
        self.compute_service_params()

    def get_SLA(self):
        key, val = next(iter(self.network.items()))
        return dict(val).get("k")
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

    def get_sensor_lambda(self):
        la_vect=[]
        keys=dict(self.sensor).keys()
        for i in keys:
            la_vect.append(dict(dict(self.sensor).get(i)).get("lambda"))
        return la_vect
    def get_sensor_delay(self):
        dly=[]
        keys = dict(self.sensor).keys()
        for i in keys:
            dly.append(dict(dict(self.sensor).get(i)).get("delay"))
        return dly
    def get_network_key(self, f1, f2):
        return '{}-{}'.format(f1, f2)

    def get_delay(self, f1, f2):
        z = self.get_network_key(f1, f2)
        # search (f1, f2)
        if z in self.network:
            return self.network[z]
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

    def get_nsensor(self):
        return len(self.sensor)

    def get_nservice(self):
        return len(self.microservice)


if __name__ == '__main__':
    with open('sample_input.json', ) as f:
        data = json.load(f)
    p = Problem(data)
    print(p)
    for ms in p.get_microservice_list():
        print(ms, p.get_microservice(ms))

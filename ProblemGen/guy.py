#!/usr/bin/python3
import argparse
import numpy
import json
import sys
import PySimpleGUI as sg


def get_net_id(i, j, n):
    if i > j:
        (i, j) = (j, i)
    rv = int((n - 1) * (j) - (((j - 1) * (j)) / 2) + (i - j) - 2)
    # print(i, j, rv)
    return rv


def get_fog(config):
    n_fog = int(config['nfog'])
    mincap = float(config['mincap']) if 'mincap' in config.keys() else 0.1
    avgcap = float(config['avgcap']) if 'avgcap' in config.keys() else 1.0
    fog = {}
    # generate capacities of fog nodes
    cap = list(numpy.random.normal(loc=avgcap, scale=0.2 * avgcap, size=n_fog))
    # remove negative values
    for idx, val in enumerate(cap):
        if val < mincap:
            cap[idx] = mincap
    scale = sum(cap) / (avgcap * n_fog)
    for f in range(n_fog):
        nf = f + 1
        fname = 'F%d' % nf
        fog[fname] = {'capacity': cap[f] / scale}
    return fog


def get_network(config):
    n_fog = int(config['nfog'])
    delta = float(config['tchain']) / float(config['nsrv_chain'])
    network = {}
    # generate network delays
    delay = list(numpy.random.normal(loc=delta, scale=0.2 * delta, size=int(n_fog * (n_fog - 1) / 2)))
    for idx, val in enumerate(delay):
        if val < 0:
            delay[idx] = 0
    scale = sum(delay) / (delta * len(delay))
    for f1 in range(n_fog):
        for f2 in range(n_fog):
            nname = 'F%d-F%d' % (f1 + 1, f2 + 1)
            if f1 == f2:
                network[nname] = {'delay': 0.0}
            else:
                network[nname] = {'delay': delay[get_net_id(f1, f2, n_fog)] / scale}
    return network


def get_sensor(config):
    n_chain = int(config['nchain'])
    lam = (float(config['rho']) * float(config['nfog'])) / (float(config['tchain']) * n_chain)
    sensor = {}
    for c in range(n_chain):
        # each service chain has a sensor
        nc = c + 1
        cname = 'SC%d' % nc
        sname = 'S%d' % nc
        sensor[sname] = {'servicechain': cname, 'lambda': lam}
    return sensor


def get_chain(config):
    n_chain = int(config['nchain'])
    n_srv_chain = int(config['nsrv_chain'])
    chain = {}
    for c in range(n_chain):
        nc = c + 1
        cname = 'SC%d' % nc
        chain[cname] = {'services': []}
        # add services
        for s in range(n_srv_chain):
            ns = s + 1
            sname = 'MS%d_%d' % (nc, ns)
            chain[cname]['services'].append(sname)
    return chain


def get_microservice(config):
    n_chain = int(config['nchain'])
    n_srv_chain = int(config['nsrv_chain'])
    t_chain = float(config['tchain'])
    microservice = {}
    # generate service chains
    for c in range(n_chain):
        # create serive times for microservices
        ts = list(numpy.random.uniform(0, t_chain, n_srv_chain - 1))
        ts.sort()
        # add max time of chain at end and 0 at beginnin
        ts.append(t_chain)
        ts.insert(0, 0.0)
        # print(ts)
        # add services
        for s in range(n_srv_chain):
            ns = s + 1
            sname = 'MS%d_%d' % (c + 1, ns)
            # compute service time
            t_srv = ts[ns] - ts[ns - 1]
            microservice[sname] = {"meanserv": t_srv, "stddevserv": 0.1 * t_srv}
    return microservice


def get_problem(config):
    if bool(config['enable_network']):
        return {'response': config['response'],
                'fog': get_fog(config),
                'sensor': get_sensor(config),
                'servicechain': get_chain(config),
                'microservice': get_microservice(config),
                'network': get_network(config)}
    else:
        return {'response': config['response'],
                'fog': get_fog(config),
                'sensor': get_sensor(config),
                'servicechain': get_chain(config),
                'microservice': get_microservice(config)}


if __name__ == "__main__":
    sg.theme('DarkAmber')
    layout = [[sg.Text('Configuratore per il ProblemGen')],
              [sg.Text('Output file'), sg.InputText('sample_problem.json', key='output'), sg.FileSaveAs(file_types=(("JSON", "*.json"),))],
              [sg.Text('Config file'), sg.InputText('', key='config'), sg.FileBrowse()],
              [sg.Text('Numero di fog'), sg.InputText('4', key='nfog')],
              [sg.Text('Numero di chain'), sg.InputText('1', key='nchain')],
              [sg.Text('Numero di servizi per chain'), sg.InputText('5', key='nsrv_chain')],
              [sg.Text('tchain'), sg.InputText('1.0', key='tchain')],
              [sg.Text('Rho'), sg.InputText('0.2', key='rho')],
              [sg.Text('Enable network'), sg.Checkbox('', default=False, key='enable_network')],
              [sg.Text('Quale algoritmo?'),
               sg.InputCombo(('Genetic Algorithm', 'VNS Algorithm', 'All 2'), default_value='Genetic Algorithm',
                             key='algorithm')],
              [sg.Text('response'), sg.InputText('sample_output', key='response')],
              [sg.Submit(), sg.Button('Exit')]]
    window = sg.Window('ProblemGen', layout)
    while True:
        event, values = window.read()
        if event in (None, 'Exit'):
            window.close()
            break
        else:
            if values['config'] != '':
                with open(values['config'], 'r') as f:
                    config = json.load(f)

            else:
                config = {}
                config['nchain'] = int(values['nchain'])
                config['nsrv_chain'] = int(values['nsrv_chain'])
                config['nfog'] = int(values['nfog'])
                config['tchain'] = float(values['tchain'])
                config['rho'] = float(values['rho'])
                config['enable_network'] = values['enable_network']
                config['response'] = values['response']
                alg = values['algorithm']
        window.close()
        prob=get_problem(config)
        with open(values['output'], 'w') as f:
            json.dump(prob, f, indent=2)
        if alg == 'Genetic Algorithm':
            config['response'] = "file://" + values['response'] + "_ga.json"
            prob = get_problem(config)
            sys.path.append('../ChainOptService')
            from ga import solve_problem
            solve_problem(prob)
        if alg == 'VNS Algorithm':
            config['response'] = "file://" + values['response'] + "_vns.json"
            prob = get_problem(config)
            sys.path.append('../VNSOptService')
            from vns import solve_problem

            solve_problem(prob)
        if alg == 'All 2':
            config['response'] = "file://" + values['response'] + "_ga.json"
            prob = get_problem(config)
            sys.path.append('../ChainOptService')
            from ga import solve_problem

            solve_problem(prob)
            print('GA done')
            config['response'] = "file://" + values['response'] + "_vns.json"
            prob = get_problem(config)
            sys.path.append('../VNSOptService')
            from vns import solve_problem

            solve_problem(prob)
            print('VNS done')

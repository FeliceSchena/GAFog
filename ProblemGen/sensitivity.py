#!/usr/bin/python3
import sys
import os
import json
import numpy as np

config = {
    'nchain_fog': 0.4,
    'nsrv_chain': 5,
    'nfog': 10,
    'tchain': 10.0,
    'rho': 0.6,
    'enable_network': True,
    'response': 'file://sample_output.json'
}

#nrun = 2
#nservices = [3, 5]
#rhos = [0.5, 0.7]
#nfogs = [10, 15]
nrun = 10
nservices = [3, 4, 5, 6, 7, 8, 9, 10]
rhos = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
nfogs = [5, 10, 15, 20, 25]

def nhop(data):
    nhop = 0
    for sc in data['servicechain']:
        ms = data['servicechain'][sc]['services']
        prevfog = None
        for s in ms:
            curfog = data['microservice'][s]
            if prevfog is not None and curfog != prevfog:
                nhop += 1
            prevfog = curfog
    return nhop / len(data['servicechain'])


def jain(data):
    rho = []
    for f in data['fog']:
        rho.append(data['fog'][f]['rho'])
    cv = np.std(rho) / np.mean(rho)
    return 1.0 / (1.0 + (cv ** 2))


def valid_solution(data):
    for f in data['fog']:
        if data['fog'][f]['rho'] >= 1:
            return False
    return True


def resp(data):
    # print(data)
    tr = []
    for sc in data['servicechain']:
        tr.append(data['servicechain'][sc]['resptime'])
    return (np.mean(tr), np.std(tr))


def gatime(data):
    return data['extra']['deltatime']


def generations(data):
    return data['extra']['conv_gen']


def parse_result(fname):
    with open(fname, 'r') as f:
        data = json.load(f)
        if not valid_solution(data):
            return None
        j = jain(data)
        (r, s) = resp(data)
        h = nhop(data)
        gt = gatime(data)
        gen = generations(data)
    return {'jain': j, 'tresp_avg': r, 'tresp_std': s, 'nhop': h, 'gatime': gt, 'convgen': gen}


def collect_results(res):
    rv = {}
    if len(res) > 0:
        for k in res[0].keys():
            samples = []
            for r in res:
                samples.append(r[k])
            rv[k] = np.mean(samples)
            rv['sigma_%s' % k] = np.std(samples)
    return rv


def dump_result(res, fname):
    with open(fname, 'w') as f:
        # heading
        keys = res[0].keys()
        s = '#'
        for k in keys:
            s = '%s%s\t' % (s, k)
        f.write(s + '\n')
        # lines
        for r in res:
            s = ''
            for k in keys:
                if k in r.keys():
                    s = '%s%f\t' % (s, r[k])
                else:
                    s = '%s0\t' % (s)
            f.write(s + '\n')


def run_experiment(par, values, nrun, config, mult, outfile):
    dir_sol = ['ga_results','vns_results']
    if not os.path.exists('ga_results'):
        os.makedirs('ga_results')
    if not os.path.exists('vns_results'):
        os.makedirs('vns_results')
    config['nchain'] = int(config['nchain_fog'] * config['nfog'])
    orig_param = config[par]
    resultga = []
    resultvns = []
    for al in dir_sol:
        print('Running %s' % al)
        for val in values:
            res = []
            resvns = []
            print('Experiment: %s=%.1f\t' % (par, val), end='')
            sys.stdout.flush()
            for nr in range(nrun):
                if mult < 0:
                    fname = '%s/output_%s%d_run%d.json' % (al, par, val, nr)
                else:
                    fname = '%s/output_%s%d_run%d.json' % (al, par, int(val * mult), nr)
                config[par] = val
                config['response'] = 'file://%s' % (fname)
                if os.path.isfile(fname):
                    print('K', end='')
                else:
                    print('R', end='')
                if al == 'ga_results':
                    # Hack to find modules of other services
                    config['response'] = 'file://%s' % (fname)
                    sys.path.append('../ChainOptService')
                    from ga import solve_problem
                    from genproblem import get_problem
                    p = get_problem(config)
                    solve_problem(p)
                else:
                    config['response'] = 'file://%s' % (fname)
                    sys.path.append('../VNSOptService')
                    from vns import solve_problem
                    from genproblem import get_problem
                    p = get_problem(config)
                    try:
                        solve_problem(p)
                    except ValueError:
                        print('Error', end='')

                sys.stdout.flush()
                # parse results
                r = parse_result(fname)
                if r is not None and al=='ga_results':
                    res.append(r)
                    print('+', end='')
                else:
                    if r is not None and al=='vns_results':
                        resvns.append(r)
                        print('+', end='')
                    else:
                        print('X', end='')
                sys.stdout.flush()
            # newline
            print()
            # compute average over multiple runs
            if al=='ga_results':
                cr = collect_results(res)
                cr = {par: val} | cr
                resultga.append(cr)
            else:
                cr = collect_results(resvns)
                cr = {par: val} | cr
                resultvns.append(cr)
        if al=='ga_results':
            dump_result(resultga, al+"/"+outfile)
            config[par] = orig_param
        else:
            dump_result(resultvns, al+"/"+outfile)
            config[par] = orig_param



# main
if __name__ == '__main__':
    run_experiment('nsrv_chain', nservices, nrun, config, -1, 'sens_nsrv_chain.data')
    run_experiment('rho', rhos, nrun, config, 10, 'sens_rho.data')
    config['nsrv_chain'] = 10
    run_experiment('nfog', nfogs, nrun, config, -1, 'sens_nfog.data')



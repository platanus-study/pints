#!/usr/bin/env python2
from __future__ import division
from __future__ import print_function
import os
import sys
import numpy as np
import myokit
import myokit.pacing as pacing
import matplotlib.pyplot as pl

#
# Show the real data vs the aslanidi model
#

# Load data
real = myokit.DataLog.load_csv('real-data.csv').npview()

# Load model
model = myokit.load_model('aslanidi-2009-ikr.mmt')

# Pre-pace
s = myokit.Simulation(model)
s.set_protocol(pacing.constant(-80))
s.run(10000, log=myokit.LOG_NONE)
model.set_state(s.state())

# Create step protocol
protocol = myokit.Protocol()
protocol.add_step(-80, 250)
protocol.add_step(-120, 50)
protocol.add_step(-80, 200)
protocol.add_step(40, 1000)
protocol.add_step(-120, 500)
protocol.add_step(-80, 1000)
protocol.add_step(-30, 3500)
protocol.add_step(-120, 500)
protocol.add_step(-80, 1000)
duration = protocol.characteristic_time()

# Create capacitance filter
cap_duration = 1.5
dt = 0.1
fcap = np.ones(int(duration / dt), dtype=int)
for event in protocol:
    i1 = int(event.start() / dt)
    i2 = i1 + int(cap_duration / dt)
    print(i1, i2)
    if i1 > 0: # Skip first one
        fcap[i1:i2] = 0

# Change RHS of membrane.V
model.get('membrane.V').set_rhs('if(engine.time < 3000 or engine.time >= 6500,'
    + ' engine.pace, '
    + ' - 30'
    + ' + 54 * sin(0.007 * (engine.time - 2500))'
    + ' + 26 * sin(0.037 * (engine.time - 2500))'
    + ' + 10 * sin(0.190 * (engine.time - 2500))'
    + ')')

# Define parameters
parameters = [
    'ikr.p1',
    'ikr.p2',
    'ikr.p3',
    'ikr.p4',
    'ikr.p5',
    'ikr.p6',
    'ikr.p7',
    'ikr.p8',
    ]

# Read last solution
with open('last-solution.txt', 'r') as f:
    lines = f.readlines()
    if len(lines) < len(parameters):
        print('Unable to read last solution, expected ' + str(len(parameters))
            + ' lines, only found ' + str(len(lines)))
        sys.exit(1)
    try:
        solution = [float(x.strip()) for x in lines[:len(parameters)]]
    except ValueError:
        print('Unable to read last solution')
        raise

# Run simulation
log_vars = ['engine.time', 'ikr.IKr']
simulation = myokit.Simulation(model, protocol)
for p, v in zip(parameters, solution):
    simulation.set_constant(p, v)
d = simulation.run(duration, log=log_vars, log_interval=0.1)

# Show solution
print('Current solution:')
for k, v in enumerate(solution):
    print(myokit.strfloat(v))

# Show plots
pl.figure()
pl.plot(real['time'], real['current'], label='real')
pl.plot(real['time'], d['ikr.IKr'], label='aslanidi')
pl.plot(real['time'], fcap, label='filter')
pl.show()
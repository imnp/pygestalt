#   pyGestalt Simulation Module

"""A library for simulating the behavior of machines."""

from pygestalt import units, plotting

class motor(object):
	def __init__(self, torque_speed_curve, max_speed = None, name = None, inertia = 0):
		"""Initializes the motor object with a provided torque-speed curve and intrinsic inertia.

		torque_speed_curve -- provided as a plotting.dataset object
		inertia -- provided as kg-mm^2
		"""

		self.torque_speed_curve = torque_speed_curve
		self.inertia = (units.kg * units.mm**2)(inertia)
		self.name = name
		self.max_speed = max_speed

	def __call__(self, angular_velocity):
		"""Returns torque at a provided angular velocity.

		angular_velocity = provided in rad/sec
		"""
		return self.torque_speed_curve(angular_velocity)


	def power_curve(self, max_speed = None, num_points = 100):
		"""Returns a dataset containing the power curve of the motor.

		max_speed -- 	the maximum speed for which to calculate the power curve.
						if None, then the motor's max speed will be used.
						if the motor has no max speed, then the last datapoint in the motor's torque-speed curve will be used.
		num_points -- the number of points to plot on the power curve.
		
		returns a plotting.dataset containing the motor's power curve.
		"""
		si_torque_speed_curve = plotting.dataset(self.torque_speed_curve, (units.rad/units.s, units.N*units.m))

		min_speed = (units.rad/units.s)(0)

		if max_speed != None:
			max_speed = (units.rad/units.s)(max_speed)
		elif self.max_speed != None:
			max_speed = (units.rad/units.s)(self.max_speed)
		else:
			max_speed = si_torque_speed_curve[-1][0]


		torque_power_curve = []
		for index in range(num_points+1):
			speed = (units.rad/units.s)(max_speed * (index/num_points))
			torque_power_curve += [(speed, speed*si_torque_speed_curve(speed))]

		return plotting.dataset(torque_power_curve, (units.rad/units.s, units.W))

class load(object):
	"""A translational or rotational mass that will be moved thru a transmission by the motor."""
	def __init__(self, inertia, name = None):
		"""Initializes the load.

		inertia -- the inertia of the load. It can be either rotational or translational.
		name -- if provided, will be assigned to the load.
		"""
		self.inertia = inertia
		self.name = name

class system(object):
	"""A simulation system."""
	def __init__(self, motor, transmission, load):
		"""Initializes the system.

		motor -- a simulation.motor object
		transmission -- a mechanics.transformer object
		load -- a simulation.load object
		"""
		self.motor = motor
		self.transmission = transmission
		self.load = load

	def reflectedInertia(self):
		"""Returns the inertia of the load, as reflected thru the transmission to the motor.

		We are going to calculate this using an energy equivalency.
		"""
		input_distance = units.rad(1) #input of 1 radian (over 1 second)

		input_velocity = input_distance / units.s

		output_distance = self.transmission.forward(input_distance)

		output_velocity = output_distance / units.s

		output_energy = 0.5 * self.load.inertia * output_velocity**2 #0.5mv^2 or 0.5jw^2

		reflected_inertia = output_energy / (0.5*input_velocity**2)

		return (units.oz*units.inch**2)(reflected_inertia)

def sim_transmissionRatioSweep(subject_motor, subject_load, subject_transmission_type, transmission_ratio_min, transmission_ratio_max, target_velocity, sweep_points = 50, time_step = 0.000001):
	"""Simulates a sweep of the transmission ratio.

	subject_motor -- a motor instance
	subject_load -- a load instance
	subject_transmission_type -- a transmission class (NOT AN INSTANCE)
	transmission_ratio_min -- starting transmission ratio for the sweep
	transmission_ratio_max -- stopping transmission ratio for the sweep
	target_velocity -- the target velocity for measuring performance.

	returns a dataset of the simulation
	"""

	ratio_range = transmission_ratio_max/transmission_ratio_min
	ratio_step = ratio_range**(1/sweep_points)

	data = plotting.dataset([], (units.n, units.s))

	for sweep_index in range(sweep_points + 1):

		this_transmission_ratio = transmission_ratio_min*ratio_step**sweep_index
		
		this_transmission = subject_transmission_type(this_transmission_ratio)

		this_system = system(subject_motor, this_transmission, subject_load)

		time_to_target, sim_data = sim_timeToTargetVelocity(this_system, target_velocity, time_step)
		print('RATIO: ' + str(this_transmission_ratio) + ", TIME: " + str(time_to_target))

		data.add((this_transmission_ratio, time_to_target))

	return data



def sim_timeToTargetVelocity(subject_system, target_velocity, timestep = 0.001):
	"""Simulates a maximum-power acceleration to a target velocity.

	subject_system -- the system object to be simulated
	velocity_target -- the velocity at which the simulation ends
	timestep -- simulation step time, in seconds

	returns time_to_target, data
	"""

	subject_motor = subject_system.motor
	subject_transmission = subject_system.transmission
	subject_load = subject_system.load


	inertia_motor = subject_motor.inertia
	inertia_load = subject_system.reflectedInertia()

	inertia_total = inertia_motor + inertia_load

	step_time = units.s(timestep)
	simulation_time = units.s(0)

	data = plotting.dataset([], (units.s, target_velocity.units)) #(s, rad/s)

	motor_velocity = target_velocity.units(0)

	data.add((simulation_time, motor_velocity))

	while True:

		torque_applied = subject_motor(motor_velocity)

		motor_acceleration = torque_applied / inertia_total

		delta_velocity = motor_acceleration * step_time

		# print("INERTIA: " + str((units.kg*units.m**2)(inertia_total)))



		motor_velocity += delta_velocity
		simulation_time += step_time

		load_velocity = subject_transmission.forward(motor_velocity)

		data.add((simulation_time, load_velocity))

		if load_velocity >= target_velocity:
			return simulation_time, data
		else:
			continue



clearpath_CPM_SDSK_3411P_RLN = motor(plotting.dataset([(0,100), (3000, 100), (4000, 75)], (units.rev/units.min, units.ozf*units.inch)), max_speed = (units.rev/units.min)(4000), name = "Clearpath CPM-SDSK-3411P-RLN", inertia = (units.oz*units.inch**2)(3.9))
dummy_standard_DC = motor(plotting.dataset([(0,200), (4000, 0)], (units.rev/units.min, units.ozf*units.inch)), max_speed = (units.rev/units.min)(4000), name = "Dummy Standard DC Motor", inertia = (units.oz*units.inch**2)(3.9))
dummy_gas_engine = motor(plotting.dataset([(0,10), (1000, 200), (4000, 0)], (units.rev/units.min, units.ozf*units.inch)), max_speed = (units.rev/units.min)(4000), name = "Dummy Gas Engine", inertia = (units.oz*units.inch**2)(3.9))

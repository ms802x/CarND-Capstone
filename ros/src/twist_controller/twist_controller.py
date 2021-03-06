from yaw_controller import YawController
from pid import PID
from lowpass import LowPassFilter
import rospy


GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit,
                 accel_limit, wheel_radius, wheel_base, steer_ratio, max_lat_accel, max_steer_angle):
# yaw controller 
        self.yaw_controller=YawController(wheel_base, steer_ratio, .1,max_lat_accel, max_steer_angle) 
    # the PID constants terms
        kp=0.3
        ki=0.1
        kd=0
        min_throttle=0
        max_throttle=0.2
        self.throttle_controller=PID(kp,ki,kd,min_throttle,max_throttle)

        tau = 0.5 # will be used to calc cutoff frequency
        ts=.02 # sampling time
        
        self.vel_lpf=LowPassFilter(tau,ts)        
        self.vehicle_mass=vehicle_mass
        self.fuel_capacity=fuel_capacity
        self.brake_deadband=brake_deadband
        self.decel_limit=decel_limit
        self.accel_limit=accel_limit
        self.wheel_radius=wheel_radius
        
        self.last_time=rospy.get_time()
        
    def control(self, current_vel,dbw_enabled, linear_vel,angular_vel):
        
       # if not enabled(stop sign) stop the pid to stop error accumlation
        if not dbw_enabled:
            self.throttle_controller.reset()
            return 0.,0.,0.
        
        current_vel=self.vel_lpf.filt(current_vel)
        
        steering=self.yaw_controller.get_steering(linear_vel,angular_vel,current_vel)
        
        vel_error=linear_vel-current_vel
        self.last_vel=current_vel       
        
        current_time=rospy.get_time()
        sample_time=current_time-self.last_time
        self.last_time=current_time
        
        throttle=self.throttle_controller.step(vel_error,sample_time)
        brake=0
        

        if linear_vel ==0. and current_vel <0.1:
            throttle=0
            # In the walkthrough, only 400 Nm of torque is applied to hold the vehicle stationary. This turns out to be slightly less than the amount of force needed. To prevent Carla from moving you should apply approximately 700 Nm of torque.
            brake = 700
        

        elif throttle <0.1 and vel_error <0:
            throttle=0
            decel=max(vel_error,self.decel_limit)
            brake=abs(decel)*self.vehicle_mass*self.wheel_radius # torque 
        
        return throttle,brake,steering
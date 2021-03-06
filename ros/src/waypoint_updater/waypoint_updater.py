#!/usr/bin/env python

import rospy

from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
from scipy.spatial import KDTree
import numpy as np
from std_msgs.msg import Int32

import math


LOOKAHEAD_WPS = 100 # Number of waypoints we will publish. You can change this number


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
# I did not implement obstacle detection
        #        rospy.Subscriber('/obstacle_waypoint', Lane, self.obstacle_cb)

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        # init the varibles 
        self.base_waypoints= None
        self.pose = None
        self.waypoints_2d= None
        self.waypoint_tree= None
        self.stoplines_wp_idx = -1

        self.loop()

    def loop(self):
        # frequency of 50HZ
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            if self.pose and self.base_waypoints:
                closest_waypoint_idx = self.get_closest_waypoint_id()
                self.publish_waypoints(closest_waypoint_idx)
            rate.sleep()

    def get_closest_waypoint_id(self):
        x = self.pose.pose.position.x
        y = self.pose.pose.position.y
        closest_idx = self.waypoint_tree.query([x,y],1)[1]
#CHECK if ahed car
        closest_coord = self.waypoints_2d[closest_idx]
        prev_coord = self.waypoints_2d[closest_idx-1]
# hyperplane equations
        cl_vect = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect = np.array([x,y])
# refrence vector direction (we car only about sign)
        val = np.dot(cl_vect-prev_vect, pos_vect-cl_vect)

        if val > 0:
            closest_idx = (closest_idx+1) % len(self.waypoints_2d)
        return closest_idx

    def publish_waypoints(self,closest_idx):
        # in the walkthrough they have defined method called generate_lane()
        # since this method is actually empty I decided to do it here. 
        lane = Lane()
        lane.header = self.base_waypoints.header
        base_waypoints= self.base_waypoints.waypoints[closest_idx:closest_idx+LOOKAHEAD_WPS]
    
        if (self.stoplines_wp_idx == -1 or (self.stoplines_wp_idx >= closest_idx+LOOKAHEAD_WPS)):
            lane.waypoints = base_waypoints
        else:
        # slow down
            lane.waypoints = self.decelerate_wps(base_waypoints,closest_idx)
                
        self.final_waypoints_pub.publish(lane)

    def decelerate_wps(self,waypoints, closest_idx):  
        temp =[]
        MAX_DECEL=3 
        for i,wp in enumerate(waypoints): 
            p=Waypoint()
            p.pose=wp.pose
            # -2 and -3 can be set to avoid the car stop at the line of after the line
            stop_idx= max(self.stoplines_wp_idx - closest_idx - 3,0)
            # calculate distance from the line 
            dist = self.distance(waypoints, i , stop_idx)
            vel= math.sqrt(2*MAX_DECEL*dist)
            # Here instead of using the velocity of the car as a measure I will be using the distance from the line. Velocity can be used but maybe we need to set it when the velocity less than 0.5/1  m/s
     
            if dist < 1:
                vel=0
            p.twist.twist.linear.x = min(vel,wp.twist.twist.linear.x)
            temp.append(p)
            
        return temp
            
        
    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):
        self.base_waypoints = waypoints
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)



    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        self.stoplines_wp_idx=msg.data


    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
#!/usr/bin/python

from Shuttle import Shuttle
from time import sleep
import rospy
from shuttle_msgs.srv import DeliverPallet
from shuttle_msgs.msg import ShuttleStatus
from std_srvs.srv import Trigger
import thread

#create instance of shuttle object
shuttle = Shuttle()

#create publisher and status message
pub = rospy.Publisher('/shuttle_status', ShuttleStatus, queue_size=1)
g_station = [1,2,3,4,5,6]
g_convey = [0,0,0,0,0,0]
g_lock_status = thread.allocate_lock()

#marks if deliver service is currently in progress
g_serv_in_progress = False
g_lock_service = thread.allocate_lock()

def pub_status():
    status = ShuttleStatus()
    status.station = g_station
    while not rospy.is_shutdown():
        g_lock_status.acquire()
        status.convey_status = g_convey
        g_lock_status.release()
        pub.publish(status)
        sleep(0.1)

def setConveyStatus(station,status):
    g_lock_status.acquire()
    g_convey[station-1]=status
    g_lock_status.release()


def deliver_pallet(req):
    #require lock (wait till the other service is finished)
    g_lock_service.acquire()
    #check for error / wrong input
    if shuttle.error or not 0<req.source<7 or not 0<req.destination<7:
        g_lock_service.release()
        return False

    #execute service
    shuttle.goToStation(req.source)
    setConveyStatus(req.source, -1)
    shuttle.recievePallet(req.source)
    setConveyStatus(req.source, 0)
    shuttle.goToStation(req.destination)
    setConveyStatus(req.destination, 1)
    shuttle.handOutPallet(req.destination)
    setConveyStatus(req.destination, 0)
    shuttle.goToStation(0) # IDLE Position
    g_lock_service.release()
    if(shuttle.error):
        return False
    else:
        return True

def reset_shuttle(req):
    shuttle.reset()
    if shuttle.error:
        return False, "Reset not succesfull. Please remove pallet from shuttle."
    else:
        return True, "Reset succesfull."

if __name__ == '__main__':

    try:
        #setup ros
        rospy.init_node('shuttle_node', anonymous=True)
        #setup shuttle
        shuttle.getPosition()
        shuttle.goToStation(0)
        #setup ros Services
        serv_del = rospy.Service('/deliver_pallet',DeliverPallet, deliver_pallet)
        serv_reset = rospy.Service('/reset_shuttle',Trigger, reset_shuttle)
        #run publisher in seperate thread
        thread.start_new_thread( pub_status, ())
        #spin
        rospy.spin()

    except rospy.ROSInterruptException:
        pass

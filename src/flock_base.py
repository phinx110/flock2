#!/usr/bin/env python

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty
from flock2.msg import Flip

# XBox One joystick axes and buttons
_joy_axis_left_lr = 0           # Left stick left/right; 1.0 is left and -1.0 is right
_joy_axis_left_fb = 1           # Left stick forward/back; 1.0 is forward and -1.0 is back
_joy_axis_left_trigger = 2      # Left trigger
_joy_axis_right_lr = 3          # Right stick left/right; 1.0 is left and -1.0 is right
_joy_axis_right_fb = 4          # Right stick forward/back; 1.0 is forward and -1.0 is back
_joy_axis_right_trigger = 5     # Right trigger
_joy_axis_trim_lr = 6           # Trim left/right; 1.0 for left and -1.0 for right
_joy_axis_trim_fb = 7           # Trim forward/back; 1.0 for forward and -1.0 for back
_joy_button_A = 0               # A button
_joy_button_B = 1               # B button
_joy_button_X = 2               # X button
_joy_button_Y = 3               # Y button
_joy_button_left_bumper = 4     # Left bumper
_joy_button_right_bumper = 5    # Right bumper
_joy_button_view = 6            # View button
_joy_button_menu = 7            # Menu button
_joy_button_shift = 8           # XBox logo button
_joy_button_left_stick = 9      # Left stick button
_joy_button_right_stick = 10    # Right stick button


class FlockBase(Node):

    def __init__(self):
        super().__init__('flock_base')

        self._trim_speed = 0.25     # TODO parameter
        left_handed = False         # TODO parameter

        # Joystick assignments
        self._joy_axis_throttle = _joy_axis_left_fb if left_handed else _joy_axis_right_fb
        self._joy_axis_strafe = _joy_axis_right_lr
        self._joy_axis_vertical = _joy_axis_right_fb if left_handed else _joy_axis_left_fb
        self._joy_axis_yaw = _joy_axis_left_lr
        self._joy_button_takeoff = _joy_button_menu
        self._joy_button_land = _joy_button_view
        self._joy_button_flip_forward = _joy_button_Y
        self._joy_button_flip_left = _joy_button_X
        self._joy_button_flip_right = _joy_button_B
        self._joy_button_flip_back = _joy_button_A
        self._joy_button_left_bumper = _joy_button_left_bumper
        self._joy_axis_trim_lr = _joy_axis_trim_lr
        self._joy_axis_trim_fb = _joy_axis_trim_fb

        # Trim axis commands
        self._trim_targets_lr = \
            {
                (-1, False): (3, -1.0),
                (1, False): (3, 1.0),
                (-1, True): (1, -1.0),
                (1, True): (1, 1.0),
            } \
            if left_handed else \
            {
                (-1, False): (1, -1.0),
                (1, False): (1, 1.0),
                (-1, True): (3, -1.0),
                (1, True): (3, 1.0),
            }
        self._trim_targets_fb = \
            {
                (-1, False): (0, -1.0),
                (1, False): (0, 1.0),
                (-1, True): (2, -1.0),
                (1, True): (2, 1.0),
            } \
            if left_handed else \
            {
                (-1, False): (0, -1.0),
                (1, False): (0, 1.0),
                (-1, True): (2, -1.0),
                (1, True): (2, 1.0),
            }

        # Publications
        self._cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel')
        self._takeoff_pub = self.create_publisher(Empty, 'takeoff')
        self._land_pub = self.create_publisher(Empty, 'land')
        self._flip_pub = self.create_publisher(Flip, 'flip')

        # Subscriptions
        self.create_subscription(Joy, 'joy', self.joy_callback)

    def joy_axis_trim_process(self, msg, axis_id, trim_targets, twist):
        axis_value = msg.axes[axis_id]
        axis_state = -1 if axis_value < -0.5 else 1 if axis_value > 0.5 else 0
        left_bumper_pressed = msg.buttons[self._joy_button_left_bumper] != 0
        key = (axis_state, left_bumper_pressed)
        if key not in trim_targets:
            return False
        twist_field, twist_sign = trim_targets[key]
        twist_value = twist_sign * self._trim_speed
        print(key, trim_targets[key])
        if twist_field == 0:
            twist.linear.x = twist_value
        elif twist_field == 1:
            twist.linear.y = twist_value
        elif twist_field == 2:
            twist.linear.z = twist_value
        else:
            twist.angular.z = twist_value
        return True

    def joy_callback(self, msg):
        twist = Twist()

        trim_lr_pressed = self.joy_axis_trim_process(msg, self._joy_axis_trim_lr, self._trim_targets_lr, twist)
        trim_fb_pressed = self.joy_axis_trim_process(msg, self._joy_axis_trim_fb, self._trim_targets_fb, twist)

        if not trim_lr_pressed and not trim_fb_pressed:
            twist.linear.x = msg.axes[self._joy_axis_throttle]   # +x is forward, -x is back
            twist.linear.y = msg.axes[self._joy_axis_strafe]     # +y is left, -y is right
            twist.linear.z = msg.axes[self._joy_axis_vertical]   # +z is ascend, -z is descend
            twist.angular.z = msg.axes[self._joy_axis_yaw]       # +yaw is ccw, -yaw is cw

        self._cmd_vel_pub.publish(twist)

        if msg.buttons[self._joy_button_takeoff] != 0:
            self._takeoff_pub.publish(Empty())
        elif msg.buttons[self._joy_button_land] != 0:
            self._land_pub.publish(Empty())

        if msg.buttons[self._joy_button_flip_forward] != 0:
            self._flip_pub.publish(Flip(flip_command=Flip.FLIP_FORWARD))
        elif msg.buttons[self._joy_button_flip_left] != 0:
            self._flip_pub.publish(Flip(flip_command=Flip.FLIP_LEFT))
        elif msg.buttons[self._joy_button_flip_right] != 0:
            self._flip_pub.publish(Flip(flip_command=Flip.FLIP_RIGHT))
        elif msg.buttons[self._joy_button_flip_back] != 0:
            self._flip_pub.publish(Flip(flip_command=Flip.FLIP_BACK))


def main(args=None):
    rclpy.init(args=args)
    node = FlockBase()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Ctrl-C detected, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

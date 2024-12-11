from machine import Pin, time_pulse_us
import time


class UltrasonicSensor:
    def __init__(self, trigger_pin, echo_pin, detection_threshold=20, max_readings=10):
        self.trigger = Pin(trigger_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.DETECTION_THRESHOLD = detection_threshold
        self.MAX_READINGS = max_readings
        self.NO_RESPONSE = -1
        self.running = False

    def measure_distance(self):
        """
        Measure distance using ultrasonic sensor with error handling.

        Returns:
            float: Distance in cm or NO_RESPONSE if measurement fails
        """
        # Ensure trigger is low to start
        self.trigger.value(0)
        time.sleep(0.000002)

        # Send ultrasonic pulse
        self.trigger.value(1)
        time.sleep(0.00001)
        self.trigger.value(0)

        # Wait for echo and measure pulse duration
        try:
            duration = time_pulse_us(self.echo, 1, 30000)  # Reduced timeout
        except OSError:
            return self.NO_RESPONSE

        if duration < 0:
            return self.NO_RESPONSE

        # Calculate distance (speed of sound is 343 m/s)
        distance = (duration / 2) * 0.0343
        return round(distance, 2)

    def wait_for_detection(self):
        """
        Wait for a significant change in distance or initial detection.

        Returns:
            float: Detected distance or NO_RESPONSE
        """
        # Initialize circular buffer for readings
        readings = [self.NO_RESPONSE] * self.MAX_READINGS
        index: int = 0
        self.running = True

        while self.running:
            current_distance = self.measure_distance()
            readings[index] = current_distance
            index = (index + 1) % self.MAX_READINGS

            # Check previous reading
            prev_index = (index - 1) % self.MAX_READINGS
            prev_distance = readings[prev_index]

            # Detection conditions
            if (prev_distance == self.NO_RESPONSE and current_distance != self.NO_RESPONSE) or \
                    (current_distance != self.NO_RESPONSE and
                     abs(current_distance - prev_distance) > self.DETECTION_THRESHOLD):
                self.running = False
                return current_distance

            time.sleep(0.02)  # Use ms for better readability

    def stop(self):
        self.running = False

import runloop
import motor_pair
import color_sensor
from hub import port

motor_pair.pair(motor_pair.PAIR_1, port.C, port.D)
speed = 200
MAX_SEGMENT = 10# Maximum increment (degrees) to turn before checking sensor

async def turn_by(total_angle, direction, turn_type):
    remaining = total_angle
    while remaining > 0:
        segment = min(MAX_SEGMENT, remaining)
        print("Turning {} {}° segment in {} mode".format(direction, segment, turn_type))
        if turn_type == "arc":
            if direction == "right":
                await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, segment, speed, 0)
            else:
                await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, segment, 0, speed)
        else:
            if direction == "right":
                await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, segment, speed, -speed)
            else:
                await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, segment, -speed, speed)
        motor_pair.stop(motor_pair.PAIR_1)
        remaining -= segment
        if color_sensor.color(port.A) == 0:
            print("Black detected during turn segment; stopping movement.")
            motor_pair.stop(motor_pair.PAIR_1)
            return True
    return False

async def search_turn(initial_direction):
    def opposite(d):
        return "left" if d == "right" else "right"

    sequence = [
        (22, initial_direction, "arc"),
        (22, opposite(initial_direction), "arc"),
        (22, initial_direction, "arc"),
        (22, opposite(initial_direction), "arc"),
        (45, initial_direction, "inplace"),
        (45, opposite(initial_direction), "inplace"),
        (90, initial_direction, "inplace"),
        (90, opposite(initial_direction), "inplace"),
        (180, initial_direction, "inplace"),
        (180, opposite(initial_direction), "inplace")
    ]

    for angle, direction, turn_type in sequence:
        print("Command: Turn {} {}° in {} mode".format(direction, angle, turn_type))
        detected = await turn_by(angle, direction, turn_type)
        if detected:
            return
    last_direction = sequence[-1][1]
    print("Starting continuous spin in {} direction (inplace).".format(last_direction))
    while True:
        if last_direction == "right":
            motor_pair.move_tank(motor_pair.PAIR_1, speed, -speed)
        else:
            motor_pair.move_tank(motor_pair.PAIR_1, -speed, speed)
        await runloop.sleep_ms(50)
        if color_sensor.color(port.A) == 0:
            motor_pair.stop(motor_pair.PAIR_1)
            print("Black detected during continuous spin; stopping movement.")
            return

async def main():
    while True:
        if color_sensor.color(port.A) == 0:
            print("Sensor TRUE (black detected) - using initial direction RIGHT.")
            await search_turn("right")
        else:
            print("Sensor FALSE (black not detected) - using initial direction LEFT.")
            await search_turn("left")
        motor_pair.stop(motor_pair.PAIR_1)
        await runloop.sleep_ms(100)

runloop.run(main())

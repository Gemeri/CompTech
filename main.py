import runloop
import motor_pair
import color_sensor
from hub import port

motor_pair.pair(motor_pair.PAIR_1, port.C, port.D)
speed = 100

async def search_turn():
    turn_sequence = [(90, "right"), (180, "left"), (270, "right"), (360, "left")]
    for angle, direction in turn_sequence:
        print("Turning {} {}°".format(direction, angle))
        if direction == "right":
            await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, angle, speed, 0)
        else:
            await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, angle, 0, speed)
        if color_sensor.color(port.A) == 0:
            print("Black detected during turn")
            return True

    last_direction = turn_sequence[-1][1]
    print("Continuing to spin continuously to the {}.".format(last_direction))
    while True:
        if last_direction == "right":
            motor_pair.move_tank(motor_pair.PAIR_1, speed, 0)
        else:
            motor_pair.move_tank(motor_pair.PAIR_1, 0, speed)
        await runloop.sleep_ms(100)
        if color_sensor.color(port.A) == 0:
            motor_pair.stop(motor_pair.PAIR_1)
            print("Black detected while spinning")
            return True

async def main():
    while True:
        if color_sensor.color(port.A) == 0:
            print("Black detected - driving forward.")
            motor_pair.move_tank(motor_pair.PAIR_1, speed, speed)
        else:
            print("Black not detected - initiating search turn sequence.")
            found = await search_turn()
            if found:
                print("Black found - resuming forward drive.")
        await runloop.sleep_ms(100)

runloop.run(main())

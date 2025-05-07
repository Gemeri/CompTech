import runloop
import motor_pair
import motor
import color_sensor
import distance_sensor
import color
from hub import port, light_matrix, sound

# ======
# CONFIG
# ======
BLACK_THRESHOLD    = 50 # midpoint between black and white reflection
BASE_SPEED            = 300 # deg/sec forward for line follow
SEARCH_DELTA        = 20 # how much reflection can differ from black before we search for the line
Kp                    = 1 # gain for steering
CAN_APPROACH_DIST    = 200 # start going in on a can
CAN_DIST_THRESHOLD    = 50 # when to ram the can
CAN_APPROACH_SPEED    = 300 # deg/sec approach speed
KNOCK_SPEED        = 600 # deg/sec for the ram
KNOCK_DEGREES        = 180 # half rotation into the can
TURN_DEGREES        = 200 # 90 degree pivot in wheel degrees
TURN_SPEED            = KNOCK_SPEED # fast pivot speed
LOOP_DELAY_MS        = 10 # ms between sensor checks

async def search_for_line():
    deg22= int(TURN_DEGREES * 22/90)
    deg45= int(TURN_DEGREES * 45/90)
    deg90= TURN_DEGREES
    deg180 = TURN_DEGREES * 2

    sequence = [
        ('left',deg22),
        ('right', deg45),
        ('left',deg90),
        ('right', deg180),
        ('left',None)
    ]

    for direction, max_deg in sequence:
        if direction == 'left':
            l_speed, r_speed = -TURN_SPEED, TURN_SPEED
        else:
            l_speed, r_speed = TURN_SPEED, -TURN_SPEED

        start_l = motor.relative_position(port.C)
        start_r = motor.relative_position(port.D)
        motor_pair.move_tank(motor_pair.PAIR_1, l_speed, r_speed)

        while True:
            if color_sensor.color(port.A) == color.BLACK:
                motor_pair.stop(motor_pair.PAIR_1)
                return
            if max_deg is not None:
                cur_l = motor.relative_position(port.C)
                cur_r = motor.relative_position(port.D)
                turned = (abs(cur_l - start_l) + abs(cur_r - start_r)) / 2
                if turned >= max_deg:
                    break
            await runloop.sleep_ms(LOOP_DELAY_MS)
        motor_pair.stop(motor_pair.PAIR_1)

    motor_pair.move_tank(motor_pair.PAIR_1, -TURN_SPEED, TURN_SPEED)
    while color_sensor.color(port.A) != color.BLACK:
        await runloop.sleep_ms(LOOP_DELAY_MS)
    motor_pair.stop(motor_pair.PAIR_1)

async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.C, port.D)
    can_count= 0
    green_count = 0
    on_green    = False

    while True:
        if color_sensor.color(port.A) == color.RED:
            motor_pair.stop(motor_pair.PAIR_1)
            break

        dist = distance_sensor.distance(port.B)
        if 0 < dist < CAN_APPROACH_DIST:
            if dist > CAN_DIST_THRESHOLD:
                motor_pair.move(motor_pair.PAIR_1, 0, velocity=CAN_APPROACH_SPEED)
            else:
                can_count += 1
                motor_pair.stop(motor_pair.PAIR_1)
                await motor_pair.move_for_degrees(
                    motor_pair.PAIR_1,
                    KNOCK_DEGREES, 0,
                    velocity=KNOCK_SPEED
                )
                if can_count == 2:
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1, TURN_DEGREES, -100,
                        velocity=TURN_SPEED
                    )
                elif can_count == 7:
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1, TURN_DEGREES, 100,
                        velocity=TURN_SPEED
                    )
                else:
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1, TURN_DEGREES, -100,
                        velocity=TURN_SPEED
                    )
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1, TURN_DEGREES, 100,
                        velocity=TURN_SPEED
                    )
                while True:
                    motor_pair.move(motor_pair.PAIR_1, 0, velocity=BASE_SPEED)
                    c = color_sensor.color(port.A)
                    if c in (color.BLACK, color.GREEN):
                        break
                    await runloop.sleep_ms(LOOP_DELAY_MS)
            await runloop.sleep_ms(LOOP_DELAY_MS)
            continue

        # =======================
        # LINE FOLLOW WITH SEARCH
        # =======================

        reflect = color_sensor.reflection(port.A)
        if reflect > BLACK_THRESHOLD + SEARCH_DELTA or reflect < BLACK_THRESHOLD - SEARCH_DELTA:
            await search_for_line()
        else:
            error = BLACK_THRESHOLD - reflect
            steer = int(error * Kp)
            steer = max(-100, min(100, steer))
            motor_pair.move(motor_pair.PAIR_1, steer, velocity=BASE_SPEED)

        # =====================
        # GREEN SQUARE COUNTING
        # =====================

        if color_sensor.color(port.A) == color.GREEN:
            if not on_green:
                green_count += 1
                sound.beep(1000, 200, 100)
                on_green = True
        else:
            on_green = False

        await runloop.sleep_ms(LOOP_DELAY_MS)

    light_matrix.write(str(green_count))

runloop.run(main())

# ============
# WE'RE FUCKED
# ============

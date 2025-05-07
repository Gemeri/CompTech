import runloop
import motor_pair
import motor
import color_sensor
import distance_sensor
import color
from hub import port, light_matrix, sound

# =======
# CONFIG
# =======
BLACK_THRESHOLD    = 50# reflect% when centered on the black tape
BASE_SPEED        = 300# deg/sec forward for line-follow & resume
SEARCH_DELTA        = 20# reflect% beyond which we search for the line
Kp                = 1    # proportional gain for steering
CAN_APPROACH_DIST= 200# mm: start homing in on a can
CAN_DIST_THRESHOLD= 50# mm: when to ram the can
CAN_APPROACH_SPEED= 300# deg/sec approach speed
KNOCK_SPEED        = 600# deg/sec for the ram
KNOCK_DEGREES    = 180# half-rotation into the can
TURN_DEGREES        = 200# wheel degrees ≈ 90° pivot
TURN_SPEED        = KNOCK_SPEED# fast pivot speed
LOOP_DELAY_MS    = 10# ms between sensor checks

async def search_for_line():
    step_wheel = int(round(TURN_DEGREES * 10 / 90))
    targets = [10, 22, 45, 90, 180, 360]

    for idx, deg in enumerate(targets):
        direction = -1 if idx % 2 == 0 else 1# L, R, L, R...
        limit = int(round(TURN_DEGREES * deg / 90))
        turned = 0

        while turned < limit:
            dist = distance_sensor.distance(port.B)
            if 0 < dist < CAN_APPROACH_DIST:
                motor_pair.stop(motor_pair.PAIR_1)
                return

            await motor_pair.move_for_degrees(
                motor_pair.PAIR_1,
                step_wheel,
                direction * 100,
                velocity=TURN_SPEED
            )
            turned += step_wheel

            if color_sensor.reflection(port.A) < BLACK_THRESHOLD:
                motor_pair.stop(motor_pair.PAIR_1)
                return

        motor_pair.stop(motor_pair.PAIR_1)

    while True:
        dist = distance_sensor.distance(port.B)
        if 0 < dist < CAN_APPROACH_DIST:
            motor_pair.stop(motor_pair.PAIR_1)
            return

        if color_sensor.reflection(port.A) < BLACK_THRESHOLD:
            return

        await motor_pair.move_for_degrees(
            motor_pair.PAIR_1,
            step_wheel,
            -100,
            velocity=TURN_SPEED
        )

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
                    motor_pair.PAIR_1, KNOCK_DEGREES, 0,
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
                    r = color_sensor.reflection(port.A)
                    if r < BLACK_THRESHOLD or color_sensor.color(port.A) == color.GREEN:
                        break
                    await runloop.sleep_ms(LOOP_DELAY_MS)
            await runloop.sleep_ms(LOOP_DELAY_MS)
            continue

        refl = color_sensor.reflection(port.A)
        if refl < BLACK_THRESHOLD:
            motor_pair.move(motor_pair.PAIR_1, 0, velocity=BASE_SPEED)
        elif refl > BLACK_THRESHOLD + SEARCH_DELTA:
            await search_for_line()
        else:
            error = BLACK_THRESHOLD - refl
            steer = int(error * Kp)
            steer = max(-100, min(100, steer))
            motor_pair.move(motor_pair.PAIR_1, steer, velocity=BASE_SPEED)

        if color_sensor.color(port.A) == color.GREEN:
            if not on_green:
                green_count += 1
                on_green = True
        else:
            on_green = False

        await runloop.sleep_ms(LOOP_DELAY_MS)

    light_matrix.write(str(green_count))

runloop.run(main())

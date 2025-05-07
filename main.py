import runloop
import motor_pair
import color_sensor
import distance_sensor
import color

from hub import port, light_matrix, sound

async def main():
    # —— CONFIG ——
    BLACK_THRESHOLD       = 50    # midpoint between black & white reflection
    BASE_SPEED            = 300   # deg/sec forward for line-follow & continue
    Kp                    = 1     # proportional gain for line steering
    CAN_APPROACH_DIST     = 200   # mm: start homing in on a can
    CAN_DIST_THRESHOLD    = 50    # mm: when to ram the can
    CAN_APPROACH_SPEED    = 300   # deg/sec approach speed
    KNOCK_SPEED           = 600   # deg/sec for the initial ram
    KNOCK_DEGREES         = 180   # half-rotation to push into the can
    TURN_DEGREES          = 200   # approx. 90° pivot in wheel degrees
    TURN_SPEED            = KNOCK_SPEED  # fast turn to knock over can
    LOOP_DELAY_MS         = 10    # ms between loop iterations

    # Pair left/right drive motors
    motor_pair.pair(motor_pair.PAIR_1, port.C, port.D)

    can_count   = 0
    green_count = 0
    on_green    = False

    while True:
        # — 1) FINISH? — stop on big red rectangle
        if color_sensor.color(port.A) == color.RED:
            motor_pair.stop(motor_pair.PAIR_1)
            break

        # — 2) CAN HANDLING — approach, ram, turn, then continue
        dist = distance_sensor.distance(port.B)
        if 0 < dist < CAN_APPROACH_DIST:
            if dist > CAN_DIST_THRESHOLD:
                # drive straight toward the can
                motor_pair.move(motor_pair.PAIR_1, 0, velocity=CAN_APPROACH_SPEED)
            else:
                # — RAM THE CAN —
                can_count += 1
                motor_pair.stop(motor_pair.PAIR_1)
                await motor_pair.move_for_degrees(
                    motor_pair.PAIR_1,
                    KNOCK_DEGREES,
                    0,
                    velocity=KNOCK_SPEED
                )

                # — IMMEDIATE TURN —  
                if can_count == 2:
                    # 90° left
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1,
                        TURN_DEGREES,
                        -100,
                        velocity=TURN_SPEED
                    )
                elif can_count == 7:
                    # 90° right
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1,
                        TURN_DEGREES,
                        100,
                        velocity=TURN_SPEED
                    )
                else:
                    # left then right
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1,
                        TURN_DEGREES,
                        -100,
                        velocity=TURN_SPEED
                    )
                    await motor_pair.move_for_degrees(
                        motor_pair.PAIR_1,
                        TURN_DEGREES,
                        100,
                        velocity=TURN_SPEED
                    )

                # — CONTINUE FORWARD until black line or green square —
                while True:
                    motor_pair.move(motor_pair.PAIR_1, 0, velocity=BASE_SPEED)
                    c = color_sensor.color(port.A)
                    if c in (color.BLACK, color.GREEN):
                        break
                    await runloop.sleep_ms(LOOP_DELAY_MS)

            # pause briefly, then re-evaluate sensors
            await runloop.sleep_ms(LOOP_DELAY_MS)
            continue

        # — 3) ZIG-ZAG LINE FOLLOW —
        reflect  = color_sensor.reflection(port.A)
        error    = reflect - BLACK_THRESHOLD
        steering = -error * Kp
        steering = max(-100, min(100, steering))  # clamp to [-100,100]

        motor_pair.move(motor_pair.PAIR_1, steering, velocity=BASE_SPEED)

        # — 4) GREEN-SQUARE COUNTING —
        if color_sensor.color(port.A) == color.GREEN:
            if not on_green:
                green_count += 1
                sound.beep(1000, 200, 100)
                on_green = True
        else:
            on_green = False

        await runloop.sleep_ms(LOOP_DELAY_MS)

    # — COURSE COMPLETE —
    light_matrix.write(str(green_count))

runloop.run(main())

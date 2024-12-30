import enum
import threading
import time
from textwrap import dedent


class State(enum.Enum):
    NOT_STARTED = threading.Event()
    MENU = threading.Event()
    SYSTEM = threading.Event()
    EXIT = threading.Event()

    def __repr__(self):
        return "<%s.%s>" % (self.__class__.__name__, self._name_)


def set_state(s: State):
    global state
    state.value.clear()
    state = s
    state.value.set()


state = State.NOT_STARTED
prog_launch = time.time()
modify = threading.Lock()


def get_positive_int(prompt) -> int:
    print(prompt, end='')
    while True:
        try:
            i = int(input())
            assert i > 0
            return i
        except (ValueError, AssertionError):
            print('Error! Incorrect Input. Try again: ', end='')


print('Welcome to the traffic management system!')
roads = get_positive_int('Input the number of roads: ')
interval = get_positive_int('Input the interval: ')
queue_roads = []
interval_time = []  # arrays of


def menu_thread():
    print(dedent('''\
        Menu:
        1. Add road
        2. Delete road
        3. Open system
        0. Quit'''))

    try:
        line = int(input())
        assert line in range(4)
    except (ValueError, AssertionError):
        print('Incorrect option')
        input()  # not clearing console and requires wait on newline to pass test
        return

    match line:
        case 1:
            line = input('Input road name: ')
            with modify:
                if len(queue_roads) >= roads:
                    print('queue is full')
                else:
                    if len(queue_roads) == 0:
                        queue_roads.append(line)
                        interval_time.append([interval, True])
                    else:
                        queue_roads.append(line)
                        interval_time.append([max(i[0] for i in interval_time)+interval, False])
                        if len(queue_roads) == 2:
                            interval_time[1][0] -= interval
                    print(f'{line} Added')
            input()

        case 2:
            with modify:
                if len(queue_roads) <= 0:
                    print('queue is empty')
                else:
                    road = queue_roads.pop(0)
                    interval_time.pop(0)
                    print(f'{road} Deleted')
            input()
        case 3:
            print('System Opened')
            set_state(State.SYSTEM)
        case 0:
            print('Bye!')
            set_state(State.EXIT)
            return

    # input()  # test requirement


def tick():
    with modify:
        if any(sl[1] for sl in interval_time):
            # perform tick on existing true
            for i, (secs, is_open) in enumerate(interval_time):
                if secs <= 1 and is_open:
                    if len(queue_roads) == 1:
                        interval_time[i] = [interval, True]
                    else:
                        interval_time[i] = [len(queue_roads)*interval - interval, False]  # close the light and reset timer to max
                elif secs <= 1 and not is_open:
                    interval_time[i] = [interval, True]  # open for the interval duration
                else:
                    interval_time[i][0] -= 1
        else:  # when none are open make next in queue open
            if queue_roads:
                interval_time[0] = [interval, True]
            for i, (secs, is_open) in enumerate(interval_time):
                if i == 0:
                    continue
                interval_time[i][0] = i * interval


if __name__ == '__main__':
    def worker():
        while state != State.EXIT:
            time.sleep(1)
            match state:
                case State.SYSTEM:
                    elapsed_time = time.time() - prog_launch
                    print(dedent(f"""\
                        ! {int(elapsed_time)}s. have passed since system startup !
                        ! Number of roads: {roads} !
                        ! Interval: {interval} !
                        """))
                    for road, (secs, is_open) in zip(queue_roads, interval_time):
                        print(f'Road "{road}" will be {"open" if is_open else "closed"} for {secs}s.')
                    print()
                    print("""! Press "Enter" to open menu !""")

            tick()


    t = threading.Thread(target=worker, name='QueueThread')
    t.start()

    set_state(State.MENU)
    while state != State.EXIT:
        match state:
            case State.MENU:
                menu_thread()
            case State.SYSTEM:
                line = input()
                if line == '':
                    state = State.MENU

    t.join()

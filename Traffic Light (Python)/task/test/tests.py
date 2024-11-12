import re
import time
import threading
from hstest import StageTest, CheckResult, WrongAnswer, TestedProgram, dynamic_test


class SystemOutput:

    def __init__(self, interval: int, max_roads: int, seconds: int, road_lines: list):
        self.interval = interval
        self.max_roads = max_roads
        self.seconds = seconds
        self.road_lines = road_lines


class Road:
    def __init__(self, line: str, parse_roads: bool):
        self.line = line
        if parse_roads:
            if "open" not in line and "closed" not in line:
                raise WrongAnswer("All lines with elements in queue should contain \"open\" or \"closed\" " +
                                  "substring, describing it's state.")
            match = re.search(r"((?!(\d+)s\.).)*(\d+)s\.((?!(\d+)s\.).)*", line)
            if match is None:
                raise WrongAnswer("All lines with elements in queue should contain only one \"Ns.\" substring " +
                                  "(where N is a number) - amount of seconds until it closes/opens")
            self.seconds = int(match.group(3))
        else:
            self.seconds = -1

    def is_open(self):
        return "open" in self.line

    def __str__(self):
        index = self.line.index("n3w_v3ry_unu5u4l_r04d_n4m3_")
        return f"Road{self.line[index + 27]}, {'open' if self.is_open() else 'closed'}, {self.seconds}s."


def check_menu(lines, test_case):
    ADD_INFO = f"Incorrect menu output in the following case: {test_case}. "
    if len(lines) != 5:
        raise WrongAnswer(f"{ADD_INFO}It should contain exactly 5 lines but there were {len(lines)} instead")
    if "menu" not in lines[0]:
        raise WrongAnswer(f"{ADD_INFO}First line should contain \"Menu\" substring")

    starts = ["1", "2", "3", "0"]
    contain = ["Add", "Delete", "System", "Quit"]
    for i in range(len(starts)):
        if not lines[1 + i].startswith(starts[i]) or not contain[i].lower() in lines[1 + i]:
            raise WrongAnswer(
                f"The {i + 1} line of menu list should start with \"{starts[i]}\" as an option from list and " +
                f"contain \"{contain[i]}\" substring as in example")


def parse_string_info(lines: list, parse_roads: bool):
    pattern = r"(\D*)(\d+)(\D*)"
    match = re.search(pattern, lines[0])
    if match is None:
        raise WrongAnswer("The line, that shows time since the start of the program, should contain " +
                          "only one integer - amount of seconds")
    seconds = int(match.group(2))

    match = re.search(pattern, lines[1])
    if match is None:
        raise WrongAnswer("The line, that shows number of roads, provided by user, should contain " +
                          "only one integer - exact number, that was set by user")
    max_roads = int(match.group(2))

    match = re.search(pattern, lines[2])
    if match is None:
        raise WrongAnswer("The line, that shows interval, provided by user, should contain " +
                          "only one integer - interval, that was set by user")
    interval = int(match.group(2))

    road_lines = [Road(lines[i], parse_roads) for i in range(3, len(lines) - 1)]
    return SystemOutput(interval, max_roads, seconds, road_lines)


def get_system_info(output: str, roads_amount: int, parse_roads: bool):
    lines = re.split(r"[\r\n]+", output.lower().strip())

    if len(lines) != 4 and roads_amount == 0:
        raise WrongAnswer("System information printed each second should contain exactly 4 " +
                          "non-empty lines, when no roads were added: one that shows amount of time since the start "
                          "of the program, next two should show the provided initial settings and the last, that asks"
                          " user to press Enter to show options, as in example")

    if roads_amount != 0 and len(lines) != 4 + roads_amount:
        raise WrongAnswer("When the user provided any changes to queue, output of system mode should " +
                          "change. There should be exactly 4+n non-empty lines, where n is the amount of elements in " +
                          "queue, in such order, just like in the example:\n" +
                          "1. Line, that shows amount of time since the start of the program\n" +
                          "2. Line, that shows max number of elements, provided by user\n" +
                          "3. Line, that shows interval, provided by user\n" +
                          "...\n" +
                          "*queue*\n" +
                          "...\n" +
                          "n+4. Line, that that asks user to press 'Enter' to show options")

    if "number" not in lines[1]:
        raise WrongAnswer("The line, that shows number of roads, provided by user, should contain " +
                          "\"number\" substring")
    if "interval" not in lines[2]:
        raise WrongAnswer("The line, that shows interval, provided by user, should contain " +
                          "\"interval\" substring")
    if "enter" not in lines[-1]:
        raise WrongAnswer("The last line, that asks user to press Enter to show options should contain" +
                          " \"Enter\" substring")

    return parse_string_info(lines, parse_roads)


def get_users_thread(thread_name: str):
    users_thread = None
    for t in threading.enumerate():
        if t.getName() == thread_name:
            users_thread = t
    if users_thread is None:
        raise WrongAnswer("There should be created new thread when number of roads and interval settings were " +
                          "set, named as \"QueueThread\". Make sure, that it was created properly and was not misspelled")
    return users_thread


def await_output_at_start(pr: TestedProgram):
    output = None
    millis_await = 0
    output_performed = False
    while millis_await < 1050 and not output_performed:
        time.sleep(0.05)
        millis_await += 50
        output = pr.get_output().lower()
        if output != "":
            output_performed = True
    if output == "" or millis_await > 1050:
        raise WrongAnswer("When the user selected '3' as an option, program should print new system " +
                          "information each second, but after 1 second of waiting there was no output.")
    time.sleep(0.2)
    add_output = pr.get_output().lower()
    return output + add_output


def reveal_test(previous: SystemOutput, users_output: SystemOutput, correct: str, action_in_between: str, interval: int,
                reveal: bool):
    if not reveal:
        return ""

    correct_roads = correct.split(";")
    if previous is None:
        action_in_between = "Started. " + action_in_between
    output = f"---Interval: {interval}---\n"
    if previous is not None:
        output += "...\n"
        for r in previous.road_lines:
            output += f'{r}\n'
    output += f"---Performed action: {action_in_between}---\n"

    expected = ""
    got = ""

    for j in range(len(users_output.road_lines)):
        data = correct_roads[j].split(",")
        got_output = str(users_output.road_lines[j]) + "\n"
        got_seconds = users_output.road_lines[j].seconds
        got += got_output

        if users_output.road_lines[j].is_open() != (data[0] == "1"):
            got_output = got_output.replace("closed", "^*#").replace("open", "closed").replace("^*#", "open")
        if got_seconds != int(data[1]):
            got_output = got_output.replace(str(got_seconds) + "s.", data[1] + "s.")
        expected += got_output
    if expected == "":
        expected = "(No roads)\n"
    if got == "":
        got = "(No roads)\n"
    return f" Formal snippet of expected/got output:\n{output}---Expected:---\n{expected}---Got:---\n{got}"


def process_conditions(output: str, exp: str, previous: SystemOutput, roads_amount: int, interval: int, reveal: bool,
                       action_in_between: str):
    info = get_system_info(output, roads_amount, True)
    roads = [] if exp == "" else exp.split(";")

    if len(info.road_lines) != len(roads):
        raise WrongAnswer(
            f"Incorrect number of roads was found in output after action: "
            f"{'Started. ' + action_in_between if previous is None else action_in_between}")
    for j in range(len(info.road_lines)):
        data = roads[j].split(",")
        if info.road_lines[j].is_open() != (data[0] == "1"):
            raise WrongAnswer("Some roads describe their state incorrectly. Road should be \"closed\", " +
                              "but found \"open\" or vise versa." + reveal_test(previous, info, exp, action_in_between,
                                                                                interval, reveal))
        if info.road_lines[j].seconds != int(data[1]):
            raise WrongAnswer("Some roads' time to close/open is incorrect." + reveal_test(previous, info, exp,
                                                                                           action_in_between,
                                                                                           interval, reveal))
    return info


def get_system_output_in_seconds(pr: TestedProgram, seconds: int):
    output = await_output_at_start(pr)
    if seconds > 1:
        time.sleep((1050 * (seconds - 1)) / 1000)
        new_output = pr.get_output().lower()
        output += new_output
    outputs = []
    tmp = ""
    for line in output.split("\n"):
        tmp += line + "\n"
        if "enter" in line:
            outputs.append(tmp)
            tmp = ""
    if tmp.strip() != "":
        outputs.append(tmp)
    return outputs


def process_system_seconds_initial(info: SystemOutput, start_second: int, init_roads: int, init_interval: int):
    if start_second != -1:
        if info.seconds != start_second + 1:
            raise WrongAnswer("Time difference between two outputs (current and a second earlier)" +
                              f" is not equal to 1:\nSecond earlier: {start_second}\nCurrent: {info.seconds}")
        if info.max_roads != init_roads:
            raise WrongAnswer("Line with initial setting (number of roads) shows incorrect value.")
        if info.interval != init_interval:
            raise WrongAnswer("Line with initial setting (interval) shows incorrect value.")
    return info.seconds


class TrafficLightTest(StageTest):
    name = "n3w_v3ry_unu5u4l_r04d_n4m3_"

    @dynamic_test
    def test_initial_and_menu(self):
        pr = TestedProgram()
        output = pr.start().lower()
        lines = re.split(r"[\r\n]+", output.strip())

        if len(lines) != 2:
            return CheckResult.wrong("There should be exactly 2 lines in the output when the program just started, " +
                                     f"but there were {len(lines)} instead")

        if ("welcome" not in lines[0]) or ("traffic management system" not in lines[0]):
            return CheckResult.wrong("The first line of output should contain a greeting, as in example")
        if ("input" not in lines[1]) or ("number" not in lines[1]):
            return CheckResult.wrong("When the program just started, there should be a line, that asks user to input " +
                                     "number of roads with \"Input\" and \"Number\" substrings")

        output = pr.execute("5").lower()
        lines = re.split(r"[\r\n]+", output.strip())

        if len(lines) != 1:
            return CheckResult.wrong("There should be exactly 1 line printed when the user inputted desired number " +
                                     f"of roads, but there were {len(lines)} instead")
        if ("input" not in lines[0]) or ("interval" not in lines[0]):
            return CheckResult.wrong("When the user provided number of roads, there should be a line, that asks user " +
                                     "to input interval value with \"Input\" and \"Interval\" substrings")

        output = pr.execute("3").lower()
        check_menu(re.split(r"[\r\n]+", output.strip()), "Start of the program")

        pr.execute("0")
        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        return CheckResult.correct()

    @dynamic_test
    def test_incorrect_initial(self):
        pr = TestedProgram()
        pr.start()

        for ex in ["asd", "-1", "6-", "0", "Hello world!"]:
            output = pr.execute(ex).lower()
            lines = re.split(r"[\r\n]+", output.strip())
            if len(lines) != 1 or "incorrect input" not in lines[0] or "again" not in lines[0]:
                return CheckResult.wrong(
                    "When the user provides incorrect input for number of roads (<=0 or not numeric),"
                    " there should be printed exactly one line, containing \"incorrect input\" and " +
                    "\"again\" substrings, followed by new input for number of roads")
        output = pr.execute("5").lower()
        lines = re.split(r"[\r\n]+", output.strip())

        if len(lines) != 1:
            return CheckResult.wrong(
                "There should be exactly 1 line printed when the user inputted desired number of roads, " +
                f"but there were {len(lines)} instead")
        if ("input" not in lines[0]) or ("interval" not in lines[0]):
            return CheckResult.wrong("When the user provided number of roads, there should be a line, that asks user " +
                                     "to input interval value with \"Input\" and \"Interval\" substrings")

        for ex in ["asd", "-1", "6-", "0", "Hello world!"]:
            output = pr.execute(ex).lower()
            lines = re.split(r"[\r\n]+", output.strip())
            if len(lines) != 1 or "incorrect input" not in lines[0] or "again" not in lines[0]:
                return CheckResult.wrong(
                    "When the user provides incorrect input for interval value (<=0 or not numeric),"
                    " there should be printed exactly one line, containing \"incorrect input\" and " +
                    "\"again\" substrings, followed by new input for interval value")

        output = pr.execute("5").lower()
        check_menu(re.split(r"[\r\n]+", output.strip()),
                   "Start of the program after correct input for initial settings")

        pr.execute("0")
        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        return CheckResult.correct()

    @dynamic_test
    def test_incorrect_options(self):
        pr = TestedProgram()
        pr.start()
        pr.execute("5")
        pr.execute("3")

        for ex in ["asd", "-1", "6-", "Hello world!", "4", "-5"]:
            output = pr.execute(ex).lower()
            lines = re.split(r"[\r\n]+", output.strip())
            if len(lines) != 1 or "incorrect option" not in lines[0]:
                return CheckResult.wrong(
                    "When the user provides incorrect input while choosing an option (not '1', '2' or " +
                    "'3'), there should be printed exactly one line, containing \"incorrect option\" " +
                    "substring, followed by input to return back to menu")

            output = pr.execute("").lower()
            check_menu(re.split(r"[\r\n]+", output.strip()), "New iteration after incorrect input for option")

        pr.execute("0")
        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        return CheckResult.correct()

    @dynamic_test(data=["1", "24367587"])
    def test_system_info(self, init):
        pr = TestedProgram()
        pr.start()
        pr.execute(init)
        pr.execute(init)

        users_thread = get_users_thread("QueueThread")
        pr.execute("3")
        outputs = get_system_output_in_seconds(pr, 4)

        prev_seconds = -1
        for info in outputs:
            so_info = get_system_info(info, 0, False)
            prev_seconds = process_system_seconds_initial(so_info, prev_seconds, int(init), int(init))

        output = pr.execute("").lower()
        check_menu(re.split(r"[\r\n]+", output.strip()), "Pressed \"Enter\" to return from system mode")

        pr.execute("3")
        pr.get_output()
        new_output = get_system_output_in_seconds(pr, 1)[0]
        so_info = get_system_info(new_output, 0, False)
        process_system_seconds_initial(so_info, prev_seconds, int(init), int(init))

        pr.execute("")
        pr.execute("0")

        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        users_thread.join(3000)
        if users_thread.is_alive():
            return CheckResult.wrong("You should kill the created thread when the program is finished")

        return CheckResult.correct()

    data_for_actions = [
        ["1", ["2", "1", "1", "2", "1"], [2, 3, 1, 4, 3]],
        ["2", ["2", "1", "1", "1", "2", "2", "2", "1"], [2, 3, 3, 1, 4, 4, 2, 3]]
    ]

    @dynamic_test(data=data_for_actions)
    def test_roads_menu_output(self, init, actions, result):
        pr = TestedProgram()
        pr.start()
        pr.execute(init)
        pr.execute(init)

        names = []

        for i in range(len(actions)):
            output = pr.execute(actions[i]).lower()
            lines = re.split(r"[\r\n]+", output.strip())
            if actions[i] == "1":
                if len(lines) != 1 or "input" not in lines[0]:
                    return CheckResult.wrong(
                        "When the user selected '1' as an option, program should print " +
                        "exactly 1 line, that contains \"input\" substring, followed by new input for element's name")
                output = pr.execute(self.name + str(i)).lower()
                lines = re.split(r"[\r\n]+", output.strip())

            if result[i] == 1:
                if len(lines) != 1 or "queue is full" not in output:
                    return CheckResult.wrong(
                        "When the user selected '1' as an option and provided new road's name, " +
                        "while queue is full, program should print exactly 1 line, that contains \"queue is full\" " +
                        "substring.")
            elif result[i] == 2:
                if len(lines) != 1 or "queue is empty" not in output:
                    return CheckResult.wrong(
                        "When the user selected '2' as an option, while queue is empty, " +
                        "program should print exactly 1 line, that contains \"queue is empty\" substring.")
            elif result[i] == 3:
                if len(lines) != 1 or "add" not in output or (self.name + str(i)) not in output:
                    return CheckResult.wrong(
                        "When the user selected '1' as an option and successfully added new road, " +
                        "program should print exactly 1 line, that contains road's name and \"add\" substrings.")
                names.append(self.name + str(i))
            elif result[i] == 4:
                if len(lines) != 1 or "delete" not in output or (names[0]) not in output:
                    return CheckResult.wrong(
                        "When the user selected '2' as an option and successfully removed a road, " +
                        "program should print exactly 1 line, that contains road's name and \"delete\" substrings.")
                names.pop(0)
            check_menu(re.split(r"[\r\n]+", pr.execute("").lower().strip()),
                       "New iteration after attempt to delete/add a road")
        pr.execute("0")
        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        return CheckResult.correct()

    @dynamic_test(data=data_for_actions)
    def test_system_info_with_roads(self, init, actions, result):
        pr = TestedProgram()
        pr.start()
        pr.execute(init)
        pr.execute(init)

        names = []
        for i in range(len(actions)):
            pr.execute(actions[i])
            if actions[i] == "1":
                pr.execute(self.name + str(i))
            if result[i] == 3:
                names.append(self.name + str(i))
            if result[i] == 4:
                names.pop(0)
            pr.execute("")

            pr.execute("3")
            output = get_system_output_in_seconds(pr, 1)[0]
            info = get_system_info(output, len(names), False)

            if len(info.road_lines) != len(names):
                return CheckResult.wrong("The amount of printed road lines from the system output is incorrect.")

            for j in range(len(names)):
                if names[j] not in info.road_lines[j].line:
                    return CheckResult.wrong(
                        "Between settings lines and the line, that asks user to press Enter to show " +
                        "options, there should be printed all elements in queue from front to rear, containing " +
                        "elements' names in such order.")
            pr.execute("")

        pr.execute("0")
        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        return CheckResult.correct()

    # maxRoads, interval, reveal, correct
    # 2 roads, with interval 2
    # 3 roads, with interval 1
    # 4 roads, with interval 3
    # 4 roads, with interval 1
    final_actions_simple = [
        [2, 2, True, ["1,2;0,2", "1,1;0,1", "0,2;1,2", "0,1;1,1", "1,2;0,2", "1,1;0,1"]],
        [2, 1, True, ["1,1;0,1", "0,1;1,1", "1,1;0,1"]],
        [3, 3, True, ["1,3;0,3;0,6", "1,2;0,2;0,5", "1,1;0,1;0,4",
                       "0,6;1,3;0,3", "0,5;1,2;0,2", "0,4;1,1;0,1",
                       "0,3;0,6;1,3", "0,2;0,5;1,2", "0,1;0,4;1,1",
                       "1,3;0,3;0,6", "1,2;0,2;0,5", "1,1;0,1;0,4"]
         ],
        [3, 1, True, ["1,1;0,1;0,2", "0,2;1,1;0,1", "0,1;0,2;1,1", "1,1;0,1;0,2"]]
    ]

    # 2 roads, with interval 2, 1 road, 1 seconds, 1 road, 2 seconds, remove road, 2 seconds, remove road, 2 seconds

    # 3 roads, with interval 3, 1 road, 1 seconds, 1 road, 1 seconds, 1 road, 2 seconds, remove road, 2 seconds,
    # remove road, 2 seconds, remove road, 2 seconds
    final_actions_advanced = [
        [2, 2, True, ["1,2", "1,1;0,1", "0,2;1,2", "1,1", "1,2", "", ""]],
        [3, 3, True, ["1,3", "1,2;0,2", "1,1;0,1;0,4", "0,6;1,3;0,3", "1,2;0,2", "1,1;0,1", "1,3", "1,2", "", ""]]
    ]

    @dynamic_test(order=7, data=final_actions_simple)
    def test_roads_conditions_simple(self, max_roads, interval, reveal, correct):
        pr = TestedProgram()
        pr.start()
        pr.execute(str(max_roads))
        pr.execute(str(interval))

        for i in range(max_roads):
            pr.execute("1")
            pr.execute(self.name + str(i))
            pr.execute("")

        pr.execute("3")
        outputs = get_system_output_in_seconds(pr, interval * (max_roads + 1))

        pr.execute("")
        pr.execute("0")

        if not pr.is_finished():
            return CheckResult.wrong("When user inputted '0' as a desired option, program should finish it's execution")

        if len(outputs) < len(correct):
            return CheckResult.wrong(
                "Incorrect number of system outputs was found. Make sure, that system prints new info" +
                " each second")

        previous = None

        for i in range(len(correct)):
            previous = process_conditions(outputs[i], correct[i], previous, max_roads, interval, reveal,
                                          f"Added {max_roads} roads." if previous is None else "Waited 1 second.")
        return CheckResult.correct()

    @dynamic_test(data=final_actions_advanced)
    def test_roads_conditions_advanced(self, max_roads, interval, reveal, correct):
        pr = TestedProgram()
        pr.start()
        pr.execute(str(max_roads))
        pr.execute(str(interval))

        previous = None
        number = 0
        j = 0

        for i in range(max_roads):
            pr.execute("1")
            pr.execute(self.name + str(i))
            pr.execute("")
            pr.execute("3")

            output = get_system_output_in_seconds(pr, 1)[0]
            number += 1
            previous = process_conditions(output, correct[j], previous, number, interval, reveal,
                                          f"Added 1 road." if previous is None else "Added 1 road. Waited 1 second.")
            j += 1
            pr.execute("")

        pr.execute("3")
        output = get_system_output_in_seconds(pr, 1)[0]
        previous = process_conditions(output, correct[j], previous, number, interval, reveal, "Waited 1 second.")
        j += 1
        pr.execute("")

        for i in range(max_roads):
            pr.execute("2")
            pr.execute("")
            pr.execute("3")

            try:
                outputs = get_system_output_in_seconds(pr, 2)
                number -= 1
                previous = process_conditions(outputs[0], correct[j], previous, number, interval, reveal,
                                              "Deleted 1 road. Waited 1 second.")
                j += 1
                previous = process_conditions(outputs[1], correct[j], previous, number, interval, reveal,
                                              "Deleted 1 road. Waited 1 second.")
                j += 1
                pr.execute("")
            except IndexError:
                return CheckResult.wrong(
                    "Can't parse the information about the amount of time since the program's start")
        pr.execute("0")

        return CheckResult.correct()


if __name__ == '__main__':
    TrafficLightTest().run_tests()
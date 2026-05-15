import sys

if sys.platform == "win32":
    import msvcrt

    def read_word(prompt: str = "      ") -> tuple[str, bool]:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        buf: list[str] = []
        had_backspace = False
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                break
            elif ch in ("\x7f", "\x08"):
                if buf:
                    buf.pop()
                    had_backspace = True
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == "\x03":
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                raise KeyboardInterrupt
            elif ch >= " ":
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
        return "".join(buf), had_backspace

else:
    import tty
    import termios

    def read_word(prompt: str = "      ") -> tuple[str, bool]:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf: list[str] = []
        had_backspace = False
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    break
                elif ch in ("\x7f", "\x08"):
                    if buf:
                        buf.pop()
                        had_backspace = True
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    raise KeyboardInterrupt
                elif ch >= " ":
                    buf.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return "".join(buf), had_backspace

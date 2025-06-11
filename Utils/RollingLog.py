import pygame #type: ignore
class RollingLog:
    def __init__(self, max_lines=300, font=None, max_width=None):
        self.lines = []
        self.max_lines = max_lines
        self.font = font or pygame.font.SysFont("consolas", 16)
        self.max_width = max_width or 462 # default width

    def append(self, line):
        self.lines.append(line)
        while len(self.lines) > self.max_lines:
            self.lines.pop(0)

    def get_visible_lines(self, start_index, num_lines):
        return self.lines[start_index:start_index + num_lines]

    def total_lines(self):
        count = 0
        for line in self.lines:
            i = 0
            while i < len(line):
                j = i + 1
                while j <= len(line):
                    slice = line[i:j]
                    width = self.font.render(slice, True, (0, 0, 0)).get_width()
                    if width > self.max_width:
                        break
                    j += 1
                count += 1
                i = j - 1
        return count

    def clear(self):
        self.lines.clear()

    def update_width(self, new_width):
        self.max_width = new_width
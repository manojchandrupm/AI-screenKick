from pathlib import Path


class SessionTimeline:

    def __init__(self):
        self.steps = []

    def add_step(self, image_path, parsed_content):

        self.steps.append({
            "image": image_path,
            "elements": parsed_content
        })

    def get_steps(self):
        return self.steps

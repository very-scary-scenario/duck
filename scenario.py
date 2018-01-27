import chardet
import os
import random
import regex as re

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), 'scenarios')


class Scenario:
    def __init__(self, filename):
        print(filename)
        self.prompt = None
        self.answers = []

        with open(filename, 'rb') as f:
            encoding = chardet.detect(f.read())
            f.seek(0)
            lines = (
                l.decode(encoding['encoding']).strip()
                for l in f.readlines() if l.strip()
            )

            for line in lines:
                answer_match = re.match(r'<(.*)>$', line)
                outcome_match = re.match(r'(\d+) (.*?)(\W[+-][^ ]*)*$', line)

                if line.lower() == '<scenario>':
                    continue
                elif self.prompt is None:
                    self.prompt = line
                elif answer_match:
                    self.answers.append({
                        'answer': answer_match.group(1), 'outcomes': [],
                    })
                elif not self.answers:
                    continue
                elif outcome_match:
                    print(line)
                    self.answers[-1]['outcomes'].append({
                        'probability': int(outcome_match.group(1)),
                        'flavour': outcome_match.group(2),
                        'effects': [
                            c.strip() for c in outcome_match.captures(3)
                        ],
                    })
                else:
                    raise RuntimeError('could not parse {!r} from {}'.format(
                        line, filename))

        raise RuntimeError(self.answers)

    @classmethod
    def get_random(cls):
        return cls(os.path.join(SCENARIO_DIR, random.choice([
            fn for fn in os.listdir(SCENARIO_DIR)
            if fn.endswith('.txt') and not fn.startswith('.')
        ])))

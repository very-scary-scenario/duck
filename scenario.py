import os
import random

from camel import CamelRegistry
import regex as re

registry = CamelRegistry()

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), 'scenarios')

EXPERIENCE = 'exp'
SPEED = 'speed'
DISTANCE = 'distance'
MOTIVATION = 'motivation'

EFFECTS = [
    EXPERIENCE,
    SPEED,
    DISTANCE,
    MOTIVATION,
]


class Scenario:
    def __init__(self, filename):
        self._filename = filename
        self.prompt = None
        self.answers = []

        with open(filename, 'r') as f:
            lines = (
                l.strip().strip('\ufeff')
                for l in f.readlines() if l.strip()
            )

            for line in lines:
                answer_match = re.match(r'<(.*)>$', line)
                outcome_match = re.match(r'(\d+) (.*?)(\W[+-]+[^ ]*)*$', line)

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
                    self.answers[-1]['outcomes'].append({
                        'probability': int(outcome_match.group(1)),
                        'flavour': outcome_match.group(2),
                        'effects': [
                            self._make_effect(c.strip())
                            for c in outcome_match.captures(3)
                        ],
                    })
                else:
                    raise RuntimeError('could not parse {!r} from {}'.format(
                        line, filename))

    def _make_effect(self, source):
        kind = source.lstrip('-+').lower()

        if kind not in EFFECTS:
            raise RuntimeError(
                '{!r} is not an effect i understand'.format(kind)
            )

        return {
            'positive': source[0] == '+',
            'multiplier': len(source) - len(kind),
            'kind': kind,
            'source': source,
        }

    @classmethod
    def get_random(cls, duck):
        return cls(os.path.join(SCENARIO_DIR, random.choice([
            fn for fn in os.listdir(SCENARIO_DIR)
            if fn.endswith('.txt') and not fn.startswith('.')
        ])))

    def answer_for(self, response):
        for answer in self.answers:
            if answer['answer'].lower() in response.lower():
                return answer

    def outcome_for(self, response):
        answer = self.answer_for(response)
        if answer is None:
            return

        total_probability = sum((o['probability'] for o in answer['outcomes']))
        seed = random.random() * total_probability
        cumulative = 0

        for outcome in answer['outcomes']:
            cumulative += outcome['probability']
            if cumulative >= seed:
                break

        return outcome


@registry.dumper(Scenario, 'scenario', version=None)
def _dump_scenario(scenario):
    return {
        'filename': scenario._filename,
    }


@registry.loader('scenario', version=None)
def _load_scenario(data, version):
    return Scenario(data['filename'])


if __name__ == '__main__':
    print('\n\n\n'.join([
        '{}\n{}'.format(
            scenario.prompt,
            '\n'.join(['\n  <{}>\n{}'.format(
                answer['answer'],
                '\n'.join([
                    '  - {}'.format(outcome['flavour'])
                    for outcome in answer['outcomes']
                ]),
            ) for answer in scenario.answers])
        )
        for scenario in [
            Scenario(os.path.join(SCENARIO_DIR, fn))
            for fn in os.listdir(SCENARIO_DIR)
            if fn.endswith('.txt') and not fn.startswith('.')
        ]
    ]))
